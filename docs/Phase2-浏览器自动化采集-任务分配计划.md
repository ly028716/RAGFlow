# Phase 2: 浏览器自动化采集 - 任务分配计划

**目标**: 实现基于浏览器自动化的网页内容采集功能，支持定时抓取网页内容并自动存储到知识库

**预计完成时间**: 3-4 周

**优先级**: P1（高优先级）

---

## 任务分配

### 任务 1: 技术架构设计与方案评审
**负责人**: 架构师 (architect)
**优先级**: P0（最高）
**依赖**: 无
**预计工时**: 2-3 天

**任务内容**:
1. 评审技术设计文档
2. 设计数据库表结构（采集任务表、执行日志表）
3. 设计API接口规范
4. 制定浏览器自动化技术方案（Playwright）
5. 制定任务调度方案（APScheduler）
6. 设计内容处理流程
7. 制定安全和性能优化策略

**交付物**:
- ✅ `docs/Phase2-浏览器自动化采集-技术设计文档.md`
- 数据库表结构SQL脚本
- API接口规范文档
- 技术选型评审报告

---

### 任务 2: 数据库迁移脚本
**负责人**: 数据库工程师 (db-migration)
**优先级**: P0
**依赖**: 任务 1 完成
**预计工时**: 1 天

**任务内容**:
1. 创建 Alembic 迁移脚本
2. 创建 `web_scraper_tasks` 表
3. 创建 `web_scraper_logs` 表
4. 添加必要的索引和外键约束
5. 编写回滚脚本

**交付物**:
- `backend/migrations/versions/010_add_web_scraper_tables.py`
- 迁移测试报告

---

### 任务 3: 数据模型和Repository层
**负责人**: 后端开发 (backend-dev)
**优先级**: P0
**依赖**: 任务 2 完成
**预计工时**: 2 天

**任务内容**:
1. 创建数据模型
   - `backend/app/models/web_scraper_task.py`
   - `backend/app/models/web_scraper_log.py`
2. 创建Repository层
   - `backend/app/repositories/web_scraper_task_repository.py`
   - `backend/app/repositories/web_scraper_log_repository.py`
3. 实现CRUD操作
4. 添加查询方法（按状态、按知识库、按时间范围）
5. 编写类型注解和文档字符串

**交付物**:
- `backend/app/models/web_scraper_task.py`
- `backend/app/models/web_scraper_log.py`
- `backend/app/repositories/web_scraper_task_repository.py`
- `backend/app/repositories/web_scraper_log_repository.py`

---

### 任务 4: 浏览器自动化核心模块
**负责人**: 后端开发 (backend-dev)
**优先级**: P0
**依赖**: 任务 1 完成
**预计工时**: 3-4 天

**任务内容**:
1. 创建 `backend/app/core/web_scraper.py`
2. 实现 WebScraper 类
   - 浏览器初始化和管理
   - 页面访问和等待
   - 内容提取（基于选择器）
   - 内容清洗和格式化
   - 错误处理和重试
3. 集成 Playwright
4. 实现内容处理管道
   - HTML清洗（BeautifulSoup4）
   - HTML转Markdown（html2text）
   - 文本分块（与现有RAG系统对接）
5. 添加配置管理

**交付物**:
- `backend/app/core/web_scraper.py`
- Playwright配置文件
- 内容处理工具函数

---

### 任务 5: 任务调度系统
**负责人**: 后端开发 (backend-dev)
**优先级**: P0
**依赖**: 任务 4 完成
**预计工时**: 2-3 天

**任务内容**:
1. 创建 `backend/app/core/scheduler.py`
2. 实现 ScraperScheduler 类
   - APScheduler集成
   - Cron表达式解析
   - 任务添加/删除/暂停/恢复
   - 并发控制
   - 任务执行监控
3. 实现调度器生命周期管理
4. 添加Redis分布式锁（防止重复执行）
5. 实现任务执行回调

**交付物**:
- `backend/app/core/scheduler.py`
- 调度器配置文件
- 分布式锁实现

---

### 任务 6: 业务服务层
**负责人**: 后端开发 (backend-dev)
**优先级**: P0
**依赖**: 任务 3、4、5 完成
**预计工时**: 3 天

**任务内容**:
1. 创建 `backend/app/services/web_scraper_service.py`
2. 实现 WebScraperService 类
   - 任务管理（CRUD）
   - 任务启动/停止
   - 采集执行协调
   - 知识库集成
   - 权限检查
3. 实现采集执行流程
   - 调用WebScraper采集内容
   - 内容分块和向量化
   - 存储到知识库
   - 记录执行日志
4. 实现错误处理和重试逻辑
5. 添加统计和监控

**交付物**:
- `backend/app/services/web_scraper_service.py`
- 业务逻辑文档

---

### 任务 7: Pydantic Schemas
**负责人**: API 开发 (api-dev)
**优先级**: P0
**依赖**: 任务 3 完成
**预计工时**: 1 天

**任务内容**:
1. 创建 `backend/app/schemas/web_scraper.py`
2. 定义请求/响应模型
   - TaskCreate
   - TaskUpdate
   - TaskResponse
   - TaskListResponse
   - LogResponse
   - LogListResponse
   - SelectorConfig
   - ScraperConfig
3. 添加验证规则
4. 添加示例数据

**交付物**:
- `backend/app/schemas/web_scraper.py`
- Schema文档

---

### 任务 8: API 端点实现
**负责人**: API 开发 (api-dev)
**优先级**: P0
**依赖**: 任务 6、7 完成
**预计工时**: 2-3 天

**任务内容**:
1. 创建 `backend/app/api/v1/web_scraper.py`
2. 实现以下端点：
   - `POST /api/v1/scraper/tasks` - 创建任务
   - `GET /api/v1/scraper/tasks` - 获取任务列表
   - `GET /api/v1/scraper/tasks/{id}` - 获取任务详情
   - `PUT /api/v1/scraper/tasks/{id}` - 更新任务
   - `DELETE /api/v1/scraper/tasks/{id}` - 删除任务
   - `POST /api/v1/scraper/tasks/{id}/start` - 启动任务
   - `POST /api/v1/scraper/tasks/{id}/stop` - 停止任务
   - `GET /api/v1/scraper/tasks/{id}/logs` - 获取执行日志
3. 添加认证和权限验证
4. 添加参数验证
5. 添加错误处理
6. 注册路由到主应用

**交付物**:
- `backend/app/api/v1/web_scraper.py`
- API文档更新

---

### 任务 9: 前端API客户端
**负责人**: 前端开发 (frontend-dev)
**优先级**: P1
**依赖**: 任务 8 完成
**预计工时**: 1 天

**任务内容**:
1. 创建 `frontend/src/api/webScraper.ts`
2. 实现API调用方法
   - createTask
   - getTasks
   - getTask
   - updateTask
   - deleteTask
   - startTask
   - stopTask
   - getTaskLogs
3. 添加TypeScript类型定义
4. 添加错误处理

**交付物**:
- `frontend/src/api/webScraper.ts`
- TypeScript类型定义

---

### 任务 10: 前端状态管理
**负责人**: 前端开发 (frontend-dev)
**优先级**: P1
**依赖**: 任务 9 完成
**预计工时**: 1 天

**任务内容**:
1. 创建 `frontend/src/stores/webScraper.ts`
2. 实现Pinia Store
   - 任务列表状态
   - 当前任务状态
   - 执行日志状态
   - 加载状态
3. 实现状态管理方法
   - fetchTasks
   - createTask
   - updateTask
   - deleteTask
   - startTask
   - stopTask
   - fetchLogs
4. 添加错误处理和通知

**交付物**:
- `frontend/src/stores/webScraper.ts`

---

### 任务 11: 前端页面开发 - 任务列表
**负责人**: 前端开发 (frontend-dev)
**优先级**: P1
**依赖**: 任务 10 完成
**预计工时**: 2 天

**任务内容**:
1. 创建 `frontend/src/views/WebScraperView.vue`
2. 实现任务列表页面
   - 任务列表展示（表格）
   - 任务状态显示（active/paused/stopped）
   - 操作按钮（启动/停止/编辑/删除）
   - 分页和搜索
   - 筛选（按状态、按知识库）
3. 添加创建任务按钮
4. 集成到路由

**交付物**:
- `frontend/src/views/WebScraperView.vue`
- 路由配置更新

---

### 任务 12: 前端页面开发 - 任务表单
**负责人**: 前端开发 (frontend-dev)
**优先级**: P1
**依赖**: 任务 11 完成
**预计工时**: 2-3 天

**任务内容**:
1. 创建 `frontend/src/components/WebScraperTaskForm.vue`
2. 实现任务创建/编辑表单
   - 基本信息（名称、描述、URL）
   - 知识库选择
   - 调度配置（一次性/定时）
   - Cron表达式编辑器
   - 选择器配置（JSON编辑器）
   - 采集器配置（JSON编辑器）
3. 添加表单验证
4. 添加配置预览
5. 实现对话框模式

**交付物**:
- `frontend/src/components/WebScraperTaskForm.vue`
- Cron表达式编辑器组件

---

### 任务 13: 前端页面开发 - 执行日志
**负责人**: 前端开发 (frontend-dev)
**优先级**: P1
**依赖**: 任务 11 完成
**预计工时**: 1-2 天

**任务内容**:
1. 创建 `frontend/src/components/WebScraperLogs.vue`
2. 实现执行日志展示
   - 日志列表（时间、状态、结果）
   - 日志详情（执行详情、错误信息）
   - 状态标识（running/success/failed）
   - 统计信息（抓取页面数、创建文档数）
3. 添加日志筛选和搜索
4. 实现自动刷新（正在执行的任务）

**交付物**:
- `frontend/src/components/WebScraperLogs.vue`

---

### 任务 14: 单元测试 - 后端核心模块
**负责人**: 测试工程师 (test-agent)
**优先级**: P1
**依赖**: 任务 4、5 完成
**预计工时**: 2-3 天

**任务内容**:
1. 编写 WebScraper 单元测试
   - `backend/tests/core/test_web_scraper.py`
   - 测试浏览器初始化
   - 测试内容提取
   - 测试内容清洗
   - 测试错误处理
2. 编写 ScraperScheduler 单元测试
   - `backend/tests/core/test_scheduler.py`
   - 测试任务添加/删除
   - 测试Cron表达式解析
   - 测试并发控制
3. Mock Playwright和APScheduler
4. 确保测试覆盖率 > 80%

**交付物**:
- `backend/tests/core/test_web_scraper.py`
- `backend/tests/core/test_scheduler.py`
- 测试覆盖率报告

---

### 任务 15: 单元测试 - 后端服务层
**负责人**: 测试工程师 (test-agent)
**优先级**: P1
**依赖**: 任务 6 完成
**预计工时**: 2 天

**任务内容**:
1. 编写 WebScraperService 单元测试
   - `backend/tests/services/test_web_scraper_service.py`
   - 测试任务CRUD
   - 测试任务启动/停止
   - 测试采集执行流程
   - 测试权限检查
   - 测试错误处理
2. Mock数据库和外部依赖
3. 确保测试覆盖率 > 80%

**交付物**:
- `backend/tests/services/test_web_scraper_service.py`
- 测试覆盖率报告

---

### 任务 16: 单元测试 - API端点
**负责人**: 测试工程师 (test-agent)
**优先级**: P1
**依赖**: 任务 8 完成
**预计工时**: 2 天

**任务内容**:
1. 编写API端点测试
   - `backend/tests/api/v1/test_web_scraper.py`
   - 测试所有端点
   - 测试认证和权限
   - 测试参数验证
   - 测试错误响应
2. 使用TestClient进行集成测试
3. 确保测试覆盖率 > 80%

**交付物**:
- `backend/tests/api/v1/test_web_scraper.py`
- API测试报告

---

### 任务 17: 集成测试
**负责人**: 测试工程师 (test-agent)
**优先级**: P1
**依赖**: 任务 6、8 完成
**预计工时**: 2-3 天

**任务内容**:
1. 编写端到端集成测试
   - `backend/tests/integration/test_web_scraper_integration.py`
   - 测试完整采集流程
   - 测试定时任务执行
   - 测试知识库集成
   - 测试并发采集
2. 使用真实的Playwright浏览器
3. 准备测试网页
4. 验证数据完整性

**交付物**:
- `backend/tests/integration/test_web_scraper_integration.py`
- 集成测试报告

---

### 任务 18: 前端组件测试
**负责人**: 测试工程师 (test-agent)
**优先级**: P2
**依赖**: 任务 11、12、13 完成
**预计工时**: 2 天

**任务内容**:
1. 编写前端组件测试
   - `frontend/src/__tests__/views/WebScraperView.spec.ts`
   - `frontend/src/__tests__/components/WebScraperTaskForm.spec.ts`
   - `frontend/src/__tests__/components/WebScraperLogs.spec.ts`
2. 测试组件渲染
3. 测试用户交互
4. 测试状态管理
5. Mock API调用

**交付物**:
- 前端组件测试文件
- 测试覆盖率报告

---

### 任务 19: 代码审查
**负责人**: 代码审查员 (code-review)
**优先级**: P1
**依赖**: 任务 4、5、6、8 完成
**预计工时**: 2 天

**任务内容**:
1. 审查后端核心模块
   - 代码质量
   - 性能优化
   - 安全性（XSS、注入攻击）
   - 错误处理
2. 审查API端点
   - 接口设计
   - 参数验证
   - 权限控制
3. 审查前端代码
   - 代码规范
   - 用户体验
   - 性能优化
4. 审查测试代码
   - 测试覆盖率
   - 测试质量

**交付物**:
- 代码审查报告
- 改进建议列表

---

### 任务 20: 文档编写
**负责人**: 产品经理 (product)
**优先级**: P1
**依赖**: 任务 8、11、12、13 完成
**预计工时**: 2 天

**任务内容**:
1. 编写用户使用文档
   - 功能介绍
   - 使用指南
   - 配置说明
   - 常见问题
2. 编写API文档
   - 端点说明
   - 请求/响应示例
   - 错误码说明
3. 编写开发者文档
   - 架构说明
   - 扩展指南
   - 故障排查

**交付物**:
- `docs/Phase2-用户使用指南.md`
- `docs/Phase2-API文档.md`
- `docs/Phase2-开发者文档.md`

---

### 任务 21: 部署和配置
**负责人**: DevOps工程师 (devops)
**优先级**: P1
**依赖**: 任务 19 完成
**预计工时**: 1-2 天

**任务内容**:
1. 更新Docker配置
   - 添加Playwright依赖
   - 配置浏览器环境
2. 更新环境变量配置
3. 配置APScheduler持久化
4. 配置Redis分布式锁
5. 编写部署脚本
6. 编写监控脚本

**交付物**:
- 更新的Dockerfile
- 部署脚本
- 监控配置

---

### 任务 22: 验收测试
**负责人**: 产品经理 (product) + 测试工程师 (test-agent)
**优先级**: P1
**依赖**: 任务 21 完成
**预计工时**: 2-3 天

**任务内容**:
1. 准备验收测试用例
2. 执行功能测试
   - 创建采集任务
   - 配置定时调度
   - 执行采集
   - 查看执行日志
   - 验证知识库内容
3. 执行性能测试
   - 并发采集测试
   - 大量任务调度测试
4. 执行安全测试
   - 权限控制测试
   - XSS防护测试
5. 编写验收报告

**交付物**:
- 验收测试用例
- 验收测试报告
- 问题列表

---

## 任务依赖关系图

```
任务1 (架构设计)
  ├─→ 任务2 (数据库迁移)
  │     └─→ 任务3 (数据模型)
  │           └─→ 任务6 (服务层)
  │           └─→ 任务7 (Schemas)
  │                 └─→ 任务8 (API端点)
  │                       └─→ 任务9 (前端API)
  │                             └─→ 任务10 (状态管理)
  │                                   └─→ 任务11 (任务列表)
  │                                         ├─→ 任务12 (任务表单)
  │                                         └─→ 任务13 (执行日志)
  ├─→ 任务4 (浏览器自动化)
  │     └─→ 任务5 (任务调度)
  │           └─→ 任务6 (服务层)
  │
  └─→ 测试任务 (14-18)
        └─→ 任务19 (代码审查)
              └─→ 任务20 (文档)
                    └─→ 任务21 (部署)
                          └─→ 任务22 (验收)
```

---

## 里程碑

### 里程碑 1: 核心功能完成（第2周末）
- ✅ 数据库表创建完成
- ✅ 浏览器自动化模块完成
- ✅ 任务调度系统完成
- ✅ 服务层完成
- ✅ API端点完成

### 里程碑 2: 前端开发完成（第3周末）
- ✅ 前端页面开发完成
- ✅ 前后端联调完成
- ✅ 基本功能可用

### 里程碑 3: 测试和优化完成（第4周中）
- ✅ 单元测试完成
- ✅ 集成测试完成
- ✅ 代码审查完成
- ✅ 性能优化完成

### 里程碑 4: 上线准备完成（第4周末）
- ✅ 文档编写完成
- ✅ 部署配置完成
- ✅ 验收测试通过
- ✅ 准备上线

---

## 风险管理

### 技术风险
1. **Playwright性能问题**
   - 风险: 浏览器资源占用过高
   - 缓解: 限制并发数，使用无头模式，复用浏览器实例

2. **反爬虫机制**
   - 风险: 目标网站封禁IP或拒绝访问
   - 缓解: 添加User-Agent伪装，控制访问频率，支持代理配置

3. **调度器稳定性**
   - 风险: 任务调度失败或重复执行
   - 缓解: 使用Redis分布式锁，添加任务执行监控

### 进度风险
1. **任务复杂度估算不足**
   - 风险: 开发时间超出预期
   - 缓解: 每周进度评审，及时调整计划

2. **依赖任务延期**
   - 风险: 前置任务延期影响后续任务
   - 缓解: 识别关键路径，优先保证关键任务

---

## 资源需求

### 人力资源
- 架构师: 0.5人周
- 后端开发: 2人周
- 前端开发: 1.5人周
- 测试工程师: 1.5人周
- DevOps工程师: 0.5人周
- 产品经理: 0.5人周
- 代码审查员: 0.5人周

### 技术资源
- Playwright浏览器环境
- APScheduler调度器
- Redis（分布式锁）
- 测试服务器

---

## 沟通计划

### 每日站会
- 时间: 每天上午10:00
- 参与人: 全体开发人员
- 内容: 进度同步、问题讨论

### 每周评审
- 时间: 每周五下午3:00
- 参与人: 全体项目成员
- 内容: 里程碑检查、风险评估、计划调整

### 技术评审
- 时间: 关键节点（任务1、6、8完成后）
- 参与人: 架构师、技术负责人
- 内容: 技术方案评审、代码审查

---

## 验收标准

### 功能验收
- ✅ 可以创建、编辑、删除采集任务
- ✅ 支持一次性和定时采集
- ✅ 可以启动、停止任务
- ✅ 采集内容正确存储到知识库
- ✅ 执行日志完整记录
- ✅ 前端界面友好易用

### 性能验收
- ✅ 单个采集任务执行时间 < 5分钟
- ✅ 支持至少5个并发采集任务
- ✅ 调度器延迟 < 10秒

### 质量验收
- ✅ 单元测试覆盖率 > 80%
- ✅ 集成测试通过率 100%
- ✅ 代码审查通过
- ✅ 无P0/P1级别bug

---

## 后续优化计划

1. **Phase 2.1**: 支持JavaScript渲染页面
2. **Phase 2.2**: 支持登录后采集
3. **Phase 2.3**: 支持分布式采集
4. **Phase 2.4**: 智能选择器生成
5. **Phase 2.5**: 内容去重和增量更新
