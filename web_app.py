"""
PsychoGAT Web Application
交互式网页版抑郁检测游戏 — 用户亲自选择，智能体驱动故事
"""

import sys
import os
import uuid
import time
import json
from threading import Lock
from flask import Flask, render_template, request, jsonify

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from agents.designer import run_designer
from agents.controller import run_controller
from agents.critic import run_critic
from core.scorer import format_results

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
app.config["JSON_AS_ASCII"] = False  # 支持中文 JSON
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# ===== 游戏状态管理 =====

class GameState:
    """单个游戏的完整状态"""

    def __init__(self, game_type, game_topic):
        self.game_type = game_type
        self.game_topic = game_topic
        self.game_data = None          # 设计师输出
        self.round = 0                 # 当前轮次 (0-based)
        self.scores = []               # 每轮得分
        self.memory = ""               # 累积记忆
        self.prev_paragraph = ""       # 前一段落
        self.prev_instruction = ""     # 上一个选择的指令
        self.summary = ""              # 首轮摘要
        self.created_at = time.time()
        self.completed = False
        self.results = None
        self.dimensions = Config.PHQ9_DIMENSIONS.copy()
        # 当前展示给用户的轮次数据
        self.current = {
            "paragraph": "",
            "instruction_1": "",
            "instruction_2": "",
        }


# 游戏存储（内存 + 锁保证线程安全）
games = {}
games_lock = Lock()

# 游戏过期时间（30分钟无活动自动清理）
GAME_TTL = 1800


def cleanup_old_games():
    """清理过期游戏"""
    now = time.time()
    with games_lock:
        expired = [gid for gid, g in games.items() if now - g.created_at > GAME_TTL]
        for gid in expired:
            del games[gid]


def get_game(game_id):
    """安全获取游戏状态"""
    with games_lock:
        g = games.get(game_id)
        if g:
            g.created_at = time.time()  # 刷新时间
        return g


def store_game(game_id, state):
    """安全存储游戏状态"""
    with games_lock:
        games[game_id] = state


def delete_game(game_id):
    """安全删除游戏"""
    with games_lock:
        games.pop(game_id, None)


# ===== 路由 =====

@app.route("/")
def index():
    """主页：游戏入口"""
    return render_template("web_game.html")


@app.route("/api/health")
def health():
    """健康检查"""
    return jsonify({"status": "ok", "games": len(games)})


@app.route("/api/start", methods=["POST"])
def api_start():
    """
    开始新游戏。
    运行设计师智能体 → 控制器（首轮）→ 评论家 → 返回第一轮内容
    """
    data = request.get_json() or {}
    game_type = data.get("game_type", "奇幻")
    game_topic = data.get("game_topic", "疗愈之旅")

    # 定期清理过期游戏
    cleanup_old_games()

    try:
        # Step 1: 设计师生成游戏配置
        print(f"[Web] 设计师开始生成，类型={game_type}，主题={game_topic}")
        game_data = run_designer(game_type=game_type, game_topic=game_topic)

        # Step 2: 初始化状态
        state = GameState(game_type, game_topic)
        state.game_data = game_data

        # Step 3: 首轮 — 控制器 (is_first_round=True)
        scale_item = game_data["redesigned_scale"][0]
        controller_out = run_controller(
            title=game_data["title"],
            outline=game_data["outline"],
            scale_item=scale_item,
            progress=11.1,
            memory="",
            prev_paragraph="",
            prev_instruction="",
            is_first_round=True,
            game_type=game_type,
            game_topic=game_topic,
            round_index=0,
        )

        # Step 4: 评论家优化
        critic_out = run_critic(
            paragraph=controller_out.get("paragraph", ""),
            memory="",
            instruction_1=controller_out.get("instruction_1", ""),
            instruction_2=controller_out.get("instruction_2", ""),
            is_first_round=True,
        )

        # Step 5: 保存状态
        state.current["paragraph"] = critic_out.get("paragraph", "")
        state.current["instruction_1"] = critic_out.get("instruction_1", "")
        state.current["instruction_2"] = critic_out.get("instruction_2", "")
        state.summary = controller_out.get("summary", "")
        state.memory = critic_out.get("memory", controller_out.get("summary", "") or "")
        state.prev_paragraph = state.current["paragraph"]

        game_id = str(uuid.uuid4())
        store_game(game_id, state)

        print(f"[Web] 游戏 {game_id[:8]} 创建成功，标题：{game_data['title']}")

        return jsonify({
            "game_id": game_id,
            "game_title": game_data["title"],
            "design_rationale": game_data.get("design_rationale", ""),
            "round": 1,
            "total_rounds": 9,
            "dimension": state.dimensions[0],
            "paragraph": state.current["paragraph"],
            "instruction_1": state.current["instruction_1"],
            "instruction_2": state.current["instruction_2"],
        })

    except Exception as e:
        print(f"[Web] 游戏创建失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"游戏创建失败: {str(e)}",
            "detail": "请检查 API Key 和网络连接后重试",
        }), 500


@app.route("/api/choice", methods=["POST"])
def api_choice():
    """
    用户做出选择后的处理。
    记录分数 → 如果还有下一轮则生成 → 否则返回结果
    """
    data = request.get_json() or {}
    game_id = data.get("game_id", "")
    choice = int(data.get("choice", 2))

    state = get_game(game_id)
    if not state:
        return jsonify({"error": "游戏不存在或已过期，请重新开始"}), 404

    try:
        # 计算本轮得分
        # instruction_1 = 1分（抑郁倾向），instruction_2 = 0分（健康）
        score = 1 if choice == 1 else 0
        state.scores.append(score)
        state.round += 1

        # 更新上一个选择的指令（用于下一轮控制器的上下文）
        state.prev_instruction = (
            state.current["instruction_1"] if choice == 1
            else state.current["instruction_2"]
        )

        # 更新记忆
        round_label = f"第{state.round}轮"
        choice_label = "抑郁倾向" if score == 1 else "健康"
        state.memory = (
            f"{state.memory}\n{round_label}：玩家选择了{choice_label}方向。"
            if state.memory
            else f"{round_label}：玩家选择了{choice_label}方向。"
        )

        # 检查是否完成
        if state.round >= 9:
            state.completed = True
            state.results = format_results(state.scores, state.dimensions)

            # 构建逐轮详情
            dimension_details = []
            for i, dim in enumerate(state.dimensions):
                s = state.scores[i] if i < len(state.scores) else 0
                dimension_details.append({
                    "round": i + 1,
                    "name": dim,
                    "score": s,
                    "result": "有倾向" if s == 1 else "无倾向",
                })

            result_data = {
                "completed": True,
                "total_score": state.results["total_score"],
                "severity": state.results["severity"],
                "dimensions": dimension_details,
            }

            delete_game(game_id)
            return jsonify(result_data)

        # 生成下一轮
        scale_item = state.game_data["redesigned_scale"][state.round]
        progress = (state.round + 1) / 9 * 100

        controller_out = run_controller(
            title=state.game_data["title"],
            outline=state.game_data["outline"],
            scale_item=scale_item,
            progress=progress,
            memory=state.memory,
            prev_paragraph=state.prev_paragraph,
            prev_instruction=state.prev_instruction,
            is_first_round=False,
            round_index=state.round,
        )

        critic_out = run_critic(
            paragraph=controller_out.get("paragraph", ""),
            memory=controller_out.get("memory", ""),
            instruction_1=controller_out.get("instruction_1", ""),
            instruction_2=controller_out.get("instruction_2", ""),
            round_index=state.round,
        )

        # 更新状态
        state.current["paragraph"] = critic_out.get("paragraph", "")
        state.current["instruction_1"] = critic_out.get("instruction_1", "")
        state.current["instruction_2"] = critic_out.get("instruction_2", "")
        state.memory = critic_out.get("memory", state.memory)
        state.prev_paragraph = state.current["paragraph"]

        # 写回存储
        store_game(game_id, state)

        return jsonify({
            "completed": False,
            "round": state.round + 1,
            "total_rounds": 9,
            "dimension": state.dimensions[state.round],
            "paragraph": state.current["paragraph"],
            "instruction_1": state.current["instruction_1"],
            "instruction_2": state.current["instruction_2"],
            "scores_so_far": sum(state.scores),
            "last_score": score,
        })

    except Exception as e:
        print(f"[Web] 轮次处理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"故事生成失败: {str(e)}",
            "round": state.round + 1,
        }), 500


# ===== 启动 =====

if __name__ == "__main__":
    if not Config.validate():
        print("\n⚠️  配置验证失败，请确保已设置 DEEPSEEK_API_KEY")
        print("   参考 .env.example 创建 .env 文件\n")

    print("=" * 50)
    print("  PsychoGAT Web 版启动")
    print(f"  模型: {Config.MODEL}")
    print(f"  地址: http://127.0.0.1:5000")
    print("=" * 50)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True,
    )
