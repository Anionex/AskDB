from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
import os

# 创建多功能智能助手
assistant = Agent(
    name="多功能助手",
    model=Gemini(api_key="AIzaSyAZ5-8XsjQamY8k30EswSyY79EJfzoXoBI"),
    tools=[
        DuckDuckGoTools(),  # 网页搜索
        YFinanceTools(),    # 股票查询
    ],
    instructions=[
        "你是一个多功能智能助手",
        "可以搜索网页信息和查询股票数据",
        "提供准确、及时的信息"
    ],
    markdown=True,
)

# 测试网页搜索
assistant.print_response("搜索最新的人工智能发展趋势")

print("\n" + "="*50 + "\n")

# 测试股票查询
assistant.print_response("查询苹果公司(AAPL)的股票价格")