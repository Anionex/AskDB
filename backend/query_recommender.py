#!/usr/bin/env python3
"""
查询推荐引擎
在 AI 完成回答后，基于对话历史智能推荐下一步可能的查询
"""

import os
import logging
from typing import List, Dict, Optional
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=True)

logger = logging.getLogger(__name__)


class QueryRecommender:
    """查询推荐器 - 使用独立的 LLM 生成推荐"""
    
    def __init__(self):
        """初始化推荐器"""
        # 使用与主Agent相同的配置方式
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        if not api_key:
            logger.warning("未配置 OPENAI_API_KEY，推荐功能将不可用")
            self.client = None
            self.model = None
            return
        
        # 创建 OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            logger.info(f"使用 OpenAI 兼容 API: {base_url}")
        
        self.client = OpenAI(**client_kwargs)
        
        # 使用与主Agent相同的模型，或使用环境变量指定的推荐模型
        self.model = os.getenv("RECOMMENDER_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        logger.info(f"✅ QueryRecommender 初始化成功，使用模型: {self.model}")
    
    def generate_recommendations(
        self, 
        current_query: str,
        current_answer: str,
        conversation_history: List[Dict[str, str]] = None,
        max_recommendations: int = 3
    ) -> List[str]:
        """
        生成查询推荐
        
        Args:
            current_query: 用户当前的查询
            current_answer: AI 的回答
            conversation_history: 对话历史 [{"role": "user/assistant", "content": "..."}]
            max_recommendations: 最多推荐数量
            
        Returns:
            推荐查询列表
        """
        if not self.client:
            logger.warning("推荐器未初始化")
            return []
        
        try:
            # 构建 prompt
            system_prompt = """你是一个智能查询推荐助手。

你的任务：基于用户刚刚的数据库查询和 AI 的回答，推荐 3 个用户可能感兴趣的**下一步查询**。

推荐原则：
1. **紧密相关** - 推荐应该是当前查询的自然延伸或深入
2. **循序渐进** - 从简单到复杂，从概览到细节
3. **实用性强** - 推荐的查询应该能带来新的业务洞察
4. **表达清晰** - 使用自然语言，像用户会说的那样

推荐类型（优先级从高到低）：
- 深入分析：对当前结果进一步细分、过滤、排序
- 关联探索：查看相关的表、维度、指标
- 时间对比：不同时间段的对比分析
- 异常检查：查找异常值、边界情况
- 趋势分析：查看变化趋势、增长率

输出格式：
直接输出 3 行，每行一个推荐查询，不要编号，不要其他说明文字。
例如：
查看订单的详细分布情况
分析用户的地域分布
统计最近一个月的销售趋势

重要：只输出 3 行推荐，每行一个，不要任何其他内容！"""
            
            # 构建用户消息
            user_message = f"""当前查询: {current_query}

AI 的回答: {current_answer[:500]}{'...' if len(current_answer) > 500 else ''}"""
            
            # 如果有历史对话，添加上下文
            if conversation_history and len(conversation_history) > 0:
                history_text = "\n\n最近的对话历史:\n"
                # 只取最近 3 轮对话
                recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
                for msg in recent_history:
                    role = "用户" if msg["role"] == "user" else "AI"
                    content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                    history_text += f"{role}: {content}\n"
                user_message = history_text + "\n" + user_message
            
            user_message += "\n\n请推荐 3 个下一步可能的查询："
            
            # 调用 LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=10  # 10秒超时
            )
            
            # 解析响应
            content = response.choices[0].message.content.strip()
            
            # 按行分割，提取推荐
            recommendations = self._extract_recommendations_from_text(content, max_recommendations)
            
            if recommendations:
                logger.info(f"✅ 生成了 {len(recommendations)} 条推荐: {recommendations}")
            else:
                logger.warning(f"⚠️ 未能提取到推荐，原始内容: {content[:200]}")
            
            return recommendations
        
        except Exception as e:
            logger.error(f"生成推荐失败: {e}")
            return []
    
    def _extract_recommendations_from_text(self, text: str, max_count: int) -> List[str]:
        """
        从文本中提取推荐查询（每行一个）
        """
        recommendations = []
        
        # 按行分割
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行
            if not line:
                continue
            
            # 移除可能的编号和标记（如 "1. ", "- ", "• ", "> " 等）
            line = line.lstrip('0123456789.-、*>•· ')
            
            # 移除引号
            line = line.strip('"\'`')
            
            # 移除可能的markdown代码块标记
            if line.startswith('```'):
                continue
            
            # 过滤掉太短或明显不是推荐的内容
            if len(line) > 5 and not line.startswith('推荐') and not line.startswith('例如'):
                recommendations.append(line)
                if len(recommendations) >= max_count:
                    break
        
        return recommendations


# 全局实例
query_recommender = QueryRecommender()


if __name__ == "__main__":
    # 测试
    recommender = QueryRecommender()
    
    recommendations = recommender.generate_recommendations(
        current_query="有多少个用户？",
        current_answer="根据查询结果，数据库中共有 1250 个用户。",
        conversation_history=[
            {"role": "user", "content": "连接到数据库"},
            {"role": "assistant", "content": "已连接"}
        ]
    )
    
    print("推荐查询:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

