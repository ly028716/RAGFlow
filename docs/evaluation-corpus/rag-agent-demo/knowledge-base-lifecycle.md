# 知识库生命周期

删除知识库时，服务会在数据库删除前调用 `VectorStoreManager.delete_collection(knowledge_base_id)` 清理对应 Chroma collection。这样可以避免已经删除的知识库仍被向量检索到。
