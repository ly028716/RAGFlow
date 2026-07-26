"""
向量数据库管理模块

提供Chroma向量数据库的初始化、管理和访问功能。
支持按知识库ID创建独立的向量存储集合。
"""

import logging
import os
import hashlib
import re
from typing import Any, Dict, List, Optional

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from chromadb.errors import InvalidDimensionException
from langchain_community.embeddings.dashscope import DashScopeEmbeddings
from langchain_community.vectorstores.chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config import settings
from app.core.llm import _is_placeholder_dashscope_api_key

logger = logging.getLogger(__name__)

_DIMENSION_MISMATCH_RE = re.compile(
    r"Embedding dimension\s+(?P<actual>\d+)\s+does not match collection dimensionality\s+(?P<expected>\d+)",
    re.IGNORECASE,
)


class VectorStoreDimensionMismatchError(RuntimeError):
    def __init__(
        self,
        *,
        knowledge_base_id: int,
        collection_name: str,
        expected_dimension: Optional[int],
        actual_dimension: Optional[int],
        original_message: str,
    ) -> None:
        self.knowledge_base_id = knowledge_base_id
        self.collection_name = collection_name
        self.expected_dimension = expected_dimension
        self.actual_dimension = actual_dimension
        self.original_message = original_message
        super().__init__(self._build_message())

    @classmethod
    def from_chroma(
        cls,
        *,
        knowledge_base_id: int,
        collection_name: str,
        exc: Exception,
    ) -> "VectorStoreDimensionMismatchError":
        message = str(exc)
        expected_dim: Optional[int] = None
        actual_dim: Optional[int] = None
        match = _DIMENSION_MISMATCH_RE.search(message)
        if match:
            actual_dim = int(match.group("actual"))
            expected_dim = int(match.group("expected"))
        return cls(
            knowledge_base_id=knowledge_base_id,
            collection_name=collection_name,
            expected_dimension=expected_dim,
            actual_dimension=actual_dim,
            original_message=message,
        )

    def _build_message(self) -> str:
        if self.expected_dimension is not None and self.actual_dimension is not None:
            return (
                "向量库维度不匹配："
                f"collection={self.collection_name}, "
                f"expected_dim={self.expected_dimension}, actual_dim={self.actual_dimension}。"
                "通常是更换了嵌入模型/从 Mock 切换到真实 Key 导致，需要重新向量化该知识库。"
            )
        return (
            "向量库维度不匹配："
            f"collection={self.collection_name}。"
            "通常是更换了嵌入模型/从 Mock 切换到真实 Key 导致，需要重新向量化该知识库。"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_base_id": self.knowledge_base_id,
            "collection_name": self.collection_name,
            "expected_dimension": self.expected_dimension,
            "actual_dimension": self.actual_dimension,
            "original_message": self.original_message,
        }


class DevMockEmbeddings(Embeddings):
    def __init__(self, dim: int = 256):
        self.dim = dim

    def _embed_one(self, text: str) -> List[float]:
        data = (text or "").encode("utf-8", errors="ignore")
        digest = hashlib.sha256(data).digest()
        out: List[float] = []
        i = 0
        while len(out) < self.dim:
            b = digest[i % len(digest)]
            out.append((b / 255.0) * 2.0 - 1.0)
            i += 1
        return out

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_one(text)


class VectorStoreManager:
    """
    向量数据库管理器

    管理Chroma向量数据库的生命周期，提供：
    - 按知识库ID创建独立的向量存储集合
    - 向量嵌入生成（使用DashScopeEmbeddings）
    - 文档添加、删除和检索
    - 集合管理

    使用方式:
        from app.core.vector_store import get_vector_store, get_embeddings

        # 获取知识库的向量存储
        vector_store = get_vector_store(knowledge_base_id=1)

        # 添加文档
        await vector_store.aadd_documents(documents)

        # 相似度搜索
        results = await vector_store.asimilarity_search("查询文本", k=5)
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        初始化向量数据库管理器

        Args:
            persist_directory: Chroma持久化目录，默认从配置读取
            api_key: DashScope API密钥，默认从配置读取
            embedding_model: 嵌入模型名称，默认从配置读取
        """
        self.persist_directory = (
            persist_directory or settings.vector_db.chroma_persist_directory
        )
        self.api_key = api_key or settings.tongyi.dashscope_api_key
        self.embedding_model = (
            embedding_model
            or os.getenv("EMBEDDING_MODEL")
            or settings.tongyi.embedding_model
        )

        # 确保持久化目录存在
        self._ensure_directory_exists()

        # 嵌入模型实例（懒加载）
        self._embeddings: Optional[Embeddings] = None

        # 向量存储实例缓存
        self._vector_stores: Dict[int, Chroma] = {}

    def _ensure_directory_exists(self) -> None:
        """确保持久化目录存在"""
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory, exist_ok=True)
            logger.info(f"创建向量数据库目录: {self.persist_directory}")

    @property
    def embeddings(self) -> Embeddings:
        """
        获取嵌入模型实例（懒加载）

        Returns:
            DashScopeEmbeddings: 配置好的嵌入模型实例
        """
        if self._embeddings is None:
            self._embeddings = self._create_embeddings()
        return self._embeddings

    def _create_embeddings(self) -> Embeddings:
        """
        创建DashScope嵌入模型实例

        Returns:
            DashScopeEmbeddings: 嵌入模型实例
        """
        if _is_placeholder_dashscope_api_key(self.api_key) and (
            settings.debug or settings.environment.lower() == "development"
        ):
            logger.warning("检测到占位 DashScope API Key，已启用开发模式 Mock Embeddings（仅用于本地调试）。")
            return DevMockEmbeddings()

        logger.info(f"创建DashScope嵌入模型: model={self.embedding_model}")

        return DashScopeEmbeddings(
            dashscope_api_key=self.api_key,
            model=self.embedding_model,
        )

    def _get_collection_name(self, knowledge_base_id: int) -> str:
        """
        根据知识库ID生成集合名称

        Args:
            knowledge_base_id: 知识库ID

        Returns:
            str: 集合名称
        """
        return f"kb_{knowledge_base_id}"

    def get_vector_store(self, knowledge_base_id: int) -> Chroma:
        """
        获取指定知识库的向量存储实例

        Args:
            knowledge_base_id: 知识库ID

        Returns:
            Chroma: 向量存储实例
        """
        if knowledge_base_id not in self._vector_stores:
            self._vector_stores[knowledge_base_id] = self._create_vector_store(
                knowledge_base_id
            )

        return self._vector_stores[knowledge_base_id]

    def _create_vector_store(self, knowledge_base_id: int) -> Chroma:
        """
        创建向量存储实例

        Args:
            knowledge_base_id: 知识库ID

        Returns:
            Chroma: 新创建的向量存储实例
        """
        collection_name = self._get_collection_name(knowledge_base_id)

        logger.info(
            f"创建向量存储: collection={collection_name}, "
            f"persist_directory={self.persist_directory}"
        )

        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )

    async def add_documents(
        self,
        knowledge_base_id: int,
        documents: List[Document],
        document_id: Optional[int] = None,
    ) -> List[str]:
        """
        向知识库添加文档

        Args:
            knowledge_base_id: 知识库ID
            documents: 文档列表
            document_id: 文档ID（可选，用于添加元数据）

        Returns:
            List[str]: 添加的文档ID列表
        """
        vector_store = self.get_vector_store(knowledge_base_id)

        # 添加元数据
        for doc in documents:
            doc.metadata["knowledge_base_id"] = knowledge_base_id
            if document_id is not None:
                doc.metadata["document_id"] = document_id

        logger.info(
            f"添加文档到向量存储: kb_id={knowledge_base_id}, "
            f"document_id={document_id}, count={len(documents)}"
        )

        # 使用异步方法添加文档
        try:
            ids = await vector_store.aadd_documents(documents)
        except InvalidDimensionException as e:
            collection_name = self._get_collection_name(knowledge_base_id)
            raise VectorStoreDimensionMismatchError.from_chroma(
                knowledge_base_id=knowledge_base_id,
                collection_name=collection_name,
                exc=e,
            ) from e

        return ids

    def add_documents_sync(
        self,
        knowledge_base_id: int,
        documents: List[Document],
        document_id: Optional[int] = None,
    ) -> List[str]:
        """
        同步向知识库添加文档

        Args:
            knowledge_base_id: 知识库ID
            documents: 文档列表
            document_id: 文档ID（可选，用于添加元数据）

        Returns:
            List[str]: 添加的文档ID列表
        """
        vector_store = self.get_vector_store(knowledge_base_id)

        # 添加元数据
        for doc in documents:
            doc.metadata["knowledge_base_id"] = knowledge_base_id
            if document_id is not None:
                doc.metadata["document_id"] = document_id

        logger.info(
            f"同步添加文档到向量存储: kb_id={knowledge_base_id}, "
            f"document_id={document_id}, count={len(documents)}"
        )

        # 使用同步方法添加文档
        ids = vector_store.add_documents(documents)

        return ids

    async def similarity_search(
        self,
        knowledge_base_id: int,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        在知识库中进行相似度搜索

        Args:
            knowledge_base_id: 知识库ID
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件

        Returns:
            List[Document]: 相似文档列表
        """
        vector_store = self.get_vector_store(knowledge_base_id)

        logger.debug(
            f"相似度搜索: kb_id={knowledge_base_id}, " f"query长度={len(query)}, k={k}"
        )

        try:
            results = await vector_store.asimilarity_search(
                query=query,
                k=k,
                filter=filter_dict,
            )
        except InvalidDimensionException as e:
            collection_name = self._get_collection_name(knowledge_base_id)
            raise VectorStoreDimensionMismatchError.from_chroma(
                knowledge_base_id=knowledge_base_id,
                collection_name=collection_name,
                exc=e,
            ) from e

        logger.debug(f"搜索结果数量: {len(results)}")
        return results

    async def similarity_search_with_score(
        self,
        knowledge_base_id: int,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[tuple]:
        """
        在知识库中进行相似度搜索（带评分）

        Args:
            knowledge_base_id: 知识库ID
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件

        Returns:
            List[tuple]: (文档, 相似度评分) 元组列表
        """
        vector_store = self.get_vector_store(knowledge_base_id)

        logger.debug(
            f"带评分相似度搜索: kb_id={knowledge_base_id}, " f"query长度={len(query)}, k={k}"
        )

        try:
            results = await vector_store.asimilarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict,
            )
        except InvalidDimensionException as e:
            collection_name = self._get_collection_name(knowledge_base_id)
            raise VectorStoreDimensionMismatchError.from_chroma(
                knowledge_base_id=knowledge_base_id,
                collection_name=collection_name,
                exc=e,
            ) from e

        logger.debug(f"搜索结果数量: {len(results)}")
        return results

    async def multi_knowledge_base_search(
        self,
        knowledge_base_ids: List[int],
        query: str,
        k: int = 5,
    ) -> List[tuple]:
        """
        在多个知识库中进行联合搜索

        Args:
            knowledge_base_ids: 知识库ID列表
            query: 查询文本
            k: 每个知识库返回的结果数量

        Returns:
            List[tuple]: (文档, 相似度评分) 元组列表，按相似度排序
        """
        all_results = []

        for kb_id in knowledge_base_ids:
            try:
                results = await self.similarity_search_with_score(
                    knowledge_base_id=kb_id,
                    query=query,
                    k=k,
                )
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"知识库 {kb_id} 搜索失败: {str(e)}")
                continue

        # 按相似度评分排序（评分越低越相似）
        all_results.sort(key=lambda x: x[1])

        # 返回前k个结果
        return all_results[:k]

    async def delete_by_document_id(
        self,
        knowledge_base_id: int,
        document_id: int,
    ) -> bool:
        """
        删除指定文档的所有向量

        Args:
            knowledge_base_id: 知识库ID
            document_id: 文档ID

        Returns:
            bool: 是否删除成功
        """
        vector_store = self.get_vector_store(knowledge_base_id)

        logger.info(f"删除文档向量: kb_id={knowledge_base_id}, " f"document_id={document_id}")

        try:
            # 使用过滤条件删除
            vector_store._collection.delete(where={"document_id": document_id})
            return True
        except Exception as e:
            logger.error(f"删除文档向量失败: {str(e)}")
            return False

    def delete_collection(self, knowledge_base_id: int) -> bool:
        """
        删除整个知识库的向量集合

        Args:
            knowledge_base_id: 知识库ID

        Returns:
            bool: 是否删除成功
        """
        collection_name = self._get_collection_name(knowledge_base_id)

        logger.info(f"删除向量集合: {collection_name}")

        try:
            # 从缓存中移除
            if knowledge_base_id in self._vector_stores:
                del self._vector_stores[knowledge_base_id]

            # 删除集合
            import chromadb

            client = chromadb.PersistentClient(path=self.persist_directory)
            client.delete_collection(collection_name)

            return True
        except Exception as e:
            logger.error(f"删除向量集合失败: {str(e)}")
            return False

    def get_collection_stats(self, knowledge_base_id: int) -> Dict[str, Any]:
        """
        获取集合统计信息

        Args:
            knowledge_base_id: 知识库ID

        Returns:
            dict: 集合统计信息
        """
        vector_store = self.get_vector_store(knowledge_base_id)
        collection_name = self._get_collection_name(knowledge_base_id)

        try:
            count = vector_store._collection.count()
            return {
                "collection_name": collection_name,
                "document_count": count,
                "knowledge_base_id": knowledge_base_id,
            }
        except Exception as e:
            logger.error(f"获取集合统计失败: {str(e)}")
            return {
                "collection_name": collection_name,
                "document_count": 0,
                "knowledge_base_id": knowledge_base_id,
                "error": str(e),
            }

    def clear_cache(self) -> None:
        """清除向量存储缓存"""
        self._vector_stores.clear()
        logger.info("向量存储缓存已清除")


# 全局向量数据库管理器实例
_vector_store_manager: Optional[VectorStoreManager] = None


def get_vector_store_manager() -> VectorStoreManager:
    """
    获取全局向量数据库管理器实例

    Returns:
        VectorStoreManager: 向量数据库管理器实例
    """
    global _vector_store_manager

    if _vector_store_manager is None:
        _vector_store_manager = VectorStoreManager()

    return _vector_store_manager


def get_vector_store(knowledge_base_id: int) -> Chroma:
    """
    获取指定知识库的向量存储实例（工厂函数）

    Args:
        knowledge_base_id: 知识库ID

    Returns:
        Chroma: 向量存储实例
    """
    manager = get_vector_store_manager()
    return manager.get_vector_store(knowledge_base_id)


def get_embeddings() -> DashScopeEmbeddings:
    """
    获取嵌入模型实例

    Returns:
        DashScopeEmbeddings: 嵌入模型实例
    """
    manager = get_vector_store_manager()
    return manager.embeddings


async def add_documents_to_knowledge_base(
    knowledge_base_id: int,
    documents: List[Document],
    document_id: Optional[int] = None,
) -> List[str]:
    """
    向知识库添加文档（便捷函数）

    Args:
        knowledge_base_id: 知识库ID
        documents: 文档列表
        document_id: 文档ID

    Returns:
        List[str]: 添加的文档ID列表
    """
    manager = get_vector_store_manager()
    return await manager.add_documents(knowledge_base_id, documents, document_id)


async def search_knowledge_base(
    knowledge_base_id: int,
    query: str,
    k: int = 5,
) -> List[Document]:
    """
    在知识库中搜索（便捷函数）

    Args:
        knowledge_base_id: 知识库ID
        query: 查询文本
        k: 返回结果数量

    Returns:
        List[Document]: 相似文档列表
    """
    manager = get_vector_store_manager()
    return await manager.similarity_search(knowledge_base_id, query, k)


async def search_multiple_knowledge_bases(
    knowledge_base_ids: List[int],
    query: str,
    k: int = 5,
) -> List[tuple]:
    """
    在多个知识库中搜索（便捷函数）

    Args:
        knowledge_base_ids: 知识库ID列表
        query: 查询文本
        k: 返回结果数量

    Returns:
        List[tuple]: (文档, 相似度评分) 元组列表
    """
    manager = get_vector_store_manager()
    return await manager.multi_knowledge_base_search(knowledge_base_ids, query, k)


def reset_vector_store_manager() -> None:
    """
    重置向量数据库管理器

    用于测试或配置更新后重新初始化
    """
    global _vector_store_manager

    if _vector_store_manager is not None:
        _vector_store_manager.clear_cache()

    _vector_store_manager = None
    logger.info("向量数据库管理器已重置")


# 导出
__all__ = [
    "VectorStoreManager",
    "get_vector_store_manager",
    "get_vector_store",
    "get_embeddings",
    "add_documents_to_knowledge_base",
    "search_knowledge_base",
    "search_multiple_knowledge_bases",
    "reset_vector_store_manager",
]
