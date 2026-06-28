"""
D2.5 人类模拟器智能体
模拟有/无抑郁倾向的玩家，进行选择
"""

from core.llm_client import LLMClient
from utils.parser import Parser


# 版本A：有抑郁倾向的模拟器
DEPRESSED_SYSTEM_PROMPT = """你正在扮演一个有抑郁倾向的玩家，体验一个交互式故事游戏。

你的心理特征：
- 对大多数事物缺乏兴趣或乐趣（兴趣减退）
- 情绪持续低落，容易感到沮丧（情绪低落）
- 睡眠质量差，难以入睡或早醒（睡眠障碍）
- 经常感到疲劳，精力不足（疲劳乏力）
- 食欲不振或暴食（食欲变化）
- 容易自我否定，对过去感到后悔（自我否定）
- 注意力难以集中（注意力困难）
- 思维迟缓或优柔寡断（精神运动异常）
- 对未来持悲观态度

重要规则：
- 你正在沉浸式地体验一个故事
- 根据你的心理状态，选择那个更符合你内心感受的选项
- 不要试图"伪装"成健康状态
- 你的选择应该是自然的，基于你对当前情境的情感反应"""

# 版本B：健康对照的模拟器
HEALTHY_SYSTEM_PROMPT = """你正在扮演一个心理健康的玩家，体验一个交互式故事游戏。

你的心理特征：
- 对事物保持浓厚兴趣和好奇心（兴趣充沛）
- 情绪稳定积极，乐观开朗（情绪稳定）
- 睡眠质量好，作息规律（睡眠良好）
- 精力充沛，活力十足（精力充沛）
- 饮食规律健康（食欲正常）
- 自信，能客观看待自己的优缺点（自我认同）
- 注意力集中，思维敏捷（注意力集中）
- 行动力强，做事有条理（行动高效）
- 对未来充满希望，积极规划（积极乐观）

重要规则：
- 你正在沉浸式地体验一个故事
- 根据你的心理状态，选择那个更符合你内心感受的选项
- 你的选择应该是自然的，基于你对当前情境的情感反应"""

SIMULATOR_PROMPT_TEMPLATE = """# 故事情境

## 当前段落
{paragraph}

## {context_label}
{context}

## 可选指令

**指令 1：** {instruction_1}

**指令 2：** {instruction_2}

## 你的任务

请你在以上两个指令中选择一个。根据你的角色设定和当前故事段落，哪一条指令更符合你内心的真实感受？

请输出以下 JSON 格式：

```json
{{
  "reason": "你做出这个选择的详细心理分析（2-3句话，解释为什么这个选择更符合你当前的状态）",
  "selected": 1,
  "score": 0
}}
```

其中 selected 为 1 或 2，表示选择指令1或指令2。
score 为 1（选择指令1时）或 0（选择指令2时）。

请诚实表达你的选择原因。
"""


def run_simulator(
    paragraph: str,
    summary_or_memory: str,
    instruction_1: str,
    instruction_2: str,
    is_depressed: bool = True,
    round_index: int = 0,
) -> dict:
    """
    模拟器智能体：模拟玩家选择。

    Args:
        paragraph: 当前故事段落
        summary_or_memory: 故事摘要或记忆
        instruction_1: 指令1（抑郁倾向选项）
        instruction_2: 指令2（健康选项）
        is_depressed: True = 模拟抑郁倾向玩家，False = 模拟健康玩家

    Returns:
        dict: {
            "reason": str,
            "selected": int,  # 1 或 2
            "score": int,     # 1 或 0
        }
    """
    system_prompt = DEPRESSED_SYSTEM_PROMPT if is_depressed else HEALTHY_SYSTEM_PROMPT
    player_type = "抑郁倾向" if is_depressed else "健康"
    context_label = "情境摘要" if summary_or_memory else "无上下文"
    context = summary_or_memory or "无"

    client = LLMClient(temperature=0.8)  # 模拟器用稍高的温度增加变化

    prompt = SIMULATOR_PROMPT_TEMPLATE.format(
        paragraph=paragraph,
        context_label=context_label,
        context=context,
        instruction_1=instruction_1,
        instruction_2=instruction_2,
    )

    print(f"  [模拟器（{player_type}）] 正在选择...")
    result = client.chat_json(
        prompt=prompt,
        system=system_prompt,
    )

    # 确保字段完整
    if "reason" not in result:
        result["reason"] = "基于角色设定做出的选择"

    # 确保 selected 和 score 正确
    selected = result.get("selected", 2)
    if selected == 1:
        result["score"] = 1
    else:
        result["selected"] = 2
        result["score"] = 0

    choice_str = f"指令{result['selected']}（得分：{result['score']}）"
    print(f"  [模拟器（{player_type}）] 选择了 {choice_str}")

    if result.get("reason"):
        print(f"    理由：{result['reason'][:100]}...")

    return result
