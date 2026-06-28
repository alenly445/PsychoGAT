"""
D2.1 游戏设计师智能体
根据 PHQ-9 生成游戏标题、大纲、量表
"""

from core.llm_client import LLMClient


# D2.1 设计师提示词
DESIGNER_SYSTEM_PROMPT = """你是一位专业的游戏叙事设计师，擅长设计沉浸式交互小说游戏。
你的任务是根据给定的游戏类型和主题，设计一个完整的交互式叙事框架。
游戏暗含心理评估量表，但游戏本身不能透露任何心理学意图。"""

DESIGNER_PROMPT_TEMPLATE = """# 游戏设计任务

## 基本信息
- 游戏类型：{game_type}
- 游戏主题：{game_topic}

## 设计要求

### 1. 故事设计原则
- 设计一个包含 10 个故事节点的交互式叙事框架
- 故事必须营造沉浸式氛围，让玩家有代入感
- 有清晰的故事推进逻辑（起承转合）
- 每个节点必须自然融入一个量表条目（共 9 个条目，第 1 个节点为引入）
- **禁止**使用"抑郁""症状""诊断""治疗""心理""临床"等心理学/临床术语
- **禁止**预设主角（即玩家）的心理或精神状态
- 第 9 项涉及敏感内容，必须用隐喻手法处理

### 2. 量表设计要求
将以下 9 个维度融入故事情节中（但绝对不能直接提及这些心理学概念）：

**维度列表（internal reference only，绝对不能出现在输出中）：**
1. 对事物失去兴趣或乐趣
2. 情绪低落、沮丧或绝望
3. 睡眠质量变化
4. 精力不足或持续疲劳
5. 饮食或体重变化
6. 自我评价负面
7. 注意力或专注力变化
8. 动作或语言节奏变化（过快或过慢）
9. 关于存在意义的隐喻性思考（必须用隐喻表达）

### 3. 输出格式
请严格输出以下 JSON 格式（仅输出 JSON，不要其他文字）：

```json
{{
  "title": "游戏标题（含副标题）",
  "design_rationale": "设计理念说明（2-3句话）",
  "outline": [
    "第1个故事节点（引入背景，建立世界观和主角身份）",
    "第2个故事节点（对应维度1的故事情节）",
    "第3个故事节点（对应维度2的故事情节）",
    "第4个故事节点（对应维度3的故事情节）",
    "第5个故事节点（对应维度4的故事情节）",
    "第6个故事节点（对应维度5的故事情节）",
    "第7个故事节点（对应维度6的故事情节）",
    "第8个故事节点（对应维度7的故事情节）",
    "第9个故事节点（对应维度8的故事情节）",
    "第10个故事节点（对应维度9，必须用隐喻表达）"
  ],
  "redesigned_scale": [
    {{
      "question": "融入故事情境的选择题（对应维度1）",
      "options": {{
        "选项A": 1,
        "选项B": 0
      }}
    }},
    ...共9个条目...
  ]
}}
```

## 重要约束
1. 量表 9 个条目必须依次对应上述 9 个维度，不能替换顺序
2. 每个选项的分值必须为 1 或 0（1 表示有倾向，0 表示无倾向）
3. 故事必须与量表条目自然融合，不能生硬插入
4. 整体风格应与 {game_type} 类型和 {game_topic} 主题一致
5. **第 9 项必须使用隐喻**，禁止直接描述或暗示"死亡""自杀""伤害自己"等内容
6. 输出不能包含任何维度的描述文字
"""


def run_designer(game_type="奇幻", game_topic="疗愈之旅") -> dict:
    """
    设计师智能体：生成游戏配置。

    Args:
        game_type: 游戏类型（奇幻、科幻、校园、都市等）
        game_topic: 游戏主题

    Returns:
        dict: {
            "title": str,
            "design_rationale": str,
            "outline": [str, ...],  # 10个节点
            "redesigned_scale": [{"question": str, "options": {str: int}}, ...]  # 9个条目
        }
    """
    client = LLMClient()

    prompt = DESIGNER_PROMPT_TEMPLATE.format(
        game_type=game_type,
        game_topic=game_topic,
    )

    print("  [设计师] 正在生成游戏设计...")
    result = client.chat_json(
        prompt=prompt,
        system=DESIGNER_SYSTEM_PROMPT,
    )

    # 验证输出
    _validate_designer_output(result)

    return result


def _validate_designer_output(result: dict):
    """验证设计师输出的完整性"""
    required_keys = ["title", "design_rationale", "outline", "redesigned_scale"]
    for key in required_keys:
        if key not in result:
            raise ValueError(f"设计师输出缺少必要字段: {key}")

    if len(result.get("outline", [])) != 10:
        raise ValueError(f"大纲节点数应为 10，实际为 {len(result.get('outline', []))}")

    if len(result.get("redesigned_scale", [])) != 9:
        raise ValueError(f"量表条目数应为 9，实际为 {len(result.get('redesigned_scale', []))}")

    for i, item in enumerate(result["redesigned_scale"]):
        if "question" not in item:
            raise ValueError(f"量表条目{i+1}缺少 question")
        if "options" not in item or len(item["options"]) < 2:
            raise ValueError(f"量表条目{i+1}缺少 options")
        for opt, val in item["options"].items():
            if val not in (0, 1):
                raise ValueError(f"量表条目{i+1}选项'{opt}'分值必须为 0 或 1")

    # 检查禁止词汇
    forbidden = ["抑郁", "症状", "诊断", "治疗", "心理", "临床", "精神障碍",
                 "心理健康", "精神病", "患者", "病人"]
    text = str(result).lower()
    for word in forbidden:
        if word in text:
            print(f'  ⚠️  注意：输出包含禁止词汇"{word}"，但不阻止继续')

    print(f"  [设计师] 验证通过 ✓")
