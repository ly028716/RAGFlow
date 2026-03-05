"""URL验证器测试

测试URL安全验证功能，确保SSRF防护有效。
"""
import pytest

from app.core.url_validator import URLValidator, URLValidationError, validate_scraper_url, is_safe_url


class TestURLValidator:
    """URL验证器测试类"""

    def test_valid_http_url(self):
        """测试有效的HTTP URL"""
        url = "http://example.com/page"
        # 允许内网访问模式（测试用）
        assert URLValidator.validate_url(url, allow_private=True) is True

    def test_valid_https_url(self):
        """测试有效的HTTPS URL"""
        url = "https://example.com/page"
        assert URLValidator.validate_url(url, allow_private=True) is True

    def test_invalid_protocol(self):
        """测试无效的协议"""
        url = "ftp://example.com/file"
        with pytest.raises(URLValidationError, match="不支持的协议"):
            URLValidator.validate_url(url)

    def test_javascript_protocol(self):
        """测试JavaScript协议（XSS风险）"""
        url = "javascript:alert('xss')"
        with pytest.raises(URLValidationError, match="不支持的协议"):
            URLValidator.validate_url(url)

    def test_missing_hostname(self):
        """测试缺少主机名"""
        url = "http://"
        with pytest.raises(URLValidationError, match="URL缺少主机名"):
            URLValidator.validate_url(url)

    def test_localhost_blocked(self):
        """测试localhost被阻止"""
        url = "http://localhost:8000/api"
        with pytest.raises(URLValidationError, match="禁止访问的主机名"):
            URLValidator.validate_url(url)

    def test_127_0_0_1_blocked(self):
        """测试127.0.0.1被阻止"""
        url = "http://127.0.0.1:8000/api"
        with pytest.raises(URLValidationError, match="禁止访问内网IP"):
            URLValidator.validate_url(url)

    def test_private_ip_10_blocked(self):
        """测试10.x.x.x内网IP被阻止"""
        url = "http://10.0.0.1/api"
        with pytest.raises(URLValidationError, match="禁止访问内网IP"):
            URLValidator.validate_url(url)

    def test_private_ip_172_blocked(self):
        """测试172.16-31.x.x内网IP被阻止"""
        url = "http://172.16.0.1/api"
        with pytest.raises(URLValidationError, match="禁止访问内网IP"):
            URLValidator.validate_url(url)

    def test_private_ip_192_blocked(self):
        """测试192.168.x.x内网IP被阻止"""
        url = "http://192.168.1.1/api"
        with pytest.raises(URLValidationError, match="禁止访问内网IP"):
            URLValidator.validate_url(url)

    def test_aws_metadata_blocked(self):
        """测试AWS元数据端点被阻止"""
        url = "http://169.254.169.254/latest/meta-data/"
        with pytest.raises(URLValidationError, match="(禁止访问内网IP|禁止访问的主机名)"):
            URLValidator.validate_url(url)

    def test_ipv6_localhost_blocked(self):
        """测试IPv6 localhost被阻止"""
        url = "http://[::1]:8000/api"
        with pytest.raises(URLValidationError, match="禁止访问内网IP"):
            URLValidator.validate_url(url)

    def test_allow_private_networks_flag(self):
        """测试允许内网访问标志"""
        url = "http://192.168.1.1/api"
        # 允许内网访问
        assert URLValidator.validate_url(url, allow_private=True) is True

    def test_url_pattern_validation_valid(self):
        """测试有效的URL模式"""
        pattern = "https://example.com/blog/*"
        assert URLValidator.validate_url_pattern(pattern) is True

    def test_url_pattern_validation_wildcard(self):
        """测试通配符URL模式"""
        pattern = "https://*.example.com/api"
        assert URLValidator.validate_url_pattern(pattern) is True

    def test_url_pattern_validation_dangerous_chars(self):
        """测试包含危险字符的URL模式"""
        pattern = "https://example.com/<script>alert('xss')</script>"
        with pytest.raises(URLValidationError, match="URL模式包含危险字符"):
            URLValidator.validate_url_pattern(pattern)

    def test_url_pattern_validation_too_many_wildcards(self):
        """测试过多通配符的URL模式"""
        pattern = "https://*.*.*/*.html"
        with pytest.raises(URLValidationError, match="URL模式中通配符过多"):
            URLValidator.validate_url_pattern(pattern)

    def test_url_pattern_validation_none(self):
        """测试None URL模式"""
        assert URLValidator.validate_url_pattern(None) is True


class TestURLValidatorWithWhitelist:
    """URL验证器白名单测试类"""

    def test_whitelist_exact_match(self, monkeypatch):
        """测试白名单精确匹配"""
        # 模拟配置白名单
        from app.config import settings
        # 设置url_whitelist字段，url_whitelist_list属性会自动解析
        monkeypatch.setattr(settings.scraper, 'url_whitelist', 'example.com,test.com')

        url = "https://example.com/page"
        assert URLValidator.validate_url(url) is True

    def test_whitelist_wildcard_match(self, monkeypatch):
        """测试白名单通配符匹配"""
        from app.config import settings
        monkeypatch.setattr(settings.scraper, 'url_whitelist', '*.example.com')

        url = "https://blog.example.com/post"
        assert URLValidator.validate_url(url) is True

    def test_whitelist_not_match(self, monkeypatch):
        """测试不在白名单中的URL"""
        from app.config import settings
        monkeypatch.setattr(settings.scraper, 'url_whitelist', 'example.com')

        url = "https://evil.com/page"
        with pytest.raises(URLValidationError, match="URL不在白名单中"):
            URLValidator.validate_url(url)

    def test_whitelist_empty_allows_all(self, monkeypatch):
        """测试空白名单允许所有（除了内网）"""
        from app.config import settings
        monkeypatch.setattr(settings.scraper, 'url_whitelist', '')

        url = "https://example.com/page"
        assert URLValidator.validate_url(url) is True


class TestConvenienceFunctions:
    """便捷函数测试类"""

    def test_validate_scraper_url_success(self):
        """测试validate_scraper_url成功"""
        url = "https://example.com/page"
        # 不应抛出异常
        validate_scraper_url(url)

    def test_validate_scraper_url_failure(self):
        """测试validate_scraper_url失败"""
        url = "http://localhost/api"
        with pytest.raises(URLValidationError):
            validate_scraper_url(url)

    def test_is_safe_url_true(self):
        """测试is_safe_url返回True"""
        url = "https://example.com/page"
        assert is_safe_url(url) is True

    def test_is_safe_url_false(self):
        """测试is_safe_url返回False"""
        url = "http://localhost/api"
        assert is_safe_url(url) is False
