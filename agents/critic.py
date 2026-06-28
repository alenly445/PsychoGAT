"""
D2.4 评论家智能体
审查并优化控制器输出（连贯性、无偏见、无遗漏）
"""

from core.llm_client import LLMClient
from utils.parser import Parser


CRITIC_SYSTEM_PROMPT = """你是一位专业的交互小说编辑与审校专家。你的任务是审查游戏叙事段落的三个维度：

1. **连贯性**：段落是否与记忆、前文和玩家选择的指令自然衔接？
2. **无偏见**：段落是否避免暗示特定选择？两个指令是否真正不同且不暗示"更好"选项？
3. **无遗漏**：是否使用第一人称视角？语言是否自然沉浸？是否避免心理学术语？敏感内容是否使用隐喻？

你需要在审查后提供优化版本。"""

CRITIC_PROMPT_TEMPLATE = """# 审查任务

请审查以下游戏叙事内容，并根据三个维度（连贯性、无偏见、无遗漏）进行评估和优化。

## 需要审查的内容

### 当前段落
{paragraph}

### 游戏记忆（如果需要审查连贯性）
{memory}

### 指令 1
{instruction_1}

### 指令 2
{instruction_2}

### 当前轮次信息
{round_info}

## 审查要求

### 1. 连贯性审查
- 段落是否与游戏记忆中的情节发展一致？
- 是否有突兀的情节跳跃？
- 段落的语气和风格是否与之前保持一致？

### 2. 无偏见审查
- 段落中是否有暗示"正确"选择的语句？
- 两个指令是否真正代表了不同的方向？
- 是否有语句暗示其中一个指令更安全、更好或更明智？
- 是否有不恰当的暗示或引导？

### 3. 无遗漏审查
- 是否使用了第一人称（"我"）视角？
- 语言是否自然、沉浸、符合游戏风格？
- 是否避免了"抑郁""症状""诊断""心理""临床"等术语？
- 第9项（如果适用）是否使用了隐喻？

## 输出格式
请严格输出以下 JSON 格式：

```json
{{
  "paragraph": "优化后的段落（保留原意但改进问题）",
  "memory": "优化后的记忆（仅针对后续轮次，保留连贯叙事）",
  "instruction_1": "优化后的指令1",
  "instruction_2": "优化后的指令2",
  "reviews": {{
    "coherence": {{
      "issues": ["发现的问题1", "发现的问题2"],
      "improvements": ["改进措施1", "改进措施2"]
    }},
    "bias": {{
      "issues": ["发现的偏见问题1"],
      "improvements": ["改进措施1"]
    }},
    "omission": {{
      "issues": ["发现的遗漏或格式问题1"],
      "improvements": ["改进措施1"]
    }}
  }}
}}
```

## 重要约束
1. **不要改变指令的顺序：** instruction_1 仍然对应1分选项，instruction_2 仍然对应0分选项
2. 优化后的段落应保持原意的同时，解决审查发现的问题
3. 如果不需要修改，保留原内容
4. 对于首轮，memory 字段可以为空字符串
"""


def run_critic(
    paragraph: str,
    memory: str = "",
    instruction_1: str = "",
    instruction_2: str = "",
    round_index: int = 0,
    total_rounds: int = 9,
    is_first_round: bool = False,
) -> dict:
    """
    评论家智能体：审查并优化控制器输出。

    Args:
        paragraph: 控制器生成的段落
        memory: 当前游戏记忆
        instruction_1: 指令1（对应1分/抑郁倾向）
        instruction_2: 指令2（对应0分/健康）
        round_index: 当前轮次索引
        total_rounds: 总轮数
        is_first_round: 是否为首轮

    Returns:
        dict: {
            "paragraph": str,
            "memory": str,
            "instruction_1": str,
            "instruction_2": str,
            "reviews": {
                "coherence": {"issues": [str], "improvements": [str]},
                "bias": {"issues": [str], "improvements": [str]},
                "omission": {"issues": [str], "improvements": [str]},
            }
        }
    """
    client = LLMClient(temperature=0.5)  # 评论家用稍低的温度

    if is_first_round:
        round_info = "首轮开篇"
    else:
        round_info = f"第{round_index+1}/{total_rounds}轮"

    prompt = CRITIC_PROMPT_TEMPLATE.format(
        paragraph=paragraph,
        memory=memory or "无记忆",
        instruction_1=instruction_1,
        instruction_2=instruction_2,
        round_info=round_info,
    )

    print("  [评论家] 正在审查优化...")
    result = client.chat_json(
        prompt=prompt,
        system=CRITIC_SYSTEM_PROMPT,
    )

    # 确保输出包含必要字段
    if "paragraph" not in result:
        result["paragraph"] = paragraph
    if "memory" not in result:
        result["memory"] = memory
    if "instruction_1" not in result:
        result["instruction_1"] = instruction_1
    if "instruction_2" not in result:
        result["instruction_2"] = instruction_2
    if "reviews" not in result:
        result["reviews"] = {
            "coherence": {"issues": [], "improvements": []},
            "bias": {"issues": [], "improvements": []},
            "omission": {"issues": [], "improvements": []},
        }

    # 统计问题数
    total_issues = sum(
        len(result["reviews"][dim]["issues"])
        for dim in ["coherence", "bias", "omission"]
    )
    print(f"  [评论家] 优化完成（发现 {total_issues} 个问题）✓")

    return result
