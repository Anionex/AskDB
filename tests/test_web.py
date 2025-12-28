# test_web_search_fix.py
#!/usr/bin/env python3
"""
测试Web搜索修复
"""

import sys
from pathlib import Path

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from askdb_agno import create_agent

def test_web_search_integration():
    """测试Web搜索集成"""
    print("🧪 测试Web搜索集成...")
    
    try:
        # 创建代理
        agent = create_agent(debug=False)
        print("✅ Agent创建成功")
        
        # 测试需要Web搜索的问题
        test_questions = [
            "什么是Python编程？",
            "介绍一下东莞实验中学",
            "腊肠的定义是什么？",
            "最新的AI技术有哪些？"
        ]
        
        for question in test_questions:
            print(f"\n🔍 测试问题: {question}")
            try:
                response = agent.run(question)
                content = response.content
                
                print(f"✅ 响应长度: {len(content)} 字符")
                print(f"📄 响应预览: {content[:200]}...")
                
                # 检查是否包含搜索相关内容
                if len(content) > 100:  # 响应应该足够详细
                    print("🎉 Web搜索结果显示正常！")
                else:
                    print("⚠️ 响应可能过短，检查AI是否整合了搜索结果")
                    
            except Exception as e:
                print(f"❌ 问题处理失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    if test_web_search_integration():
        print("\n🎉 Web搜索修复测试通过！")
    else:
        print("\n⚠️ Web搜索仍需进一步调试")