# Phase 2: 浏览器自动化采集 - 测试完善任务分配计划

**文档版本**: v1.0
**创建日期**: 2026-03-05
**负责人**: 测试经理
**状态**: 待执行

---

## 📊 执行摘要

### 当前测试覆盖情况

**已完成测试**（约70%）:
- ✅ 前端Store单元测试（410行，覆盖率95%）
- ✅ 前端组件测试（WebScraperTaskForm: 333行，WebScraperLogs: 535行）
- ✅ 后端API测试（323行，覆盖CRUD和控制操作）
- ✅ 后端核心采集器测试（268行，覆盖浏览器管理和内容提取）
- ✅ 后端集成测试（285行，覆盖完整工作流程）

**待完善测试**（约30%）:
- ❌ E2E端到端测试（0%）
- ❌ 性能测试和压力测试（0%）
- ❌ 定时任务调度验证（0%）
- ❌ 错误恢复和重试机制测试（部分）
- ❌ 并发采集场景测试（部分）
- ❌ 前端视图组件测试（WebScraperView.vue）

### 目标

1. **完成度目标**: 将测试覆盖率从70%提升到90%+
2. **质量目标**: 确保所有核心功能通过验收测试
3. **时间目标**: 3-5个工作日完成所有测试任务
4. **验收目标**: 通过Phase 2功能验收

---

## 👥 团队角色分配

### 测试团队

| 角色 | 姓名 | 职责 | 工作量 |
|------|------|------|--------|
| **测试负责人** | [待分配] | 整体协调、进度跟踪、验收把关 | 全程 |
| **后端测试工程师** | [待分配] | 后端单元测试、集成测试、性能测试 | 2-3天 |
| **前端测试工程师** | [待分配] | 前端组件测试、E2E测试 | 2-3天 |
| **QA工程师** | [待分配] | 手动测试、验收测试、测试报告 | 1-2天 |

### 开发支持

| 角色 | 姓名 | 职责 | 工作量 |
|------|------|------|--------|
| **后端工程师** | [待分配] | 修复测试发现的Bug、协助测试环境搭建 | 按需 |
| **前端工程师** | [待分配] | 修复前端Bug、协助E2E测试编写 | 按需 |

---

## 📋 任务清单

### 任务组1: 后端测试完善（优先级P0）

#### 任务1.1: 定时任务调度测试
**负责人**: 后端测试工程师
**预计工作量**: 0.5天
**优先级**: P0

**测试范围**:
- APScheduler调度器初始化和关闭
- Cron表达式解析和任务调度
- 任务执行时间准确性
- 任务并发控制
- 调度器异常恢复

**测试文件**: `backend/tests/core/test_scheduler.py`

**验收标准**:
- [ ] 至少15个测试用例
- [ ] 覆盖所有调度类型（once, cron, interval）
- [ ] 测试通过率100%
- [ ] 代码覆盖率>85%

**测试用例清单**:
```python
# 基础功能测试
- test_scheduler_initialization()
- test_scheduler_shutdown()
- test_add_once_job()
- test_add_cron_job()
- test_add_interval_job()
- test_remove_job()
- test_pause_job()
- test_resume_job()

# 边界情况测试
- test_invalid_cron_expression()
- test_duplicate_job_id()
- test_job_not_found()
- test_concurrent_job_execution()

# 异常处理测试
- test_scheduler_restart_recovery()
- test_job_execution_failure()
- test_max_instances_limit()
```

---

#### 任务1.2: 错误恢复和重试机制测试
**负责人**: 后端测试工程师
**预计工作量**: 0.5天
**优先级**: P0

**测试范围**:
- 网络超时重试
- 页面加载失败重试
- 选择器未找到重试
- 浏览器崩溃恢复
- 重试次数和延迟配置

**测试文件**: `backend/tests/core/test_web_scraper.py`（扩展）

**验收标准**:
- [ ] 至少10个测试用例
- [ ] 覆盖所有重试场景
- [ ] 验证重试次数和延迟
- [ ] 测试通过率100%

**测试用例清单**:
```python
# 重试机制测试
- test_retry_on_network_timeout()
- test_retry_on_page_load_failure()
- test_retry_on_selector_not_found()
- test_retry_with_exponential_backoff()
- test_max_retry_limit()

# 恢复机制测试
- test_browser_crash_recovery()
- test_context_recreation()
- test_page_recreation()
- test_partial_failure_recovery()
- test_graceful_degradation()
```

---

#### 任务1.3: 并发采集场景测试
**负责人**: 后端测试工程师
**预计工作量**: 0.5天
**优先级**: P1

**测试范围**:
- 多任务并发执行
- 浏览器资源管理
- 数据库并发写入
- 内存和CPU使用
- 并发限制控制

**测试文件**: `backend/tests/integration/test_web_scraper_integration.py`（扩展）

**验收标准**:
- [ ] 至少8个测试用例
- [ ] 测试3-10个并发任务
- [ ] 验证资源隔离
- [ ] 测试通过率100%

**测试用例清单**:
```python
# 并发执行测试
- test_concurrent_tasks_execution()
- test_concurrent_browser_instances()
- test_concurrent_database_writes()
- test_resource_isolation()

# 并发控制测试
- test_max_concurrent_tasks_limit()
- test_task_queue_management()
- test_browser_pool_management()
- test_concurrent_error_handling()
```

---

#### 任务1.4: 性能和压力测试
**负责人**: 后端测试工程师
**预计工作量**: 1天
**优先级**: P1

**测试范围**:
- 单任务采集性能
- 批量任务处理能力
- 内存泄漏检测
- 长时间运行稳定性
- 资源使用监控

**测试文件**: `backend/tests/performance/test_web_scraper_performance.py`（新建）

**验收标准**:
- [ ] 至少10个性能测试用例
- [ ] 建立性能基准
- [ ] 生成性能测试报告
- [ ] 识别性能瓶颈

**性能指标**:
- 单页采集时间: <10秒（P95）
- 批量任务处理: >5任务/分钟
- 内存使用: <500MB（10个并发任务）
- CPU使用: <80%（峰值）
- 浏览器启动时间: <3秒

**测试用例清单**:
```python
# 性能基准测试
- test_single_page_scraping_time()
- test_batch_tasks_throughput()
- test_browser_startup_time()
- test_content_extraction_speed()

# 资源使用测试
- test_memory_usage_single_task()
- test_memory_usage_concurrent_tasks()
- test_cpu_usage_under_load()
- test_memory_leak_detection()

# 稳定性测试
- test_long_running_stability()
- test_continuous_task_execution()
```

---

### 任务组2: 前端测试完善（优先级P0）

#### 任务2.1: 前端视图组件测试
**负责人**: 前端测试工程师
**预计工作量**: 0.5天
**优先级**: P0

**测试范围**:
- WebScraperView.vue组件渲染
- 任务列表展示和交互
- 任务创建/编辑流程
- 任务控制操作（启动/停止/暂停）
- 日志查看功能

**测试文件**: `frontend/src/__tests__/views/WebScraperView.spec.ts`（新建）

**验收标准**:
- [ ] 至少20个测试用例
- [ ] 覆盖所有用户交互
- [ ] 测试通过率100%
- [ ] 代码覆盖率>80%

**测试用例清单**:
```typescript
// 组件渲染测试
- test_view_renders_correctly()
- test_empty_state_display()
- test_task_list_display()
- test_pagination_display()

// 任务管理测试
- test_create_task_button_click()
- test_edit_task_button_click()
- test_delete_task_confirmation()
- test_task_form_dialog_display()

// 任务控制测试
- test_start_task_action()
- test_stop_task_action()
- test_pause_task_action()
- test_resume_task_action()

// 日志查看测试
- test_view_logs_button_click()
- test_logs_dialog_display()
- test_logs_auto_refresh()
- test_logs_filter_by_status()

// 状态更新测试
- test_task_status_update()
- test_real_time_status_sync()
- test_error_message_display()
- test_success_message_display()
```

---

#### 任务2.2: E2E端到端测试
**负责人**: 前端测试工程师
**预计工作量**: 1.5天
**优先级**: P0

**测试范围**:
- 完整的用户操作流程
- 前后端集成验证
- 真实浏览器环境测试
- 跨页面导航测试

**测试框架**: Playwright或Cypress

**测试文件**: `frontend/tests/e2e/web-scraper.spec.ts`（新建）

**验收标准**:
- [ ] 至少8个E2E测试场景
- [ ] 覆盖核心用户流程
- [ ] 测试通过率100%
- [ ] 生成测试报告和截图

**E2E测试场景**:
```typescript
// 场景1: 创建并执行一次性采集任务
- 用户登录
- 导航到Web Scraper页面
- 点击"创建任务"按钮
- 填写任务表单（名称、URL、知识库、选择器）
- 提交表单
- 验证任务创建成功
- 点击"启动任务"
- 等待任务执行完成
- 验证日志显示成功
- 验证文档已创建

// 场景2: 创建定时采集任务
- 创建任务并选择"定时执行"
- 填写Cron表达式
- 启动任务
- 验证任务状态为"活动"
- 暂停任务
- 验证任务状态为"已暂停"

// 场景3: 编辑现有任务
- 选择一个任务
- 点击"编辑"按钮
- 修改任务配置
- 保存更改
- 验证更改已生效

// 场景4: 删除任务
- 选择一个任务
- 点击"删除"按钮
- 确认删除
- 验证任务已从列表中移除

// 场景5: 查看任务执行日志
- 选择一个已执行的任务
- 点击"查看日志"
- 验证日志列表显示
- 验证执行详情展示
- 验证统计信息正确

// 场景6: 任务执行失败处理
- 创建一个无效URL的任务
- 启动任务
- 等待任务失败
- 验证错误信息显示
- 验证日志记录失败原因

// 场景7: 并发任务执行
- 创建3个不同的任务
- 同时启动所有任务
- 验证所有任务都在执行
- 等待所有任务完成
- 验证所有任务状态正确

// 场景8: 任务列表分页和筛选
- 创建多个任务（>10个）
- 验证分页功能
- 使用状态筛选
- 验证筛选结果正确
```

---

### 任务组3: 集成和验收测试（优先级P0）

#### 任务3.1: 手动验收测试
**负责人**: QA工程师
**预计工作量**: 1天
**优先级**: P0

**测试范围**:
- 用户故事验收
- UI/UX体验测试
- 跨浏览器兼容性
- 边界情况探索性测试

**测试文档**: `docs/Phase2-验收测试报告.md`（新建）

**验收标准**:
- [ ] 完成所有用户故事验收
- [ ] 发现并记录所有Bug
- [ ] 生成验收测试报告
- [ ] 确认所有P0/P1 Bug已修复

**用户故事验收清单**:
```markdown
## 用户故事1: 创建采集任务
作为用户，我想创建一个网页采集任务，以便自动抓取网页内容到知识库

验收标准:
- [ ] 可以填写任务名称、描述、目标URL
- [ ] 可以选择目标知识库
- [ ] 可以配置选择器（标题、内容、作者等）
- [ ] 可以选择调度类型（一次性/定时）
- [ ] 表单验证正确（必填项、URL格式等）
- [ ] 创建成功后显示在任务列表中

## 用户故事2: 执行采集任务
作为用户，我想启动采集任务，以便立即抓取网页内容

验收标准:
- [ ] 可以点击"启动"按钮
- [ ] 任务状态变为"运行中"
- [ ] 可以实时查看执行进度
- [ ] 执行完成后状态变为"已完成"
- [ ] 可以查看执行日志

## 用户故事3: 定时采集
作为用户，我想设置定时采集，以便定期更新知识库内容

验收标准:
- [ ] 可以选择"定时执行"
- [ ] 可以输入Cron表达式
- [ ] 提供Cron表达式帮助
- [ ] 任务按计划自动执行
- [ ] 可以暂停和恢复定时任务

## 用户故事4: 查看执行日志
作为用户，我想查看任务执行日志，以便了解采集结果和问题

验收标准:
- [ ] 可以查看所有执行记录
- [ ] 显示执行状态（成功/失败/运行中）
- [ ] 显示采集页数和文档数
- [ ] 显示执行时间和耗时
- [ ] 失败时显示错误信息
- [ ] 可以查看详细的执行步骤

## 用户故事5: 管理任务
作为用户，我想编辑和删除任务，以便管理我的采集配置

验收标准:
- [ ] 可以编辑任务配置
- [ ] 可以删除任务（需确认）
- [ ] 删除任务时清理相关数据
- [ ] 可以暂停和恢复任务
- [ ] 可以停止正在运行的任务
```

---

#### 任务3.2: 测试报告编写
**负责人**: 测试负责人
**预计工作量**: 0.5天
**优先级**: P0

**交付物**:
1. **测试覆盖率报告**
   - 后端单元测试覆盖率
   - 前端单元测试覆盖率
   - 集成测试覆盖率
   - E2E测试覆盖率

2. **测试执行报告**
   - 测试用例总数
   - 通过/失败/跳过数量
   - 测试执行时间
   - 失败用例分析

3. **Bug统计报告**
   - Bug总数和严重程度分布
   - Bug修复状态
   - 遗留Bug清单

4. **性能测试报告**
   - 性能指标对比
   - 性能瓶颈分析
   - 优化建议

**报告模板**: `docs/Phase2-测试完成报告.md`

---

## 📅 执行计划

### 第1天（Day 1）

**上午**:
- 测试环境搭建和验证
- 测试数据准备
- 任务1.1: 定时任务调度测试（后端测试工程师）
- 任务2.1: 前端视图组件测试（前端测试工程师）

**下午**:
- 任务1.2: 错误恢复和重试机制测试（后端测试工程师）
- 任务2.1: 前端视图组件测试（继续）（前端测试工程师）

**产出**:
- 定时任务调度测试完成
- 错误恢复测试完成
- 前端视图组件测试完成50%

---

### 第2天（Day 2）

**上午**:
- 任务1.3: 并发采集场景测试（后端测试工程师）
- 任务2.1: 前端视图组件测试（完成）（前端测试工程师）
- 任务2.2: E2E测试环境搭建（前端测试工程师）

**下午**:
- 任务1.4: 性能测试（开始）（后端测试工程师）
- 任务2.2: E2E测试用例编写（前端测试工程师）

**产出**:
- 并发采集测试完成
- 前端视图组件测试完成
- E2E测试环境就绪
- 性能测试完成50%

---

### 第3天（Day 3）

**上午**:
- 任务1.4: 性能测试（完成）（后端测试工程师）
- 任务2.2: E2E测试执行（前端测试工程师）
- 任务3.1: 手动验收测试（开始）（QA工程师）

**下午**:
- Bug修复和回归测试（开发工程师+测试工程师）
- 任务3.1: 手动验收测试（继续）（QA工程师）

**产出**:
- 性能测试完成
- E2E测试完成80%
- 手动验收测试完成50%
- 发现的Bug清单

---

### 第4天（Day 4）

**上午**:
- 任务2.2: E2E测试（完成）（前端测试工程师）
- 任务3.1: 手动验收测试（完成）（QA工程师）
- Bug修复验证（测试工程师）

**下午**:
- 回归测试（全体测试工程师）
- 任务3.2: 测试报告编写（测试负责人）

**产出**:
- E2E测试完成
- 手动验收测试完成
- 所有P0 Bug修复完成
- 测试报告初稿

---

### 第5天（Day 5）- 缓冲和收尾

**上午**:
- 遗留Bug修复
- 补充测试用例
- 测试报告完善

**下午**:
- 最终验收
- 测试报告审核
- 项目交付

**产出**:
- 测试覆盖率>90%
- 所有P0/P1 Bug修复
- 完整的测试报告
- Phase 2功能验收通过

---

## 🎯 验收标准

### 测试覆盖率目标

| 测试类型 | 当前覆盖率 | 目标覆盖率 | 状态 |
|---------|-----------|-----------|------|
| 后端单元测试 | 75% | 90% | 🔄 进行中 |
| 前端单元测试 | 80% | 90% | 🔄 进行中 |
| 集成测试 | 60% | 85% | 🔄 进行中 |
| E2E测试 | 0% | 80% | ❌ 未开始 |
| 性能测试 | 0% | 100% | ❌ 未开始 |

### 质量目标

- [ ] 所有P0优先级测试用例通过率100%
- [ ] 所有P1优先级测试用例通过率>95%
- [ ] 无P0/P1级别的遗留Bug
- [ ] 性能指标达到SLA要求
- [ ] 所有用户故事通过验收

### 交付物清单

- [ ] 完整的测试代码（提交到Git）
- [ ] 测试覆盖率报告
- [ ] 测试执行报告
- [ ] Bug统计报告
- [ ] 性能测试报告
- [ ] 验收测试报告
- [ ] 测试完成总结报告

---

## 🛠 测试环境

### 后端测试环境

```bash
# 环境要求
- Python 3.10+
- MySQL 8.0
- Redis 7.0
- Playwright浏览器

# 安装测试依赖
cd backend
pip install -r requirements-dev.txt
playwright install chromium

# 运行测试
pytest tests/ -v --cov=app --cov-report=html

# 运行特定测试
pytest tests/core/test_scheduler.py -v
pytest tests/integration/test_web_scraper_integration.py -v
```

### 前端测试环境

```bash
# 环境要求
- Node.js 18+
- npm 9+

# 安装测试依赖
cd frontend
npm install

# 运行单元测试
npm run test

# 运行E2E测试
npm run test:e2e

# 生成覆盖率报告
npm run test:coverage
```

---

## 📞 沟通机制

### 日常站会

- **时间**: 每天上午9:30
- **时长**: 15分钟
- **内容**:
  - 昨日完成情况
  - 今日计划
  - 遇到的问题和阻塞

### Bug处理流程

1. **发现Bug** → 测试工程师在Jira/GitHub创建Issue
2. **Bug分类** → 测试负责人评估严重程度（P0/P1/P2）
3. **分配修复** → 分配给相应的开发工程师
4. **修复验证** → 测试工程师验证修复
5. **关闭Bug** → 验证通过后关闭Issue

### 问题升级机制

- **P0 Bug**: 立即通知项目经理，当天必须修复
- **P1 Bug**: 2个工作日内修复
- **P2 Bug**: 本周内修复或推迟到下个版本

---

## 📊 风险管理

### 识别的风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Playwright环境配置问题 | 中 | 高 | 提前准备Docker测试环境 |
| E2E测试不稳定 | 高 | 中 | 增加重试机制和等待时间 |
| 性能测试环境不一致 | 中 | 中 | 使用独立的性能测试环境 |
| Bug修复时间超预期 | 中 | 高 | 预留1天缓冲时间 |
| 测试数据准备不足 | 低 | 中 | 使用种子数据脚本 |

### 应急预案

1. **进度延迟**: 优先完成P0任务，P1任务可推迟
2. **环境问题**: 使用Docker容器化测试环境
3. **人员不足**: 从其他项目临时调配测试人员
4. **严重Bug**: 启动紧急修复流程，延长测试时间

---

## 📝 附录

### A. 测试工具清单

**后端测试**:
- pytest: 单元测试框架
- pytest-cov: 覆盖率统计
- pytest-asyncio: 异步测试支持
- pytest-mock: Mock工具
- locust: 性能测试工具

**前端测试**:
- Vitest: 单元测试框架
- Vue Test Utils: Vue组件测试
- Playwright/Cypress: E2E测试框架
- @vitest/coverage-v8: 覆盖率工具

### B. 测试数据模板

```python
# 示例任务数据
SAMPLE_TASK = {
    "name": "测试采集任务",
    "url": "https://example.com/article",
    "knowledge_base_id": 1,
    "schedule_type": "once",
    "selector_config": {
        "title": "h1.article-title",
        "content": "div.article-content",
        "author": "span.author-name"
    },
    "scraper_config": {
        "wait_for_selector": "article",
        "wait_timeout": 30000,
        "retry_times": 3,
        "retry_delay": 5
    }
}
```

### C. 参考文档

- [Playwright文档](https://playwright.dev/)
- [Pytest文档](https://docs.pytest.org/)
- [Vitest文档](https://vitest.dev/)
- [Vue Test Utils文档](https://test-utils.vuejs.org/)

---

**文档结束**

**下一步行动**:
1. 召开测试启动会议，分配具体人员
2. 搭建测试环境
3. 开始执行测试任务
4. 每日更新进度
