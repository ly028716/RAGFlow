---
name: code-review
description: 按照项目安全和性能标准审查代码。当需要代码审查、检查代码质量、安全审计、性能优化建议时使用。
allowed-tools: Read, Grep, Glob
---

# 代码审查 Skill

为 RAGAgentLangChain 项目进行符合规范的代码审查。

## 审查清单

### 1. 代码质量

#### 命名规范
- [ ] 类名使用 PascalCase：`UserRepository`, `AuthService`
- [ ] 函数/方法使用 snake_case：`get_by_id`, `create_user`
- [ ] 常量使用 UPPER_SNAKE_CASE：`MAX_LOGIN_ATTEMPTS`
- [ ] 私有方法以下划线开头：`_check_account_locked`

#### 文档规范
- [ ] 模块有文档字符串说明用途
- [ ] 类有文档字符串说明职责和使用方式
- [ ] 公共方法有完整的 Args/Returns/Raises 文档
- [ ] 复杂逻辑有注释说明
- [ ] 使用中文注释

#### 类型注解
- [ ] 所有函数参数有类型注解
- [ ] 所有函数返回值有类型注解
- [ ] 使用 `Optional` 标注可选参数
- [ ] 使用 `List`, `Dict`, `Tuple` 等泛型类型

#### 代码结构
- [ ] 函数长度合理（建议 < 50 行）
- [ ] 类职责单一
- [ ] 无重复代码（DRY 原则）
- [ ] 适当的抽象层次

### 2. 安全检查

#### 认证与授权
- [ ] API 端点使用 `get_current_user` 依赖
- [ ] 敏感操作验证用户权限
- [ ] 密码使用 bcrypt 加密存储
- [ ] JWT 令牌正确验证

#### 输入验证
- [ ] 使用 Pydantic 模型验证请求数据
- [ ] 字符串长度限制
- [ ] 数值范围验证
- [ ] 枚举值验证

#### SQL 注入防护
- [ ] 使用 SQLAlchemy ORM 参数化查询
- [ ] 避免字符串拼接 SQL
- [ ] 使用 `filter()` 而非原始 SQL

#### XSS 防护
- [ ] 用户输入在输出前转义
- [ ] 避免直接渲染 HTML

#### 敏感数据
- [ ] 密码不在日志中输出
- [ ] API 密钥从环境变量读取
- [ ] 敏感配置不硬编码

### 3. 性能检查

#### 数据库
- [ ] 避免 N+1 查询问题
- [ ] 使用适当的索引
- [ ] 分页查询大数据集
- [ ] 使用 `joinedload` 预加载关联

#### 缓存
- [ ] 频繁访问的数据使用 Redis 缓存
- [ ] 缓存键命名规范
- [ ] 设置合理的过期时间

#### 异步处理
- [ ] 耗时操作使用后台任务
- [ ] 文档处理异步执行
- [ ] 适当使用 `async/await`

### 4. 错误处理

#### 异常处理
- [ ] 使用自定义异常类
- [ ] 异常有明确的错误信息
- [ ] 在 API 层转换为 HTTPException
- [ ] 不吞掉异常（避免空 except）

#### 日志记录
- [ ] 错误有日志记录
- [ ] 日志级别使用正确
- [ ] 敏感信息不记录到日志

### 5. 架构规范

#### 三层架构
- [ ] API 层只处理 HTTP 请求/响应
- [ ] 业务逻辑在 Service 层
- [ ] 数据访问在 Repository 层
- [ ] 层之间通过依赖注入

#### 依赖管理
- [ ] 使用 FastAPI 的 `Depends`
- [ ] 数据库会话正确管理
- [ ] 避免循环依赖

## 审查报告模板

```markdown
# 代码审查报告

## 概述
- 审查文件: {文件路径}
- 审查日期: {日期}
- 审查范围: {功能描述}

## 发现的问题

### 严重 (Critical)
| 位置 | 问题 | 建议 |
|------|------|------|
| file.py:123 | SQL 注入风险 | 使用参数化查询 |

### 重要 (Major)
| 位置 | 问题 | 建议 |
|------|------|------|
| file.py:45 | 缺少输入验证 | 添加 Pydantic 验证 |

### 一般 (Minor)
| 位置 | 问题 | 建议 |
|------|------|------|
| file.py:78 | 缺少类型注解 | 添加返回类型 |

### 建议 (Suggestion)
| 位置 | 建议 |
|------|------|
| file.py:100 | 可以提取为独立函数 |

## 总结
- 严重问题: X 个
- 重要问题: X 个
- 一般问题: X 个
- 建议: X 个

## 审查结论
[ ] 通过
[ ] 需要修改后重新审查
[ ] 不通过
```

## 常见问题示例

### 1. SQL 注入风险

```python
# 不好 - 字符串拼接
query = f"SELECT * FROM users WHERE username = '{username}'"

# 好 - 使用 ORM
user = db.query(User).filter(User.username == username).first()
```

### 2. 缺少输入验证

```python
# 不好 - 直接使用输入
@router.post("/users")
def create_user(username: str, password: str):
    ...

# 好 - 使用 Pydantic 验证
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

@router.post("/users")
def create_user(data: UserCreate):
    ...
```

### 3. N+1 查询问题

```python
# 不好 - N+1 查询
users = db.query(User).all()
for user in users:
    print(user.conversations)  # 每次循环都查询

# 好 - 预加载
from sqlalchemy.orm import joinedload
users = db.query(User).options(joinedload(User.conversations)).all()
```

### 4. 密码泄露风险

```python
# 不好 - 日志中包含密码
logger.info(f"User login: {username}, password: {password}")

# 好 - 不记录敏感信息
logger.info(f"User login attempt: {username}")
```

### 5. 缺少权限检查

```python
# 不好 - 没有验证所有权
@router.delete("/conversations/{id}")
def delete_conversation(id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).get(id)
    db.delete(conversation)

# 好 - 验证所有权
@router.delete("/conversations/{id}")
def delete_conversation(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(404, "对话不存在")
    db.delete(conversation)
```

## 审查流程

1. **理解上下文**: 阅读相关需求和设计文档
2. **检查代码**: 按照审查清单逐项检查
3. **运行测试**: 确保测试通过
4. **记录问题**: 使用报告模板记录发现
5. **提供建议**: 给出具体的改进建议
6. **跟踪修复**: 确认问题已修复
