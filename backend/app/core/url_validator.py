"""URL安全验证模块

防止SSRF攻击，验证用户提供的URL是否安全。
"""
import ipaddress
import re
from typing import Optional, Union
from urllib.parse import urlparse

from app.config import settings


class URLValidationError(Exception):
    """URL验证失败异常"""
    pass


class URLValidator:
    """URL安全验证器"""

    # 禁止访问的内网IP段
    PRIVATE_IP_RANGES = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16'),
        ipaddress.ip_network('127.0.0.0/8'),  # localhost
        ipaddress.ip_network('169.254.0.0/16'),  # link-local (AWS metadata)
        ipaddress.ip_network('::1/128'),  # IPv6 localhost
        ipaddress.ip_network('fc00::/7'),  # IPv6 private
        ipaddress.ip_network('fe80::/10'),  # IPv6 link-local
    ]

    # 禁止访问的主机名
    BLOCKED_HOSTNAMES = {
        'localhost',
        '0.0.0.0',
        'metadata.google.internal',  # GCP metadata
        '169.254.169.254',  # AWS/Azure metadata
    }

    @classmethod
    def validate_url(cls, url: str, allow_private: bool = False) -> bool:
        """验证URL是否安全

        Args:
            url: 要验证的URL
            allow_private: 是否允许访问内网地址（仅用于测试）

        Returns:
            bool: URL是否安全

        Raises:
            URLValidationError: URL验证失败
        """
        # 解析URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise URLValidationError(f"URL格式无效: {str(e)}")

        # 检查协议
        if parsed.scheme not in ['http', 'https']:
            raise URLValidationError(f"不支持的协议: {parsed.scheme}，仅支持 http/https")

        # 检查主机名
        hostname = parsed.hostname
        if not hostname:
            raise URLValidationError("URL缺少主机名")

        # 检查是否在黑名单中
        if hostname.lower() in cls.BLOCKED_HOSTNAMES:
            raise URLValidationError(f"禁止访问的主机名: {hostname}")

        # 如果允许内网访问（测试模式），跳过IP检查
        if allow_private:
            return True

        # 检查是否为IP地址
        try:
            ip = ipaddress.ip_address(hostname)
            if cls._is_private_ip(ip):
                raise URLValidationError(f"禁止访问内网IP: {hostname}")
        except ValueError:
            # 不是IP地址，是域名，需要检查白名单
            pass

        # 检查白名单（如果配置了）
        if settings.scraper.url_whitelist:
            if not cls._check_whitelist(hostname):
                raise URLValidationError(
                    f"URL不在白名单中: {hostname}。"
                    f"允许的域名: {', '.join(settings.scraper.url_whitelist)}"
                )

        return True

    @classmethod
    def _is_private_ip(cls, ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
        """检查IP是否为内网地址

        Args:
            ip: IP地址对象

        Returns:
            bool: 是否为内网地址
        """
        for network in cls.PRIVATE_IP_RANGES:
            if ip in network:
                return True
        return False

    @classmethod
    def _check_whitelist(cls, hostname: str) -> bool:
        """检查主机名是否在白名单中

        支持精确匹配和通配符匹配（*.example.com）

        Args:
            hostname: 主机名

        Returns:
            bool: 是否在白名单中
        """
        whitelist = settings.scraper.url_whitelist_list
        if not whitelist:
            return True  # 未配置白名单，允许所有

        hostname_lower = hostname.lower()

        for pattern in whitelist:
            pattern_lower = pattern.lower()

            # 精确匹配
            if hostname_lower == pattern_lower:
                return True

            # 通配符匹配 (*.example.com)
            if pattern_lower.startswith('*.'):
                domain = pattern_lower[2:]
                if hostname_lower.endswith(f'.{domain}') or hostname_lower == domain:
                    return True

        return False

    @classmethod
    def validate_url_pattern(cls, pattern: Optional[str]) -> bool:
        """验证URL模式是否有效

        Args:
            pattern: URL模式（支持通配符）

        Returns:
            bool: 模式是否有效

        Raises:
            URLValidationError: 模式验证失败
        """
        if not pattern:
            return True

        # 检查是否包含危险字符
        dangerous_chars = ['<', '>', '"', "'", '`', '\n', '\r']
        for char in dangerous_chars:
            if char in pattern:
                raise URLValidationError(f"URL模式包含危险字符: {char}")

        # 验证通配符使用是否合理
        if '*' in pattern:
            # 通配符只能出现在域名部分
            if pattern.count('*') > 2:
                raise URLValidationError("URL模式中通配符过多")

        return True


# 便捷函数
def validate_scraper_url(url: str) -> None:
    """验证采集器URL（抛出异常）

    Args:
        url: 要验证的URL

    Raises:
        URLValidationError: URL验证失败
    """
    URLValidator.validate_url(url)


def is_safe_url(url: str) -> bool:
    """检查URL是否安全（返回布尔值）

    Args:
        url: 要验证的URL

    Returns:
        bool: URL是否安全
    """
    try:
        URLValidator.validate_url(url)
        return True
    except URLValidationError:
        return False
