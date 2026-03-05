-- ============================================================================
-- Phase 2: 浏览器自动化采集 - 数据库表结构
-- ============================================================================
-- 创建日期: 2026-03-04
-- 作者: 架构师
-- 版本: v1.0
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 表1: web_scraper_tasks (采集任务表)
-- ----------------------------------------------------------------------------
-- 用途: 存储网页采集任务的配置信息
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS web_scraper_tasks (
    -- 主键
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '任务ID',

    -- 基本信息
    name VARCHAR(200) NOT NULL COMMENT '任务名称',
    description TEXT COMMENT '任务描述',

    -- URL配置
    url VARCHAR(500) NOT NULL COMMENT '目标URL',
    url_pattern VARCHAR(500) COMMENT 'URL匹配模式（支持通配符，用于批量采集）',

    -- 知识库关联
    knowledge_base_id INT NOT NULL COMMENT '目标知识库ID',

    -- 调度配置
    schedule_type ENUM('once', 'cron') DEFAULT 'once' COMMENT '调度类型：once-一次性，cron-定时',
    cron_expression VARCHAR(100) COMMENT 'Cron表达式（仅当schedule_type=cron时有效）',

    -- 采集配置
    selector_config JSON COMMENT '选择器配置（JSON格式）',
    scraper_config JSON COMMENT '采集器配置（JSON格式）',

    -- 状态管理
    status ENUM('active', 'paused', 'stopped') DEFAULT 'active' COMMENT '任务状态：active-活跃，paused-暂停，stopped-停止',

    -- 执行时间
    last_run_at DATETIME COMMENT '最后执行时间',
    next_run_at DATETIME COMMENT '下次执行时间',

    -- 审计字段
    created_by INT NOT NULL COMMENT '创建者用户ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 外键约束
    CONSTRAINT fk_scraper_task_kb FOREIGN KEY (knowledge_base_id)
        REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    CONSTRAINT fk_scraper_task_user FOREIGN KEY (created_by)
        REFERENCES users(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_status (status),
    INDEX idx_next_run (next_run_at),
    INDEX idx_knowledge_base (knowledge_base_id),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='网页采集任务表';

-- ----------------------------------------------------------------------------
-- 表2: web_scraper_logs (采集执行日志表)
-- ----------------------------------------------------------------------------
-- 用途: 记录每次采集任务的执行情况
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS web_scraper_logs (
    -- 主键
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',

    -- 任务关联
    task_id INT NOT NULL COMMENT '任务ID',

    -- 执行状态
    status ENUM('running', 'success', 'failed') DEFAULT 'running' COMMENT '执行状态：running-运行中，success-成功，failed-失败',

    -- 执行时间
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',

    -- 执行统计
    pages_scraped INT DEFAULT 0 COMMENT '抓取页面数',
    documents_created INT DEFAULT 0 COMMENT '创建文档数',

    -- 错误信息
    error_message TEXT COMMENT '错误信息（仅当status=failed时有值）',

    -- 执行详情
    execution_details JSON COMMENT '执行详情（JSON格式，包含URL列表、处理时间等）',

    -- 审计字段
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    -- 外键约束
    CONSTRAINT fk_scraper_log_task FOREIGN KEY (task_id)
        REFERENCES web_scraper_tasks(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='网页采集执行日志表';

-- ============================================================================
-- JSON字段结构说明
-- ============================================================================

-- ----------------------------------------------------------------------------
-- selector_config 字段结构示例
-- ----------------------------------------------------------------------------
-- {
--   "title": "h1.article-title",           // 标题选择器
--   "content": "div.article-content",      // 内容选择器
--   "author": "span.author-name",          // 作者选择器（可选）
--   "publish_date": "time.publish-date",   // 发布日期选择器（可选）
--   "exclude": [".advertisement", ".sidebar"]  // 排除选择器列表
-- }

-- ----------------------------------------------------------------------------
-- scraper_config 字段结构示例
-- ----------------------------------------------------------------------------
-- {
--   "wait_for_selector": "div.article-content",  // 等待的选择器
--   "wait_timeout": 30000,                       // 等待超时时间（毫秒）
--   "screenshot": false,                         // 是否截图
--   "user_agent": "Mozilla/5.0...",              // User-Agent
--   "headers": {                                 // 自定义请求头
--     "Accept-Language": "zh-CN,zh;q=0.9"
--   },
--   "retry_times": 3,                            // 重试次数
--   "retry_delay": 5                             // 重试延迟（秒）
-- }

-- ----------------------------------------------------------------------------
-- execution_details 字段结构示例
-- ----------------------------------------------------------------------------
-- {
--   "urls_processed": [                          // 处理的URL列表
--     "https://example.com/page1",
--     "https://example.com/page2"
--   ],
--   "processing_time": {                         // 处理时间统计
--     "scraping": 10.5,                          // 采集时间（秒）
--     "processing": 5.2,                         // 处理时间（秒）
--     "storing": 2.3                             // 存储时间（秒）
--   },
--   "documents": [                               // 创建的文档列表
--     {
--       "title": "文档标题",
--       "url": "https://example.com/page1",
--       "document_id": 123
--     }
--   ],
--   "errors": []                                 // 错误列表（如果有）
-- }

-- ============================================================================
-- 示例数据
-- ============================================================================

-- 示例1: 一次性采集任务
-- INSERT INTO web_scraper_tasks (
--     name, description, url, knowledge_base_id,
--     schedule_type, selector_config, scraper_config,
--     status, created_by
-- ) VALUES (
--     '技术博客采集',
--     '采集技术博客文章到知识库',
--     'https://example.com/blog/article-1',
--     1,
--     'once',
--     '{"title": "h1.title", "content": "div.content", "exclude": [".ads"]}',
--     '{"wait_for_selector": "div.content", "wait_timeout": 30000, "retry_times": 3}',
--     'active',
--     1
-- );

-- 示例2: 定时采集任务（每天凌晨2点）
-- INSERT INTO web_scraper_tasks (
--     name, description, url, knowledge_base_id,
--     schedule_type, cron_expression, selector_config, scraper_config,
--     status, created_by
-- ) VALUES (
--     '新闻网站每日采集',
--     '每天定时采集新闻网站最新文章',
--     'https://news.example.com/latest',
--     2,
--     'cron',
--     '0 2 * * *',
--     '{"title": "h2.news-title", "content": "div.news-body", "publish_date": "time.date"}',
--     '{"wait_for_selector": "div.news-body", "wait_timeout": 30000, "retry_times": 3}',
--     'active',
--     1
-- );

-- ============================================================================
-- 查询示例
-- ============================================================================

-- 查询所有活跃的定时任务
-- SELECT * FROM web_scraper_tasks
-- WHERE status = 'active' AND schedule_type = 'cron'
-- ORDER BY next_run_at ASC;

-- 查询某个任务的最近10次执行日志
-- SELECT * FROM web_scraper_logs
-- WHERE task_id = 1
-- ORDER BY start_time DESC
-- LIMIT 10;

-- 查询某个知识库的所有采集任务
-- SELECT t.*,
--        COUNT(l.id) as total_runs,
--        SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END) as success_runs
-- FROM web_scraper_tasks t
-- LEFT JOIN web_scraper_logs l ON t.id = l.task_id
-- WHERE t.knowledge_base_id = 1
-- GROUP BY t.id;

-- 查询最近24小时的采集统计
-- SELECT
--     DATE_FORMAT(start_time, '%Y-%m-%d %H:00:00') as hour,
--     COUNT(*) as total_runs,
--     SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_runs,
--     SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
--     SUM(pages_scraped) as total_pages,
--     SUM(documents_created) as total_documents
-- FROM web_scraper_logs
-- WHERE start_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
-- GROUP BY hour
-- ORDER BY hour DESC;

-- ============================================================================
-- 维护操作
-- ============================================================================

-- 清理30天前的执行日志
-- DELETE FROM web_scraper_logs
-- WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 重置失败任务的状态
-- UPDATE web_scraper_tasks
-- SET status = 'active'
-- WHERE status = 'stopped' AND id IN (1, 2, 3);
