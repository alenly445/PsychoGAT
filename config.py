"""
PsychoGAT 配置文件
支持从环境变量和 .env 文件读取配置
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """全局配置管理"""

    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")

    # 模型设置
    MODEL = os.getenv("MODEL", "deepseek-chat")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

    # 日志
    VERBOSE = os.getenv("VERBOSE", "true").lower() == "true"

    # PHQ-9 的 9 个核心维度（内部使用，不直接暴露给游戏）
    PHQ9_DIMENSIONS = [
        "兴趣减退",       # 条目1：对做事缺乏兴趣或乐趣
        "情绪低落",       # 条目2：感到沮丧、抑郁或绝望
        "睡眠障碍",       # 条目3：入睡困难、睡不安稳或睡眠过多
        "疲劳乏力",       # 条目4：感到疲倦或精力不足
        "食欲变化",       # 条目5：食欲不振或暴饮暴食
        "自我否定",       # 条目6：对自己感到失望或觉得自己让家人失望
        "注意力困难",     # 条目7：难以集中注意力
        "精神运动异常",   # 条目8：动作或说话迟缓，或坐立不安
        "自伤意念",       # 条目9：有不如死了好的念头或自伤行为（须用隐喻）
    ]

    @classmethod
    def validate(cls) -> bool:
        """验证必要配置是否存在"""
        if not cls.DEEPSEEK_API_KEY:
            print("❌ 错误：未设置 DEEPSEEK_API_KEY")
            print("   请创建 .env 文件并填入你的 API Key，参考 .env.example")
            print("   或在环境变量中设置 DEEPSEEK_API_KEY")
            return False
        return True
