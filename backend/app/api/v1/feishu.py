"""
飞书 webhook 接入模块

实现飞书机器人消息接收和回复功能，对接现有 RAG/Agent 系统。

快速开始:
    1. 在飞书开放平台创建企业自建应用
    2. 获取 App ID 和 App Secret
    3. 配置事件订阅 URL: https://your-domain/api/v1/feishu/webhook
    4. 订阅 "接收消息" 事件
    5. 配置加密 Token 和 Verification Token
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.langchain_integration.rag_chain import RAGManager, get_rag_manager
from app.models.user import User
from app.services.conversation import ConversationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feishu", tags=["飞书"])


# ============================================================
# 飞书事件模型
# ============================================================

class FeishuMessageEvent:
    """飞书消息事件结构"""
    
    def __init__(self, data: Dict[str, Any]):
        self.schema = data.get("schema", "2.0")
        self.header = data.get("header", {})
        self.event = data.get("event", {})
        
        # Header 字段
        self.event_id = self.header.get("event_id")
        self.event_type = self.header.get("event_type")
        self.app_id = self.header.get("app_id")
        self.tenant_key = self.header.get("tenant_key")
        self.create_time = self.header.get("create_time")
        
        # 消息特有字段
        self.message = self.event.get("message", {})
        self.sender = self.event.get("sender", {})
        
    @property
    def is_message_event(self) -> bool:
        return self.event_type == "im.message.receive_v1"
    
    @property
    def chat_type(self) -> str:
        """p2p: 单聊, group: 群聊"""
        return self.message.get("chat_type", "")
    
    @property
    def message_type(self) -> str:
        """text, post, image, file 等"""
        return self.message.get("message_type", "")
    
    @property
    def content(self) -> str:
        """消息内容（JSON字符串，需解析）"""
        return self.message.get("content", "{}")
    
    @property
    def message_id(self) -> str:
        return self.message.get("message_id", "")
    
    @property
    def chat_id(self) -> str:
        """群聊ID或用户ID"""
        return self.message.get("chat_id", "")
    
    @property
    def sender_id(self) -> str:
        """发送者用户ID"""
        sender_id = self.sender.get("sender_id", {})
        return sender_id.get("user_id", "")
    
    @property
    def sender_type(self) -> str:
        return self.sender.get("sender_type", "")
    
    def get_text_content(self) -> str:
        """提取文本内容"""
        try:
            content_obj = json.loads(self.content)
            if self.message_type == "text":
                return content_obj.get("text", "")
            elif self.message_type == "post":
                # 富文本消息处理
                return self._extract_post_text(content_obj)
        except json.JSONDecodeError:
            logger.error(f"解析消息内容失败: {self.content}")
        return ""
    
    def _extract_post_text(self, post_content: Dict) -> str:
        """从富文本中提取纯文本"""
        texts = []
        content = post_content.get("content", [])
        for item in content:
            if isinstance(item, list):
                for sub_item in item:
                    if isinstance(sub_item, dict):
                        tag = sub_item.get("tag")
                        if tag == "text":
                            texts.append(sub_item.get("text", ""))
                        elif tag == "at":
                            # @机器人，跳过
                            pass
        return "".join(texts)


# ============================================================
# 安全验证
# ============================================================

def verify_feishu_signature(
    request_body: bytes,
    signature: str,
    timestamp: str,
    nonce: str,
    encrypt_key: str
) -> bool:
    """
    验证飞书请求签名

    Args:
        request_body: 原始请求体
        signature: 请求头中的 X-Lark-Signature
        timestamp: 请求头中的 X-Lark-Request-Timestamp
        nonce: 请求头中的 X-Lark-Request-Nonce
        encrypt_key: 飞书应用的 Encrypt Key

    Returns:
        bool: 签名是否有效
    """
    # 按照飞书文档计算签名
    # signature = HMAC_SHA256(timestamp + nonce + encrypt_key + body, encrypt_key)
    import hmac

    bytes_to_sign = f"{timestamp}{nonce}{encrypt_key}".encode('utf-8') + request_body

    # 使用 HMAC-SHA256 计算签名
    expected_signature = hmac.new(
        encrypt_key.encode('utf-8'),
        bytes_to_sign,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


# ============================================================
# 用户身份映射
# ============================================================

class FeishuUserMapper:
    """
    飞书用户与系统用户映射管理
    
    策略：
    1. 首次使用的飞书用户自动创建系统账号
    2. 使用 feishu_user_id 作为唯一标识
    3. 存储映射关系到 user_feishu_bindings 表（可选）
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
    
    async def get_or_create_user(
        self, 
        feishu_user_id: str,
        feishu_user_name: Optional[str] = None
    ) -> User:
        """
        获取或创建系统用户
        
        Args:
            feishu_user_id: 飞书用户唯一ID
            feishu_user_name: 飞书用户显示名
            
        Returns:
            User: 系统用户对象
        """
        # TODO: 实现用户查找/创建逻辑
        # 1. 检查是否已有绑定关系
        # 2. 有则返回现有用户
        # 3. 无则创建新用户，username = f"feishu_{feishu_user_id}"
        
        # 临时实现：返回一个默认用户（实际项目中需要实现）
        user = self.user_service.get_user_by_username(f"feishu_{feishu_user_id}")
        if not user:
            # 创建新用户
            from app.schemas.user import UserCreate
            user_data = UserCreate(
                username=f"feishu_{feishu_user_id}",
                email=f"{feishu_user_id}@feishu.user",
                password=self._generate_random_password(),
                full_name=feishu_user_name or f"飞书用户_{feishu_user_id[:8]}"
            )
            user = self.user_service.create_user(user_data)
            logger.info(f"为飞书用户 {feishu_user_id} 创建系统账号: {user.id}")
        
        return user
    
    def _generate_random_password(self) -> str:
        """生成随机密码（飞书用户不需要密码登录）"""
        import secrets
        return secrets.token_hex(32)


# ============================================================
# 消息处理器
# ============================================================

class FeishuMessageHandler:
    """飞书消息处理器"""
    
    def __init__(self, db: Session, rag_manager: RAGManager):
        self.db = db
        self.rag_manager = rag_manager
        self.user_mapper = FeishuUserMapper(db)
        self.conv_service = ConversationService(db)
    
    async def handle_message(self, event: FeishuMessageEvent) -> Dict[str, Any]:
        """
        处理飞书消息
        
        Args:
            event: 飞书消息事件
            
        Returns:
            Dict: 回复消息内容
        """
        # 提取文本内容
        text = event.get_text_content().strip()
        if not text:
            return {"content": "暂时只支持文本消息哦~"}
        
        # 获取/创建系统用户
        user = await self.user_mapper.get_or_create_user(
            feishu_user_id=event.sender_id,
            feishu_user_name=None  # TODO: 从飞书API获取用户名
        )
        
        # 获取或创建对话（按 chat_id 隔离）
        conversation = self._get_or_create_conversation(
            user_id=user.id,
            chat_id=event.chat_id,
            chat_type=event.chat_type
        )
        
        # 判断意图
        if text.startswith("/"):
            # 命令模式
            return await self._handle_command(text, user, conversation)
        
        # RAG 问答模式（默认）
        return await self._handle_rag_query(text, user, conversation)
    
    def _get_or_create_conversation(
        self, 
        user_id: int, 
        chat_id: str,
        chat_type: str
    ):
        """获取或创建对话"""
        # 使用 chat_id 作为外部标识
        # TODO: 可以添加 feishu_chat_id 字段到 conversation 表
        # 临时：每次创建新对话或按用户维度复用
        
        # 查找该用户最近的一个对话
        conversations = self.conv_service.get_user_conversations(user_id, limit=1)
        if conversations:
            return conversations[0]
        
        # 创建新对话
        return self.conv_service.create_conversation(
            user_id=user_id,
            title=f"飞书{'群聊' if chat_type == 'group' else '私聊'}_{chat_id[:8]}"
        )
    
    async def _handle_command(
        self, 
        text: str, 
        user: User, 
        conversation
    ) -> Dict[str, Any]:
        """处理命令"""
        parts = text[1:].split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        commands = {
            "help": self._cmd_help,
            "kb": self._cmd_list_knowledge_bases,
            "clear": self._cmd_clear_history,
            "status": self._cmd_status,
        }
        
        handler = commands.get(cmd, self._cmd_unknown)
        return await handler(args, user, conversation)
    
    async def _cmd_help(self, args, user, conversation) -> Dict[str, Any]:
        """帮助命令"""
        help_text = """🤖 **RAG智能助手使用指南**

**基础问答**：直接输入问题，我会基于知识库回答

**可用命令**：
• `/help` - 显示本帮助
• `/kb` - 查看可选知识库
• `/kb 1,2` - 切换到知识库 1 和 2
• `/clear` - 清空当前对话历史
• `/status` - 查看配额状态

**提示**：
- 问题越具体，回答越准确
- 支持多轮对话，我会记住上下文
"""
        return {"content": help_text}
    
    async def _cmd_list_knowledge_bases(self, args, user, conversation) -> Dict[str, Any]:
        """列出知识库"""
        # TODO: 从 KnowledgeBasePermissionService 获取用户有权限的知识库
        return {"content": "知识库功能开发中... 默认使用全局知识库"}
    
    async def _cmd_clear_history(self, args, user, conversation) -> Dict[str, Any]:
        """清空历史"""
        self.rag_manager.clear_memory(str(conversation.id))
        return {"content": "✅ 对话历史已清空"}
    
    async def _cmd_status(self, args, user, conversation) -> Dict[str, Any]:
        """查看状态"""
        # TODO: 调用 QuotaService 获取配额信息
        return {"content": "📊 配额查询功能开发中..."}
    
    async def _cmd_unknown(self, args, user, conversation) -> Dict[str, Any]:
        """未知命令"""
        return {"content": f"未知命令，输入 `/help` 查看可用命令"}
    
    async def _handle_rag_query(
        self, 
        text: str, 
        user: User, 
        conversation
    ) -> Dict[str, Any]:
        """处理 RAG 查询"""
        try:
            # 获取对话历史
            history = self._get_formatted_history(conversation.id, user.id)
            
            # TODO: 从用户配置获取默认知识库ID列表
            # 临时使用空列表（不走RAG，直接走普通对话）
            knowledge_base_ids = []
            
            if knowledge_base_ids:
                # RAG 模式
                rag_response = await self.rag_manager.query(
                    knowledge_base_ids=knowledge_base_ids,
                    question=text,
                    conversation_id=str(conversation.id),
                    chat_history=history
                )
                
                answer = rag_response.answer
                sources = rag_response.sources
                
                # 格式化引用来源
                if sources:
                    source_text = "\n\n📚 **参考来源**：\n"
                    for i, src in enumerate(sources[:3], 1):
                        source_text += f"{i}. {src.document_name} (相似度: {src.similarity_score:.2%})\n"
                    answer += source_text
            else:
                # 普通对话模式（不走RAG）
                from app.langchain_integration.chains import get_conversation_manager
                manager = get_conversation_manager()
                answer, _ = await manager.chat(
                    conversation_id=conversation.id,
                    message=text,
                    history=history
                )
            
            # 保存消息到数据库
            self.conv_service.add_message(
                conversation_id=conversation.id,
                user_id=user.id,
                role="user",
                content=text,
                tokens=0
            )
            
            # 估算token并保存AI回复
            tokens_used = len(answer) // 2  # 粗略估算
            self.conv_service.add_message(
                conversation_id=conversation.id,
                user_id=user.id,
                role="assistant",
                content=answer,
                tokens=tokens_used
            )
            
            return {"content": answer}
            
        except Exception as e:
            logger.exception(f"处理RAG查询失败: {e}")
            return {"content": "抱歉，处理问题时出了点差错，请稍后再试~"}
    
    def _get_formatted_history(self, conversation_id: int, user_id: int) -> list:
        """获取格式化的对话历史"""
        messages = self.conv_service.get_recent_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            limit=10
        )
        
        history = []
        for msg in messages:
            history.append({
                "role": "user" if msg.role.value == "USER" else "assistant",
                "content": msg.content
            })
        return history


# ============================================================
# API 端点
# ============================================================

@router.post("/webhook")
async def feishu_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_lark_signature: Optional[str] = Header(None, alias="X-Lark-Signature"),
    x_lark_timestamp: Optional[str] = Header(None, alias="X-Lark-Request-Timestamp"),
    x_lark_nonce: Optional[str] = Header(None, alias="X-Lark-Request-Nonce"),
):
    """
    飞书事件订阅 Webhook

    配置步骤：
    1. 在飞书开放平台 → 事件订阅 → 添加订阅URL
    2. 订阅 "im.message.receive_v1" 事件
    3. 配置 Encrypt Key 和 Verification Token

    请求示例：
    ```json
    {
        "schema": "2.0",
        "header": {
            "event_id": "xxx",
            "event_type": "im.message.receive_v1",
            "app_id": "cli_xxx",
            "tenant_key": "xxx"
        },
        "event": {
            "message": {
                "chat_id": "oc_xxx",
                "chat_type": "p2p",
                "content": "{\"text\":\"你好\"}",
                "message_type": "text"
            },
            "sender": {
                "sender_id": {"user_id": "ou_xxx"},
                "sender_type": "user"
            }
        }
    }
    ```
    """
    from app.config import settings

    body = await request.body()
    data = await request.json()

    # URL 验证（首次配置时需要）
    if data.get("type") == "url_verification":
        challenge = data.get("challenge")
        return {"challenge": challenge}

    # 签名验证（生产环境必须启用）
    if settings.feishu.enable_signature_verification:
        if not all([x_lark_signature, x_lark_timestamp, x_lark_nonce]):
            logger.warning("飞书请求缺少签名验证头")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少签名验证头"
            )

        if not settings.feishu.encrypt_key:
            logger.error("飞书 Encrypt Key 未配置")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="服务器配置错误"
            )

        if not verify_feishu_signature(
            body,
            x_lark_signature,
            x_lark_timestamp,
            x_lark_nonce,
            settings.feishu.encrypt_key
        ):
            logger.warning("飞书请求签名验证失败")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="签名验证失败"
            )

    # 解析事件
    event = FeishuMessageEvent(data)

    # 只处理消息事件
    if not event.is_message_event:
        return {"status": "ignored", "reason": "not a message event"}

    # 过滤机器人消息（避免循环）
    if event.sender_type == "app":
        return {"status": "ignored", "reason": "bot message"}

    # 处理消息
    handler = FeishuMessageHandler(db, get_rag_manager())
    result = await handler.handle_message(event)

    # 返回回复内容（飞书事件订阅模式不需要在这里返回，
    # 实际应该调用飞书消息发送API回复）
    return {
        "status": "ok",
        "reply": result.get("content", "")[:100] + "..."  # 日志截断
    }


@router.post("/webhook/send-reply")
async def send_feishu_reply(
    message_id: str,
    content: str,
    app_id: str = "YOUR_APP_ID",
    app_secret: str = "YOUR_APP_SECRET"
):
    """
    发送飞书回复消息（独立API，用于异步回复场景）
    
    实际场景中，webhook 收到消息后应该：
    1. 立即返回 200 OK 给飞书（避免超时重试）
    2. 异步处理消息并调用此API回复
    
    或者使用飞书消息发送API直接回复。
    """
    import aiohttp
    
    # 1. 获取 tenant access token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, json={
            "app_id": app_id,
            "app_secret": app_secret
        }) as resp:
            token_data = await resp.json()
            tenant_token = token_data.get("tenant_access_token")
    
    if not tenant_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant access token"
        )
    
    # 2. 发送回复消息
    reply_url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    headers = {"Authorization": f"Bearer {tenant_token}"}
    
    message_data = {
        "content": json.dumps({"text": content}),
        "msg_type": "text"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(reply_url, headers=headers, json=message_data) as resp:
            result = await resp.json()
            return result


# ============================================================
# 导出
# ============================================================

__all__ = ["router", "FeishuMessageEvent", "FeishuMessageHandler", "FeishuUserMapper"]
