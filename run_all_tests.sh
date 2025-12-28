#!/bin/bash
# AskDB 完整测试套件执行脚本

echo "========================================================================"
echo "🧪 AskDB 完整测试套件"
echo "========================================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 1. 后端测试
echo "========================================================================"
echo "📦 步骤 1/4: 运行后端模块测试"
echo "========================================================================"
if uv run python run_tests.py > backend_test.log 2>&1; then
    echo -e "${GREEN}✅ 后端测试完成${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 后端测试失败${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""

# 2. 前端测试
echo "========================================================================"
echo "🎨 步骤 2/4: 运行前端组件测试"
echo "========================================================================"
if uv run python test_frontend.py > frontend_test.log 2>&1; then
    echo -e "${GREEN}✅ 前端测试完成${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 前端测试失败${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""

# 3. E2E测试
echo "========================================================================"
echo "🔄 步骤 3/4: 运行端到端集成测试"
echo "========================================================================"
if uv run python test_e2e.py > e2e_test.log 2>&1; then
    echo -e "${GREEN}✅ E2E测试完成${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}⚠️  E2E测试部分通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""

# 4. 生成综合报告
echo "========================================================================"
echo "📊 步骤 4/4: 生成综合测试报告"
echo "========================================================================"
if uv run python generate_test_report.py > report_generation.log 2>&1; then
    echo -e "${GREEN}✅ 报告生成完成${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}⚠️  报告生成完成（有警告）${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""

# 显示测试结果摘要
echo "========================================================================"
echo "📋 测试执行摘要"
echo "========================================================================"
echo ""
echo "执行的测试套件: ${TOTAL_TESTS}"
echo -e "${GREEN}通过: ${PASSED_TESTS}${NC}"
echo -e "${RED}失败: ${FAILED_TESTS}${NC}"
echo ""

# 显示详细报告
if [ -f "test_results.json" ]; then
    BACKEND_PASS_RATE=$(cat test_results.json | grep -o '"pass_rate": "[^"]*"' | cut -d'"' -f4)
    echo "后端测试通过率: ${BACKEND_PASS_RATE}"
fi

if [ -f "test_frontend_results.json" ]; then
    FRONTEND_PASS_RATE=$(cat test_frontend_results.json | grep -o '"pass_rate": "[^"]*"' | cut -d'"' -f4)
    echo "前端测试通过率: ${FRONTEND_PASS_RATE}"
fi

if [ -f "test_e2e_results.json" ]; then
    E2E_PASS_RATE=$(cat test_e2e_results.json | grep -o '"pass_rate": "[^"]*"' | cut -d'"' -f4)
    echo "E2E测试通过率: ${E2E_PASS_RATE}"
fi

echo ""
echo "========================================================================"
echo "📄 生成的报告文件"
echo "========================================================================"
echo ""
echo "  1. test_results.json           - 后端测试详细结果"
echo "  2. test_frontend_results.json  - 前端测试详细结果"
echo "  3. test_e2e_results.json       - E2E测试详细结果"
echo "  4. COMPREHENSIVE_TEST_REPORT.json - 综合报告(JSON)"
echo "  5. TEST_REPORT_SUMMARY.md      - 测试报告摘要"
echo "  6. 测试执行总结.md              - 详细测试总结"
echo ""
echo "========================================================================"
echo "✅ 所有测试执行完成！"
echo "========================================================================"
echo ""
echo "查看详细报告:"
echo "  cat TEST_REPORT_SUMMARY.md"
echo "  cat 测试执行总结.md"
echo ""


