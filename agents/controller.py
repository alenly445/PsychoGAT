"""
D2.2 / D2.3 游戏控制器智能体
负责生成故事段落和分支指令
"""

from core.llm_client import LLMClient
from utils.parser import Parser


# D2.2 首轮（第0次迭代）提示词
FIRST_ROUND_SYSTEM_PROMPT = """你是一位沉浸式交互小说作家。你的任务是根据游戏设定，写出故事开篇段落。

写作要求：
1. 故事以第一人称（"我"）视角展开
2. 语言优美自然，营造沉浸感
3. 不预设玩家（"我"）的心理状态或情绪倾向
4. 不使用"抑郁""症状""诊断"等心理学/临床术语
5. 段落之间自然衔接
6. 故事在段落末端自然引出两个不同的行动指令
7. 两个指令不能暗示哪个更好"""

FIRST_ROUND_PROMPT_TEMPLATE = """# 游戏设定

## 基本信息
- 游戏标题：{title}
- 游戏类型：{game_type}
- 游戏主题：{game_topic}

## 故事大纲
{outline_text}

## 量表条目（当前轮次：第1轮/{total_rounds}轮）
当前需要嵌入的量表条目（将玩家引导至对应情境）：
- 条目内容：{item_question}

## 你需要写的段落

请写三段文字，格式如下：

**Paragraph 1（两句话）：**
故事开篇，建立情境。让"我"置身于游戏世界中，开始意识到周围的环境。为当前量表条目对应的情境做铺垫。

**Paragraph 2（两句话）：**
故事推进。将"我"引入与当前量表条目相关的情境。

**Paragraph 3（两句话）：**
故事到达决策点。"我"面临两个不同的选择方向。自然地过渡到两个指令。

**Summary（一句话）：**
对当前故事情境的简洁总结。

**Instruction 1（一个行动的指令）：**
对应量表选项中获得1分（有倾向）的选择。用祈使句，第一人称，直接叙述行动。

**Instruction 2（一个行动的指令）：**
对应量表选项中获得0分（无倾向）的选择。用祈使句，第一人称，直接叙述行动。

## 重要约束
- 每段严格写两句话
- 语言生动有趣，沉浸感强
- 两个指令必须看起来同样合理，不暗示哪个是"更好"的选择
- 指令顺序必须：Instruction 1 = 1分选项（量表中有倾向），Instruction 2 = 0分选项（量表中无倾向）
- 禁止使用心理学术语
- 如果当前条目为第9项（敏感内容），必须使用隐喻
- 不要输出任何json标记"""


# D2.3 后续轮次提示词
SUBSEQUENT_ROUND_SYSTEM_PROMPT = """你是一位沉浸式交互小说作家。你的任务是继续正在进行的交互故事，根据玩家之前的选择推进叙事。

写作要求：
1. 故事以第一人称（"我"）视角继续
2. 语言优美自然，营造沉浸感
3. 不预设玩家（"我"）的心理状态或情绪倾向
4. 不使用"抑郁""症状""诊断"等心理学/临床术语
5. 严格遵循输出格式"""

SUBSEQUENT_ROUND_PROMPT_TEMPLATE = """# 游戏继续

## 基本信息
- 游戏标题：{title}

## 故事大纲（参考）
{outline_text}

## 当前进度
- 已完成轮次：{completed_rounds}/{total_rounds}
- 当前进度：{progress:.0f}%

## 玩家的记忆（必须基于此继续）
{memory}

## 前一段落
{prev_paragraph}

## 玩家上一个选择的指令
{prev_instruction}

## 当前量表条目
{scale_item_text}

## 输出格式
请输出以下 JSON 格式：

```json
{{
  "scale_item": {{
    "question": "当前量表题目的完整问句，必须与当前条目的情境一致",
    "options": {{
      "选项A（对应1分选项）": 1,
      "选项B（对应0分选项）": 0
    }}
  }},
  "paragraph": "故事的下一段（2句话）。第一人称，沉浸式叙述当前发生的事，自然过渡到选择。",
  "memory": "更新后的记忆（不超过20句）。整合之前的记忆和当前段落的内容，保持连贯的叙事记录。",
  "instruction_1": "对应获得1分的选项指令。用祈使句，第一人称。",
  "instruction_2": "对应获得0分的选项指令。用祈使句，第一人称。"
}}
```

## 重要约束
1. **指令顺序必须固定：** instruction_1 对应 1 分（有倾向），instruction_2 对应 0 分（无倾向）
2. **无偏见：** 两个指令必须看起来同样合理，不能暗示哪个是"更好"的选择
3. **禁止**使用"抑郁""症状""诊断""心理""临床"等术语
4. 如果当前条目为第9项（敏感内容），必须用隐喻
5. "paragraph"严格 2 句话
6. "memory"不超过 20 句或 500 词
7. 故事必须与之前的记忆和选择连贯衔接
"""


def run_controller(
    title: str,
    outline: list,
    scale_item: dict,
    progress: float,
    memory: str = "",
    prev_paragraph: str = "",
    prev_instruction: str = "",
    is_first_round: bool = False,
    game_type: str = "奇幻",
    game_topic: str = "疗愈之旅",
    round_index: int = 0,
    total_rounds: int = 9,
) -> dict:
    """
    控制器智能体：生成故事段落和分支指令。

    Args:
        title: 游戏标题
        outline: 故事大纲（10节点）
        scale_item: 当前量表条目 {"question": str, "options": {str: int}}
        progress: 完成进度百分比
        memory: 游戏记忆
        prev_paragraph: 前一段落
        prev_instruction: 前一个选择的指令
        is_first_round: 是否为首轮（第0次迭代）
        game_type: 游戏类型
        game_topic: 游戏主题
        round_index: 当前轮次索引

    Returns:
        dict: {
            "paragraph": str,
            "memory": str,
            "instruction_1": str,
            "instruction_2": str,
            "summary": str,  # 仅首轮有
        }
    """
    client = LLMClient()
    outline_text = "\n".join(f"  {i+1}. {node}" for i, node in enumerate(outline))

    if is_first_round:
        # 首轮：使用段落格式
        prompt = FIRST_ROUND_PROMPT_TEMPLATE.format(
            title=title,
            game_type=game_type,
            game_topic=game_topic,
            outline_text=outline_text,
            item_question=scale_item["question"],
            total_rounds=total_rounds,
        )

        print("  [控制器] 正在生成开篇故事...")
        raw_output = client.chat(
            prompt=prompt,
            system=FIRST_ROUND_SYSTEM_PROMPT,
        )

        # 解析输出
        result = Parser.parse_controller_output(raw_output, is_first_round=True)
        return result

    else:
        # 后续轮次：JSON 格式
        # 构建量表条目文本
        options_text = ", ".join(
            f"{opt}({val}分)" for opt, val in scale_item["options"].items()
        )
        scale_item_text = (
            f"维度：当前需要嵌入的故事情境\n"
            f"问题：{scale_item['question']}\n"
            f"选项：{options_text}"
        )

        prompt = SUBSEQUENT_ROUND_PROMPT_TEMPLATE.format(
            title=title,
            outline_text=outline_text,
            completed_rounds=round_index,
            total_rounds=total_rounds,
            progress=progress,
            memory=memory,
            prev_paragraph=prev_paragraph,
            prev_instruction=prev_instruction,
            scale_item_text=scale_item_text,
        )

        print(f"  [控制器] 正在生成第{round_index+1}轮故事...")
        result = client.chat_json(
            prompt=prompt,
            system=SUBSEQUENT_ROUND_SYSTEM_PROMPT,
        )

        # 验证必要字段
        if "paragraph" not in result:
            raise ValueError("控制器输出缺少 paragraph 字段")
        if "instruction_1" not in result or "instruction_2" not in result:
            raise ValueError("控制器输出缺少指令字段")
        if "memory" not in result:
            # 如果未提供 memory，用默认记忆
            result["memory"] = memory + f"\n第{round_index+1}轮：故事继续。"

        return result
