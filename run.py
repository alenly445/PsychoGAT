"""
PsychoGAT 抑郁检测交互式小说游戏
主入口

用法：
    python run.py
    python run.py --game-type 奇幻 --game-topic 疗愈之旅 --simulator depressed
    python run.py --simulator healthy
    python run.py --model deepseek-reasoner
    python run.py --verbose
    python run.py --output example_output/full_game_demo.md
"""

import sys
import os
import argparse
import json
from datetime import datetime

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from core.game_loop import run_full_game


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PsychoGAT 抑郁检测交互式小说游戏",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python run.py                             # 默认运行
  python run.py --simulator healthy          # 健康对照模式
  python run.py --model deepseek-reasoner    # 使用推理模型
  python run.py --output result.md           # 保存到文件
  python run.py --verbose                    # 详细输出
        """,
    )

    parser.add_argument(
        "--game-type",
        type=str,
        default="奇幻",
        help="游戏类型（奇幻、科幻、校园、都市等，默认：奇幻）",
    )
    parser.add_argument(
        "--game-topic",
        type=str,
        default="疗愈之旅",
        help="游戏主题（默认：疗愈之旅）",
    )
    parser.add_argument(
        "--simulator",
        type=str,
        choices=["depressed", "healthy"],
        default="depressed",
        help="模拟器类型（depressed=抑郁倾向模拟，healthy=健康对照，默认：depressed）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=Config.MODEL,
        help=f"模型名称（默认：{Config.MODEL}）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=Config.VERBOSE,
        help="详细输出模式",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="保存输出到文件（如 example_output/game_result.md）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="安静模式（仅输出关键信息）",
    )

    return parser.parse_args()


def save_output(result: dict, output_path: str):
    """保存游戏记录到文件"""
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    except OSError:
        pass

    game_data = result["game_data"]
    rounds = result["rounds"]
    results = result["results"]

    lines = []
    lines.append("# PsychoGAT 抑郁检测游戏记录\n")
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**模型：** {result['config']['model']}\n")
    lines.append(f"**模拟器：** {'抑郁倾向' if result['config']['simulator_depressed'] else '健康对照'}\n")
    lines.append("---\n")

    # 游戏信息
    lines.append("## 🎮 游戏信息\n")
    lines.append(f"- **标题：** {game_data['title']}\n")
    lines.append(f"- **类型：** {result['config']['game_type']}\n")
    lines.append(f"- **主题：** {result['config']['game_topic']}\n")
    lines.append(f"- **设计理念：** {game_data.get('design_rationale', '无')}\n")
    lines.append("\n### 故事大纲\n")
    for i, node in enumerate(game_data["outline"]):
        lines.append(f"{i+1}. {node}\n")

    # 量表
    lines.append("\n### 量表设计\n")
    for i, item in enumerate(game_data["redesigned_scale"]):
        options_str = " / ".join(f"{opt}({val}分)" for opt, val in item["options"].items())
        lines.append(f"{i+1}. {item['question']}\n")
        lines.append(f"   选项：{options_str}\n")

    # 各轮记录
    lines.append("\n---\n## 📝 游戏过程\n")
    for r in rounds:
        lines.append(f"\n### 第 {r['round']} 轮（{r['dimension']}）\n")
        lines.append(f"**控制器生成段落：**\n{r['controller_paragraph']}\n\n")
        if r["critic_paragraph"] != r["controller_paragraph"]:
            lines.append(f"**评论家优化后段落：**\n{r['critic_paragraph']}\n\n")
        lines.append(f"**指令1：** {r['instruction_1']}\n")
        lines.append(f"**指令2：** {r['instruction_2']}\n")
        lines.append(f"**玩家选择：** 指令{r['selected_instruction']} → **得分：{r['score']}**\n")
        if r.get("simulator_reason"):
            lines.append(f"**选择理由：** {r['simulator_reason']}\n")

    # 结果
    lines.append("\n---\n## 📊 评估结果\n")
    lines.append(f"| 轮次 | 维度 | 结果 | 得分 |\n")
    lines.append(f"|------|------|------|------|\n")
    for detail in results["details"]:
        mark = "⚠️" if detail["score"] == 1 else "✅"
        lines.append(f"| {detail['round']} | {detail['dimension']} | {mark} {detail['result']} | {detail['score']} |\n")

    lines.append(f"\n**总分：** {results['total_score']}/9\n")
    lines.append(f"**评估：** {results['severity']['level']}\n")
    lines.append(f"**建议：** {results['severity']['recommendation']}\n")

    content = "".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n  ✅ 完整游戏记录已保存至：{output_path}")


def main():
    """主函数"""
    # 验证配置
    if not Config.validate():
        sys.exit(1)

    args = parse_args()

    # 打印启动信息
    if not args.quiet:
        print("=" * 55)
        print("  PsychoGAT 抑郁检测交互式小说游戏")
        print(f"  模型: {args.model}")
        print(f"  模拟器: {'抑郁倾向' if args.simulator == 'depressed' else '健康对照'}")
        print("=" * 55)
        print("")

    # 运行游戏
    try:
        result = run_full_game(
            game_type=args.game_type,
            game_topic=args.game_topic,
            simulator_depressed=(args.simulator == "depressed"),
            model=args.model,
            verbose=args.verbose and not args.quiet,
        )

        # 保存输出
        if args.output:
            save_output(result, args.output)

        # 也保存一份 JSON 格式的完整记录
        json_output = args.output.replace(".md", ".json") if args.output else ""
        if json_output:
            # 移除不可序列化内容
            serializable = {
                "config": result["config"],
                "game_data": result["game_data"],
                "rounds": result["rounds"],
                "results": result["results"],
                "timestamp": datetime.now().isoformat(),
            }
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)

            print(f"  ✅ JSON 数据已保存至：{json_output}")

        return 0

    except KeyboardInterrupt:
        print("\n\n  ⚠️  游戏被用户中断")
        return 1
    except Exception as e:
        print(f"\n  ❌ 游戏运行出错：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
