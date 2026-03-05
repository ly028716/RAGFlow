#!/bin/bash
# 测试运行脚本 - 运行所有测试

set -e

echo "=========================================="
echo "AI智能助手系统 - 测试套件"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 运行测试函数
run_test() {
    local test_name=$1
    local test_command=$2

    echo ""
    echo "=========================================="
    echo "运行: $test_name"
    echo "=========================================="

    if eval "$test_command"; then
        echo -e "${GREEN}✓ $test_name 通过${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ $test_name 失败${NC}"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
}

# 检查是否在backend目录
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}错误: 请在backend目录下运行此脚本${NC}"
    exit 1
fi

# 解析命令行参数
TEST_TYPE=${1:-all}
COVERAGE=${2:-false}

echo "测试类型: $TEST_TYPE"
echo "生成覆盖率报告: $COVERAGE"
echo ""

# 基础pytest命令
PYTEST_CMD="python -m pytest -v"
if [ "$COVERAGE" = "true" ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term"
fi

case $TEST_TYPE in
    "unit")
        echo "运行单元测试..."
        run_test "核心模块测试" "$PYTEST_CMD tests/core/"
        run_test "Schema验证测试" "$PYTEST_CMD tests/schemas/"
        ;;

    "service")
        echo "运行服务层测试..."
        run_test "服务层测试" "$PYTEST_CMD tests/services/"
        ;;

    "api")
        echo "运行API测试..."
        run_test "API端点测试" "$PYTEST_CMD tests/api/"
        ;;

    "integration")
        echo "运行集成测试..."
        run_test "集成测试" "$PYTEST_CMD tests/integration/"
        ;;

    "web-scraper")
        echo "运行Web Scraper相关测试..."
        run_test "Web Scraper核心测试" "$PYTEST_CMD tests/core/test_web_scraper.py"
        run_test "Web Scraper调度器测试" "$PYTEST_CMD tests/core/test_scheduler.py"
        run_test "URL验证器测试" "$PYTEST_CMD tests/core/test_url_validator.py"
        run_test "Web Scraper服务测试" "$PYTEST_CMD tests/services/test_web_scraper_service.py"
        run_test "Web Scraper API测试" "$PYTEST_CMD tests/api/v1/test_web_scraper.py"
        run_test "Web Scraper集成测试" "$PYTEST_CMD tests/integration/test_web_scraper_integration.py"
        ;;

    "all")
        echo "运行所有测试..."
        run_test "所有测试" "$PYTEST_CMD tests/"
        ;;

    *)
        echo -e "${RED}错误: 未知的测试类型 '$TEST_TYPE'${NC}"
        echo "用法: $0 [unit|service|api|integration|web-scraper|all] [true|false]"
        echo "示例: $0 web-scraper true  # 运行Web Scraper测试并生成覆盖率报告"
        exit 1
        ;;
esac

# 打印测试结果摘要
echo ""
echo "=========================================="
echo "测试结果摘要"
echo "=========================================="
echo "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}所有测试通过！${NC}"

    if [ "$COVERAGE" = "true" ]; then
        echo ""
        echo "覆盖率报告已生成: htmlcov/index.html"
    fi

    exit 0
else
    echo -e "${RED}有测试失败，请检查日志${NC}"
    exit 1
fi
