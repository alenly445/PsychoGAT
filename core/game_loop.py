"""
主游戏循环逻辑
协调 4 个智能体完成 9 轮交互
"""

from config import Config
from utils.logger import Logger
from core.scorer import format_results
from agents.designer import run_designer
from agents.controller import run_controller
from agents.critic import run_critic
from agents.simulator import run_simulator


def run_full_game(
    game_type="奇幻",
    game_topic="疗愈之旅",
    simulator_depressed=True,
    model="deepseek-chat",
    verbose=True,
) -> dict:
    """
    运行完整 PsychoGAT 游戏。

    Args:
        game_type: 游戏类型
        game_topic: 游戏主题
        simulator_depressed: 模拟器是否抑郁倾向
        model: 模型名称
        verbose: 是否详细输出

    Returns:
        dict: 包含完整游戏记录和评估结果
    """
    logger = Logger(verbose=verbose)
    dimensions = Config.PHQ9_DIMENSIONS

    logger.section("PsychoGAT 抑郁检测游戏")
    logger.info(f"模型: {model} | 模拟器类型: {'抑郁倾向' if simulator_depressed else '健康对照'}", "bold")

    # ==================== Phase 1: 设计师 ====================
    logger.section("Phase 1: 游戏设计")
    logger.agent("设计师", "正在生成游戏配置...")
    game_data = run_designer(game_type=game_type, game_topic=game_topic)

    title = game_data["title"]
    outline = game_data["outline"]
    redesigned_scale = game_data["redesigned_scale"]

    logger.info("")
    logger.agent("设计师", f"游戏标题：{title}")
    logger.agent("设计师", f"游戏类型：{game_type} | 主题：{game_topic}")
    logger.detail(f"设计理念：{game_data.get('design_rationale', '无')}")
    logger.detail("故事大纲：")
    for i, node in enumerate(outline):
        logger.detail(f"  {i+1}. {node}")
    logger.info(f"  ✅ 设计师完成")

    # ==================== Phase 2: 游戏循环 ====================
    logger.section("Phase 2: 游戏进行中")

    scores = []
    memory = ""
    prev_paragraph = ""
    prev_instruction = ""
    round_logs = []
    total_rounds = len(redesigned_scale)

    for i in range(total_rounds):
        is_first = (i == 0)
        progress = (i + 1) / total_rounds * 100
        scale_item = redesigned_scale[i]
        dimension_name = dimensions[i] if i < len(dimensions) else f"维度{i+1}"

        logger.divider()
        logger.info(f"  第 {i+1}/{total_rounds} 轮 —— {dimension_name}", "bold")
        logger.progress(i + 1, total_rounds, dimension_name)

        # Step a: 控制器生成
        controller_output = run_controller(
            title=title,
            outline=outline,
            scale_item=scale_item,
            progress=progress,
            memory=memory,
            prev_paragraph=prev_paragraph,
            prev_instruction=prev_instruction,
            is_first_round=is_first,
            game_type=game_type,
            game_topic=game_topic,
            round_index=i,
            total_rounds=total_rounds,
        )

        paragraph = controller_output.get("paragraph", "")
        memory_candidate = controller_output.get("memory", "")
        instruction_1 = controller_output.get("instruction_1", "")
        instruction_2 = controller_output.get("instruction_2", "")
        summary = controller_output.get("summary", "")

        logger.detail(f"[控制器] 段落生成完成")

        # Step b: 评论家优化
        critic_output = run_critic(
            paragraph=paragraph,
            memory=memory_candidate if not is_first else "",
            instruction_1=instruction_1,
            instruction_2=instruction_2,
            round_index=i,
            total_rounds=total_rounds,
            is_first_round=is_first,
        )

        refined_paragraph = critic_output.get("paragraph", paragraph)
        refined_memory = critic_output.get("memory", memory_candidate)
        refined_instruction_1 = critic_output.get("instruction_1", instruction_1)
        refined_instruction_2 = critic_output.get("instruction_2", instruction_2)
        reviews = critic_output.get("reviews", {})

        # 输出评论家审查意见
        total_issues = sum(
            len(reviews.get(dim, {}).get("issues", []))
            for dim in ["coherence", "bias", "omission"]
        )
        if total_issues > 0:
            logger.detail(f"[评论家] 发现 {total_issues} 个问题：")
            for dim_name in ["coherence", "bias", "omission"]:
                issues = reviews.get(dim_name, {}).get("issues", [])
                for issue in issues:
                    logger.detail(f"    • [{dim_name}] {issue}")
        logger.detail(f"[评论家] 优化完成 ✓")

        # Step c: 模拟器选择
        context = refined_memory if (not is_first and refined_memory) else summary
        choice = run_simulator(
            paragraph=refined_paragraph,
            summary_or_memory=context,
            instruction_1=refined_instruction_1,
            instruction_2=refined_instruction_2,
            is_depressed=simulator_depressed,
            round_index=i,
        )

        score = choice["score"]
        selected = choice["selected"]
        scores.append(score)

        # 记录本轮详情
        round_info = {
            "round": i + 1,
            "dimension": dimension_name,
            "controller_paragraph": paragraph,
            "critic_paragraph": refined_paragraph,
            "instruction_1": refined_instruction_1,
            "instruction_2": refined_instruction_2,
            "simulator_reason": choice.get("reason", ""),
            "selected_instruction": selected,
            "score": score,
        }
        round_logs.append(round_info)

        # 更新状态
        prev_paragraph = refined_paragraph
        prev_instruction = refined_instruction_1 if selected == 1 else refined_instruction_2
        memory = refined_memory if (not is_first and refined_memory) else f"第{i+1}轮：玩家选择了{'抑郁倾向' if score == 1 else '健康'}方向。"
        if summary and is_first:
            memory = summary + "\n" + memory

        player_type = "抑郁倾向" if simulator_depressed else "健康"
        choice_label = "抑郁倾向" if score == 1 else "健康"
        logger.info(f"  ▶ 玩家选择了指令{selected}（{choice_label}）→ 得分：{score}")
        logger.info(f"    当前总分：{sum(scores)}/{total_rounds}")

    # ==================== Phase 3: 评分与评估 ====================
    logger.section("Phase 3: 评估结果")

    results = format_results(scores, dimensions)

    # 输出各维度结果
    total = results["total_score"]
    severity = results["severity"]

    logger.info("各维度得分：")
    for detail in results["details"]:
        mark = "⚠️" if detail["score"] == 1 else "✅"
        logger.info(f"  {mark}  第{detail['round']}轮（{detail['dimension']}）: {detail['result']}（{detail['score']}分）")

    logger.divider()
    logger.info(f"  总分：{total}/9", "bold")
    logger.info(f"  评估：{severity['level']}", "bold")
    logger.info(f"  建议：{severity['recommendation']}", "bold")

    # ==================== 返回完整结果 ====================
    return {
        "config": {
            "game_type": game_type,
            "game_topic": game_topic,
            "simulator_depressed": simulator_depressed,
            "model": model,
        },
        "game_data": {
            "title": title,
            "design_rationale": game_data.get("design_rationale", ""),
            "outline": outline,
            "redesigned_scale": redesigned_scale,
        },
        "rounds": round_logs,
        "results": results,
        "full_log": logger.get_log(),
    }
