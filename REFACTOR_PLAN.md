# RAGFlow架构重构计划：OpenClaw作为统一消息网关

## 📋 重构目标

将当前的"飞书直接对接RAG/Agent"架构重构为"飞书→OpenClaw Gateway→RAGFlow→RAG/Agent"架构，使OpenClaw成为统一的消息传递桥梁。

**当前架构**：
```
飞书 → RAGFlow(/api/v1/feishu) → RAG/Agent（直接）
```

**目标架构**：
```
飞书/钉钉/企业微信 → OpenClaw Gateway → RAGFlow(/api/v1/message) → RAG/Agent
                                              ↓
                                          返回结果
                                              ↓
                      OpenClaw Gateway ← RAGFlow
                              ↓
                      飞书/钉钉/企业微信
```

---

## 🎯 重构收益

1. **统一消息网关**：所有外部消息渠道统一由OpenClaw管理
2. **解耦架构**：RAGFlow专注于RAG/Agent业务逻辑，不关心消息来源
3. **易于扩展**：接入新渠道（钉钉、企业微信）只需在OpenClaw配置
4. **统一管理**：工具注册、权限控制、限流、消息格式转换都在OpenClaw层
5. **降级方案**：保留飞书直接对接作为备用方案

---

## 📅 重构阶段划分

### Phase 1: 设计与准备（1-2天）
### Phase 2: RAGFlow后端改造（2-3天）
### Phase 3: OpenClaw Gateway改造（3-4天）
### Phase 4: 集成测试与灰度发布（2-3天）
### Phase 5: 文档与监控（1-2天）

**总计：9-14天**

---

## 🔧 Phase 1: 设计与准备（1-2天）

### 1.1 定义统一消息格式

**目标**：设计跨渠道的统一消息协议

**任务清单**：

- [ ] **创建统一消息Schema**
  - 文件：`backend/app/schemas/unified_message.py`
  - 内容：
    ```python
    class UnifiedMessageRequest(BaseModel):
        """统一消息请求格式"""
        message_id: str  # 消息唯一ID
        source: str  # 消息来源：feishu, dingtalk, wechat_work
        channel_type: str  # 渠道类型：p2p, group
        sender_id: str  # 发送者ID
        sender_name: Optional[str]  # 发送者名称
        chat_id: str  # 会话ID
        content: str  # 消息内容（纯文本）
        content_type: str  # 内容类型：text, image, file
        timestamp: int  # 时间戳
        context: Dict[str, Any]  # 上下文信息

    class UnifiedMessageResponse(BaseModel):
        """统一消息响应格式"""
        message_id: str  # 原消息ID
        response_content: str  # 响应内容
        response_type: str  # 响应类型：text, card, image
        execution_time: float  # 执行时间
        metadata: Optional[Dict[str, Any]]  # 元数据
    ```

- [ ] **设计错误处理机制**
  - 统一错误码映射
  - 降级策略定义

- [ ] **设计认证机制**
  - OpenClaw → RAGFlow的API Token认证
  - 在`backend/app/config.py`添加`OPENCLAW_API_TOKENS`配置

### 1.2 架构设计文档

- [ ] **绘制详细架构图**
  - 消息流转图
  - 组件交互图
  - 数据流图

- [ ] **定义接口规范**
  - OpenClaw → RAGFlow接口规范
  - RAGFlow → OpenClaw回调规范

- [ ] **制定数据库变更计划**
  - 是否需要新增表记录消息来源
  - 是否需要添加`source`字段到`conversations`表

### 1.3 环境准备

- [ ] **创建开发分支**
  ```bash
  git checkout -b refactor/openclaw-gateway-integration
  ```

- [ ] **准备测试环境**
  - 本地OpenClaw Gateway实例
  - 飞书测试机器人
  - 测试用户账号

---

## 🔧 Phase 2: RAGFlow后端改造（2-3天）

### 2.1 创建统一消息处理接口

**目标**：创建`/api/v1/message`端点，接收OpenClaw转发的消息

**任务清单**：

- [ ] **创建Schema文件**
  - 文件：`backend/app/schemas/unified_message.py`
  - 实现Phase 1.1定义的Schema

- [ ] **创建统一消息服务**
  - 文件：`backend/app/services/unified_message_service.py`
  - 功能：
    - 解析统一消息格式
    - 路由到RAG/Agent系统
    - 处理用户映射（source_user_id → system_user_id）
    - 记录消息来源
  - 代码结构：
    ```python
    class UnifiedMessageService:
        def __init__(self, db: Session):
            self.db = db
            self.conversation_service = ConversationService(db)
            self.rag_manager = get_rag_manager()

        async def process_message(
            self,
            request: UnifiedMessageRequest,
            user: User
        ) -> UnifiedMessageResponse:
            """处理统一格式消息"""
            # 1. 查找或创建会话
            # 2. 调用RAG/Agent
            # 3. 记录消息
            # 4. 返回统一格式响应
    ```

- [ ] **创建API端点**
  - 文件：`backend/app/api/v1/unified_message.py`
  - 端点：`POST /api/v1/message`
  - 认证：使用API Token（从OpenClaw传入）
  - 代码结构：
    ```python
    @router.post("/message", response_model=UnifiedMessageResponse)
    async def process_unified_message(
        request: UnifiedMessageRequest,
        api_token: str = Header(..., alias="X-API-Token"),
        db: Session = Depends(get_db)
    ):
        # 1. 验证API Token
        # 2. 根据source_user_id查找或创建系统用户
        # 3. 调用UnifiedMessageService处理
        # 4. 返回响应
    ```

- [ ] **注册路由**
  - 文件：`backend/app/api/v1/__init__.py`
  - 添加：`from app.api.v1 import unified_message`
  - 注册：`api_router.include_router(unified_message.router)`

### 2.2 实现用户映射机制

**目标**：将外部用户ID（飞书user_id）映射到系统用户

**任务清单**：

- [ ] **数据库迁移：添加外部用户ID字段**
  - 文件：`backend/migrations/versions/xxxx_add_external_user_mapping.py`
  - 修改`users`表：
    ```python
    # 添加字段
    op.add_column('users', sa.Column('external_user_id', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('external_source', sa.String(50), nullable=True))
    op.create_index('idx_external_user', 'users', ['external_source', 'external_user_id'])
    ```

- [ ] **修改User模型**
  - 文件：`backend/app/models/user.py`
  - 添加字段：
    ```python
    external_user_id = Column(String(200), nullable=True, comment="外部用户ID")
    external_source = Column(String(50), nullable=True, comment="外部来源：feishu, dingtalk")
    ```

- [ ] **创建用户映射服务**
  - 文件：`backend/app/services/user_mapping_service.py`
  - 功能：
    ```python
    class UserMappingService:
        def get_or_create_user_by_external_id(
            self,
            external_source: str,
            external_user_id: str,
            external_user_name: Optional[str] = None
        ) -> User:
            """根据外部ID查找或创建用户"""
            # 1. 查找是否已存在映射
            # 2. 如果不存在，创建新用户
            # 3. 返回用户对象
    ```

### 2.3 重构飞书集成为降级方案

**目标**：保留飞书直接对接，但标记为降级方案

**任务清单**：

- [ ] **重命名飞书端点**
  - 文件：`backend/app/api/v1/feishu.py`
  - 修改路由前缀：`/feishu` → `/feishu-legacy`
  - 添加注释：标记为降级方案

- [ ] **添加降级开关**
  - 文件：`backend/app/config.py`
  - 添加配置：
    ```python
    class FeishuSettings(BaseSettings):
        enable_legacy_mode: bool = Field(
            default=False,
            description="是否启用飞书直接对接（降级模式）"
        )
    ```

- [ ] **修改飞书webhook逻辑**
  - 添加条件判断：如果`enable_legacy_mode=True`，使用旧逻辑
  - 否则返回提示信息，引导配置OpenClaw

### 2.4 添加API Token认证中间件

**任务清单**：

- [ ] **创建API Token验证依赖**
  - 文件：`backend/app/dependencies.py`
  - 添加：
    ```python
    async def verify_openclaw_api_token(
        api_token: str = Header(..., alias="X-API-Token")
    ) -> bool:
        """验证OpenClaw API Token"""
        valid_tokens = settings.openclaw.api_tokens.split(",")
        if api_token not in valid_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Token"
            )
        return True
    ```

- [ ] **应用到统一消息端点**
  - 在`/api/v1/message`端点添加依赖

---

## 🔧 Phase 3: OpenClaw Gateway改造（3-4天）

**注意**：此阶段假设OpenClaw Gateway是一个独立的项目。如果OpenClaw Gateway是第三方服务，需要与其团队协调。

### 3.1 OpenClaw Gateway添加飞书Webhook接收

**任务清单**：

- [ ] **创建飞书消息接收端点**
  - 端点：`POST /webhooks/feishu`
  - 功能：
    - 接收飞书webhook事件
    - 验证飞书签名
    - 解析飞书消息格式

- [ ] **实现消息格式转换**
  - 飞书消息格式 → 统一消息格式（`UnifiedMessageRequest`）
  - 提取：message_id, sender_id, content, chat_id等

- [ ] **调用RAGFlow后端**
  - HTTP Client配置
  - 调用`POST http://ragflow-backend:8000/api/v1/message`
  - 传递API Token（`X-API-Token`）

- [ ] **处理响应并回复飞书**
  - 接收RAGFlow的`UnifiedMessageResponse`
  - 转换为飞书消息格式
  - 调用飞书API发送消息

### 3.2 OpenClaw Gateway配置管理

**任务清单**：

- [ ] **添加RAGFlow后端配置**
  - 配置项：
    ```yaml
    ragflow:
      backend_url: "http://localhost:8000"
      api_token: "your-api-token-here"
      timeout: 30
      max_retries: 3
    ```

- [ ] **添加飞书配置**
  - 配置项：
    ```yaml
    feishu:
      app_id: "cli_xxx"
      app_secret: "xxx"
      verification_token: "xxx"
      encrypt_key: "xxx"
    ```

### 3.3 OpenClaw Gateway错误处理与降级

**任务清单**：

- [ ] **实现熔断器**
  - 当RAGFlow后端连续失败N次，触发熔断
  - 返回友好错误提示给用户

- [ ] **实现重试机制**
  - 对于临时性错误（超时、5xx），自动重试
  - 最大重试3次，指数退避

- [ ] **实现降级响应**
  - 当RAGFlow不可用时，返回预设消息
  - 例如："系统繁忙，请稍后再试"

---

## 🔧 Phase 4: 集成测试与灰度发布（2-3天）

### 4.1 单元测试

**RAGFlow后端测试**：

- [ ] **测试统一消息处理**
  - 文件：`backend/tests/api/v1/test_unified_message.py`
  - 测试用例：
    - 正常消息处理
    - API Token验证
    - 用户映射逻辑
    - 错误处理

- [ ] **测试用户映射服务**
  - 文件：`backend/tests/services/test_user_mapping_service.py`
  - 测试用例：
    - 创建新用户
    - 查找已存在用户
    - 多来源用户隔离

**OpenClaw Gateway测试**：

- [ ] **测试飞书消息接收**
  - 测试用例：
    - 飞书签名验证
    - 消息格式转换
    - RAGFlow调用

- [ ] **测试错误处理**
  - 测试用例：
    - RAGFlow超时
    - RAGFlow返回错误
    - 熔断器触发

### 4.2 集成测试

- [ ] **端到端测试**
  - 测试流程：
    1. 飞书发送消息
    2. OpenClaw接收并转发
    3. RAGFlow处理并返回
    4. OpenClaw回复飞书
  - 验证点：
    - 消息内容正确
    - 响应时间<3秒
    - 用户映射正确

- [ ] **压力测试**
  - 并发100个请求
  - 验证系统稳定性
  - 验证熔断器工作

### 4.3 灰度发布策略

**阶段1：内部测试（1-2天）**

- [ ] **部署到测试环境**
  - RAGFlow后端部署
  - OpenClaw Gateway部署
  - 配置飞书测试机器人

- [ ] **内部团队测试**
  - 邀请5-10人测试
  - 收集反馈
  - 修复问题

**阶段2：小范围灰度（2-3天）**

- [ ] **配置灰度规则**
  - 10%用户流量走新架构
  - 90%用户流量走旧架构（降级方案）

- [ ] **监控关键指标**
  - 成功率
  - 响应时间
  - 错误率

- [ ] **逐步扩大灰度**
  - 10% → 30% → 50% → 100%

**阶段3：全量发布**

- [ ] **切换所有流量到新架构**
- [ ] **保留降级开关**
- [ ] **监控1周，确保稳定**

### 4.4 回滚方案

- [ ] **准备回滚脚本**
  - 一键切换到降级模式
  - 修改飞书webhook URL

- [ ] **回滚触发条件**
  - 错误率>5%
  - 响应时间>5秒
  - 用户投诉>10条

---

## 🔧 Phase 5: 文档与监控（1-2天）

### 5.1 API文档

- [ ] **更新Swagger文档**
  - 文件：`backend/app/api/v1/unified_message.py`
  - 添加详细的接口说明、示例

- [ ] **编写架构文档**
  - 文件：`docs/architecture/openclaw-integration.md`
  - 内容：
    - 架构图
    - 消息流转说明
    - 接口规范
    - 错误处理

- [ ] **编写部署文档**
  - 文件：`docs/deployment/openclaw-deployment.md`
  - 内容：
    - 环境要求
    - 配置说明
    - 部署步骤
    - 故障排查

### 5.2 监控与告警

- [ ] **添加Prometheus指标**
  - 指标：
    - `unified_message_requests_total`：总请求数
    - `unified_message_duration_seconds`：处理时间
    - `unified_message_errors_total`：错误数
    - `openclaw_backend_calls_total`：OpenClaw调用次数

- [ ] **配置告警规则**
  - 错误率>5%，发送告警
  - 响应时间>3秒，发送告警
  - OpenClaw连接失败，发送告警

- [ ] **配置日志收集**
  - 统一消息处理日志
  - OpenClaw调用日志
  - 错误日志

### 5.3 用户文档

- [ ] **编写用户指南**
  - 文件：`docs/user-guide/feishu-integration.md`
  - 内容：
    - 如何配置飞书机器人
    - 如何使用RAG功能
    - 常见问题FAQ

---

## 📊 关键文件清单

### 新增文件

**RAGFlow后端**：
```
backend/app/schemas/unified_message.py          # 统一消息Schema
backend/app/services/unified_message_service.py # 统一消息服务
backend/app/services/user_mapping_service.py    # 用户映射服务
backend/app/api/v1/unified_message.py           # 统一消息API端点
backend/migrations/versions/xxxx_add_external_user_mapping.py  # 数据库迁移
backend/tests/api/v1/test_unified_message.py    # 单元测试
backend/tests/services/test_user_mapping_service.py  # 单元测试
```

**OpenClaw Gateway**（假设独立项目）：
```
openclaw-gateway/handlers/feishu_webhook.py     # 飞书webhook处理
openclaw-gateway/services/message_converter.py  # 消息格式转换
openclaw-gateway/clients/ragflow_client.py      # RAGFlow客户端
openclaw-gateway/config/ragflow.yaml            # RAGFlow配置
```

**文档**：
```
docs/architecture/openclaw-integration.md       # 架构文档
docs/deployment/openclaw-deployment.md          # 部署文档
docs/user-guide/feishu-integration.md           # 用户指南
REFACTOR_PLAN.md                                # 本重构计划
```

### 修改文件

**RAGFlow后端**：
```
backend/app/models/user.py                      # 添加外部用户ID字段
backend/app/config.py                           # 添加配置项
backend/app/dependencies.py                     # 添加API Token验证
backend/app/api/v1/__init__.py                  # 注册新路由
backend/app/api/v1/feishu.py                    # 重命名为降级方案
```

---

## ⚠️ 风险与注意事项

### 技术风险

1. **OpenClaw Gateway是否支持自定义webhook？**
   - 风险：如果OpenClaw是第三方服务，可能不支持自定义webhook
   - 缓解：提前与OpenClaw团队确认，或考虑自建Gateway

2. **消息延迟增加**
   - 风险：增加一层网络调用，延迟可能增加200-500ms
   - 缓解：优化网络配置，使用HTTP/2，启用连接池

3. **数据库迁移风险**
   - 风险：添加字段可能影响现有数据
   - 缓解：先在测试环境验证，使用可回滚的迁移脚本

### 业务风险

1. **用户体验中断**
   - 风险：重构期间可能影响用户使用
   - 缓解：采用灰度发布，保留降级方案

2. **用户映射错误**
   - 风险：外部用户ID映射错误，导致会话混乱
   - 缓解：充分测试，添加日志审计

### 依赖风险

1. **OpenClaw Gateway可用性**
   - 风险：OpenClaw故障导致整个系统不可用
   - 缓解：实现熔断器，保留降级方案

---

## ✅ 验收标准

### 功能验收

- [ ] 飞书消息能通过OpenClaw正常转发到RAGFlow
- [ ] RAGFlow响应能正常返回到飞书
- [ ] 用户映射正确，会话不混乱
- [ ] 降级方案可用，一键切换

### 性能验收

- [ ] 端到端响应时间<3秒（P95）
- [ ] 系统吞吐量>100 QPS
- [ ] 错误率<1%

### 安全验收

- [ ] API Token认证正常工作
- [ ] 飞书签名验证正常工作
- [ ] 敏感信息不泄露

---

## 📞 协调与沟通

### 需要协调的团队

1. **OpenClaw团队**（如果是独立团队）
   - 确认是否支持自定义webhook
   - 协调接口规范
   - 协调部署时间

2. **飞书管理员**
   - 修改webhook配置
   - 测试机器人配置

3. **运维团队**
   - 部署新服务
   - 配置监控告警
   - 准备回滚方案

### 沟通计划

- **Week 1**：设计评审会议，确认技术方案
- **Week 2**：每日站会，同步进度
- **Week 3**：测试评审会议，确认测试结果
- **Week 4**：发布评审会议，确认发布计划

---

## 📈 后续优化

重构完成后，可以考虑以下优化：

1. **接入更多渠道**
   - 钉钉
   - 企业微信
   - Slack

2. **增强OpenClaw能力**
   - 消息路由规则
   - 智能分流
   - A/B测试

3. **性能优化**
   - 消息队列异步处理
   - 缓存优化
   - 连接池优化

---

## 📝 总结

本重构计划将RAGFlow从"飞书直接对接"架构升级为"OpenClaw统一网关"架构，预计耗时9-14天。重构后系统将具备更好的扩展性、可维护性和稳定性。

**关键成功因素**：
1. 充分的测试覆盖
2. 灰度发布策略
3. 完善的降级方案
4. 团队间的有效协调

**下一步行动**：
1. 评审本重构计划
2. 确认OpenClaw Gateway的技术可行性
3. 创建开发分支，开始Phase 1
