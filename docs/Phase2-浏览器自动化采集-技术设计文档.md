# Phase 2: 浏览器自动化采集 - 技术设计文档

**文档版本**: v1.0
**创建日期**: 2026-03-04
**作者**: 架构师
**状态**: 待评审

---

## 1. 设计概述

### 1.1 目标

实现基于浏览器自动化的网页内容采集功能，支持定时抓取网页内容并自动存储到知识库，为RAG系统提供持续更新的知识源。

### 1.2 核心功能

1. **网页采集任务管理** - 创建、配置、启动、停止采集任务
2. **定时调度系统** - 支持Cron表达式的定时采集
3. **浏览器自动化** - 使用Playwright进行网页内容抓取
4. **内容处理** - 清洗、格式化、分块处理网页内容
5. **知识库集成** - 自动将采集内容存储到指定知识库
6. **任务监控** - 采集任务执行状态、日志、统计信息

### 1.3 技术约束

- 遵循项目4层架构（API → Service → Repository → Infrastructure）
- 使用Playwright作为浏览器自动化引擎
- 使用APScheduler进行任务调度
- 支持异步执行，不阻塞主线程
- 完整的错误处理和重试机制
- 采集内容自动向量化并存储到Chroma

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                  前端 Vue 3 应用                         │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  WebScraperManagement.vue                      │    │
│  │  - 采集任务列表                                │    │
│  │  - 创建/编辑任务                               │    │
│  │  - 启动/停止任务                               │    │
│  │  - 查看执行日志                                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI 后端（API 网关层）                  │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  app/api/v1/web_scraper.py                     │    │
│  │  - POST   /api/v1/scraper/tasks                │    │
│  │  - GET    /api/v1/scraper/tasks                │    │
│  │  - GET    /api/v1/scraper/tasks/{id}           │    │
│  │  - PUT    /api/v1/scraper/tasks/{id}           │    │
│  │  - DELETE /api/v1/scraper/tasks/{id}           │    │
│  │  - POST   /api/v1/scraper/tasks/{id}/start     │    │
│  │  - POST   /api/v1/scraper/tasks/{id}/stop      │    │
│  │  - GET    /api/v1/scraper/tasks/{id}/logs      │    │
│  └────────────────────────────────────────────────┘    │
│                          │                              │
│                          ▼                              │
│  ┌────────────────────────────────────────────────┐    │
│  │  app/services/web_scraper_service.py           │    │
│  │  - 任务管理逻辑                                │    │
│  │  - 调度器管理                                  │    │
│  │  - 采集执行协调                                │    │
│  └────────────────────────────────────────────────┘    │
│                          │                              │
│                          ▼                              │
│  ┌────────────────────────────────────────────────┐    │
│  │  app/core/web_scraper.py                       │    │
│  │  - Playwright浏览器控制                        │    │
│  │  - 网页内容提取                                │    │
│  │  - 内容清洗和格式化                            │    │
│  └────────────────────────────────────────────────┘    │
│                          │                              │
│                          ▼                              │
│  ┌────────────────────────────────────────────────┐    │
│  │  app/core/scheduler.py                         │    │
│  │  - APScheduler调度器                           │    │
│  │  - Cron任务管理                                │    │
│  │  - 任务执行监控                                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   数据存储层                             │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   MySQL      │  │   Chroma     │  │   Redis      │ │
│  │  任务配置    │  │  向量存储    │  │  任务状态    │ │
│  │  执行日志    │  │  文档内容    │  │  调度锁      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据模型

#### 采集任务表 (web_scraper_tasks)

```sql
CREATE TABLE web_scraper_tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL COMMENT '任务名称',
    description TEXT COMMENT '任务描述',
    url VARCHAR(500) NOT NULL COMMENT '目标URL',
    url_pattern VARCHAR(500) COMMENT 'URL匹配模式（支持通配符）',
    knowledge_base_id INT NOT NULL COMMENT '目标知识库ID',
    schedule_type ENUM('once', 'cron') DEFAULT 'once' COMMENT '调度类型',
    cron_expression VARCHAR(100) COMMENT 'Cron表达式',
    selector_config JSON COMMENT '选择器配置',
    scraper_config JSON COMMENT '采集器配置',
    status ENUM('active', 'paused', 'stopped') DEFAULT 'active',
    last_run_at DATETIME COMMENT '最后执行时间',
    next_run_at DATETIME COMMENT '下次执行时间',
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_status (status),
    INDEX idx_next_run (next_run_at)
);
```

#### 采集执行日志表 (web_scraper_logs)

```sql
CREATE TABLE web_scraper_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id INT NOT NULL,
    status ENUM('running', 'success', 'failed') DEFAULT 'running',
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    pages_scraped INT DEFAULT 0 COMMENT '抓取页面数',
    documents_created INT DEFAULT 0 COMMENT '创建文档数',
    error_message TEXT COMMENT '错误信息',
    execution_details JSON COMMENT '执行详情',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES web_scraper_tasks(id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time)
);
```

### 2.3 核心组件设计

#### 2.3.1 WebScraper 类

```python
class WebScraper:
    """浏览器自动化采集器"""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.browser = None
        self.page = None

    async def initialize(self):
        """初始化浏览器"""
        self.browser = await async_playwright().start()
        self.page = await self.browser.chromium.launch()

    async def scrape_url(self, url: str) -> ScrapedContent:
        """抓取单个URL"""
        pass

    async def extract_content(self, selectors: Dict) -> str:
        """提取页面内容"""
        pass

    async def clean_content(self, raw_content: str) -> str:
        """清洗内容"""
        pass

    async def close(self):
        """关闭浏览器"""
        pass
```

#### 2.3.2 ScraperScheduler 类

```python
class ScraperScheduler:
    """采集任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running_tasks = {}

    def add_task(self, task: WebScraperTask):
        """添加调度任务"""
        pass

    def remove_task(self, task_id: int):
        """移除调度任务"""
        pass

    def pause_task(self, task_id: int):
        """暂停任务"""
        pass

    def resume_task(self, task_id: int):
        """恢复任务"""
        pass

    async def execute_task(self, task_id: int):
        """执行采集任务"""
        pass
```

#### 2.3.3 WebScraperService 类

```python
class WebScraperService:
    """采集服务层"""

    def __init__(self, db: Session):
        self.db = db
        self.task_repo = WebScraperTaskRepository(db)
        self.log_repo = WebScraperLogRepository(db)
        self.scheduler = ScraperScheduler()

    def create_task(self, task_data: TaskCreate) -> WebScraperTask:
        """创建采集任务"""
        pass

    def start_task(self, task_id: int):
        """启动任务"""
        pass

    def stop_task(self, task_id: int):
        """停止任务"""
        pass

    async def execute_scraping(self, task: WebScraperTask):
        """执行采集"""
        pass
```

---

## 3. 技术选型

### 3.1 浏览器自动化

**选择**: Playwright

**理由**:
- 支持Chromium、Firefox、WebKit多种浏览器
- 异步API，性能优秀
- 支持无头模式，资源占用低
- 强大的选择器和等待机制
- 活跃的社区和完善的文档

**替代方案**:
- Selenium: 较老，性能较差
- Puppeteer: 仅支持Chromium

### 3.2 任务调度

**选择**: APScheduler

**理由**:
- 支持Cron表达式
- 支持异步任务
- 轻量级，易于集成
- 支持任务持久化

**替代方案**:
- Celery: 过于重量级，需要额外的消息队列
- Airflow: 适合复杂DAG，本场景过度设计

### 3.3 内容处理

**选择**: BeautifulSoup4 + html2text

**理由**:
- BeautifulSoup4: HTML解析和清洗
- html2text: HTML转Markdown
- 轻量级，易于使用

---

## 4. 关键流程

### 4.1 创建采集任务流程

```
用户 → 前端表单 → POST /api/v1/scraper/tasks
    ↓
验证任务配置（URL、Cron表达式、知识库权限）
    ↓
创建数据库记录
    ↓
添加到调度器
    ↓
返回任务信息
```

### 4.2 执行采集流程

```
调度器触发 → execute_task(task_id)
    ↓
创建执行日志（status=running）
    ↓
初始化WebScraper
    ↓
访问目标URL
    ↓
提取内容（根据selector_config）
    ↓
清洗和格式化内容
    ↓
分块处理（chunk_size=1000, overlap=200）
    ↓
向量化（DashScope Embedding）
    ↓
存储到知识库（Chroma + MySQL）
    ↓
更新执行日志（status=success/failed）
    ↓
更新任务的last_run_at和next_run_at
```

### 4.3 错误处理流程

```
采集失败
    ↓
记录错误信息到日志
    ↓
判断是否需要重试
    ↓
是 → 延迟后重试（最多3次）
    ↓
否 → 标记任务失败
    ↓
发送通知（可选）
```

---

## 5. 配置示例

### 5.1 选择器配置 (selector_config)

```json
{
  "title": "h1.article-title",
  "content": "div.article-content",
  "author": "span.author-name",
  "publish_date": "time.publish-date",
  "exclude": [".advertisement", ".sidebar"]
}
```

### 5.2 采集器配置 (scraper_config)

```json
{
  "wait_for_selector": "div.article-content",
  "wait_timeout": 30000,
  "screenshot": false,
  "user_agent": "Mozilla/5.0...",
  "headers": {
    "Accept-Language": "zh-CN,zh;q=0.9"
  },
  "retry_times": 3,
  "retry_delay": 5
}
```

### 5.3 Cron表达式示例

```
0 0 * * *        # 每天凌晨0点
0 */6 * * *      # 每6小时
0 9 * * 1        # 每周一上午9点
0 0 1 * *        # 每月1号凌晨0点
```

---

## 6. 安全考虑

### 6.1 访问控制

- 只有任务创建者和管理员可以修改/删除任务
- 知识库权限检查：用户必须对目标知识库有写权限
- URL白名单：可配置允许采集的域名列表

### 6.2 资源限制

- 单个任务最大执行时间：30分钟
- 并发采集任务数：最多5个
- 单次采集最大页面数：100页
- 采集频率限制：同一域名最小间隔5秒

### 6.3 内容安全

- XSS防护：清洗HTML标签
- 敏感信息过滤：不采集包含敏感词的内容
- 版权检查：添加来源标注

---

## 7. 性能优化

### 7.1 浏览器优化

- 使用无头模式
- 禁用图片加载（可选）
- 禁用CSS加载（可选）
- 复用浏览器实例

### 7.2 并发控制

- 使用信号量限制并发数
- 异步执行，不阻塞主线程
- 使用连接池管理数据库连接

### 7.3 缓存策略

- Redis缓存已采集URL（24小时）
- 避免重复采集相同内容

---

## 8. 监控和日志

### 8.1 监控指标

- 任务执行成功率
- 平均执行时间
- 采集页面数统计
- 错误类型分布

### 8.2 日志级别

- INFO: 任务启动、完成
- WARNING: 重试、超时
- ERROR: 采集失败、系统错误

---

## 9. 扩展性设计

### 9.1 支持多种采集模式

- 单页采集
- 列表页+详情页采集
- 深度爬取（跟随链接）
- API采集（JSON数据）

### 9.2 插件化架构

- 自定义内容提取器
- 自定义内容处理器
- 自定义存储适配器

---

## 10. 部署要求

### 10.1 依赖安装

```bash
pip install playwright apscheduler beautifulsoup4 html2text
playwright install chromium
```

### 10.2 环境变量

```env
SCRAPER_MAX_CONCURRENT_TASKS=5
SCRAPER_DEFAULT_TIMEOUT=30000
SCRAPER_ENABLE_SCREENSHOT=false
SCRAPER_USER_AGENT="Mozilla/5.0..."
```

---

## 11. 测试策略

### 11.1 单元测试

- WebScraper类测试
- ScraperScheduler类测试
- 内容提取和清洗测试

### 11.2 集成测试

- 完整采集流程测试
- 调度器触发测试
- 知识库集成测试

### 11.3 端到端测试

- 创建任务 → 执行采集 → 验证知识库内容

---

## 12. 风险和挑战

### 12.1 技术风险

- 目标网站反爬虫机制
- 网页结构变化导致选择器失效
- 浏览器资源占用过高

### 12.2 缓解措施

- 添加User-Agent和Headers伪装
- 支持选择器配置更新
- 限制并发数和执行时间
- 提供手动重试机制

---

## 13. 后续优化方向

1. 支持JavaScript渲染页面
2. 支持登录后采集
3. 支持分布式采集
4. 智能选择器生成（AI辅助）
5. 内容去重和增量更新
6. 采集结果预览和审核
