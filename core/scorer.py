"""
计分与评估模块
根据 PHQ-9 评分标准评估抑郁倾向
"""

from config import Config


# PHQ-9 评分等级
SEVERITY_LEVELS = [
    (0, "正常范围", "无抑郁倾向，建议保持健康生活方式"),
    (3, "轻度抑郁倾向", "可能有轻微情绪波动，建议关注自我调节"),
    (5, "中重度抑郁倾向", "有较明显的抑郁倾向，建议关注心理健康"),
    (7, "重度抑郁倾向", "有显著的抑郁倾向，强烈建议寻求专业帮助"),
]


def calculate_score(scores: list) -> int:
    """
    计算总分。

    Args:
        scores: 每轮得分的列表（0 或 1）

    Returns:
        int: 总分（0-9）
    """
    return sum(scores)


def get_severity(total_score: int) -> dict:
    """
    根据总分确定抑郁倾向等级。

    Args:
        total_score: 总分

    Returns:
        dict: {
            "level": str,       # 等级名称
            "recommendation": str,  # 建议
            "score": int,       # 总分
        }
    """
    level = SEVERITY_LEVELS[0]
    for threshold, name, advice in reversed(SEVERITY_LEVELS):
        if total_score >= threshold:
            level = (threshold, name, advice)
            break

    return {
        "score": total_score,
        "level": level[1],
        "recommendation": level[2],
    }


def format_results(scores: list, dimensions: list = None) -> dict:
    """
    格式化完整评估结果。

    Args:
        scores: 每轮得分列表
        dimensions: 各维度名称（可选）

    Returns:
        dict: 包含详细评估结果
    """
    if dimensions is None:
        dimensions = Config.PHQ9_DIMENSIONS

    total = calculate_score(scores)
    severity = get_severity(total)

    # 各维度详情
    details = []
    for i, (dim, score) in enumerate(zip(dimensions, scores)):
        details.append({
            "round": i + 1,
            "dimension": dim,
            "score": score,
            "result": "有倾向" if score == 1 else "无倾向",
        })

    return {
        "total_score": total,
        "severity": severity,
        "details": details,
    }
