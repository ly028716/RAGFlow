"""
Web Scraper 服务异常模块

定义 Web Scraper 相关的所有异常类。
"""


class WebScraperServiceError(Exception):
    """Web Scraper服务异常基类"""
    pass


class TaskNotFoundError(WebScraperServiceError):
    """任务不存在异常"""
    pass


class TaskAlreadyRunningError(WebScraperServiceError):
    """任务已在运行中异常"""
    pass


class InvalidTaskConfigError(WebScraperServiceError):
    """任务配置无效异常"""
    pass


class KnowledgeBaseAccessError(WebScraperServiceError):
    """知识库访问异常"""
    pass


__all__ = [
    "WebScraperServiceError",
    "TaskNotFoundError",
    "TaskAlreadyRunningError",
    "InvalidTaskConfigError",
    "KnowledgeBaseAccessError",
]
