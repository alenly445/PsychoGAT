"""
日志与进度输出工具
"""

import sys
from datetime import datetime
from config import Config


class Logger:
    """统一的日志管理器"""

    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "red": "\033[91m",
    }

    def __init__(self, verbose=None):
        self.verbose = verbose if verbose is not None else Config.VERBOSE
        self.log_buffer = []

    def _color(self, text, color):
        """如果支持颜色则着色"""
        if sys.stdout.isatty():
            return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
        return text

    def info(self, msg, color=""):
        """普通信息"""
        if color:
            msg = self._color(msg, color)
        print(msg)
        self.log_buffer.append(("info", msg))

    def agent(self, name, msg):
        """智能体输出"""
        colored = self._color(f"[{name}] {msg}", "cyan" if "设计师" in name else
                              "green" if "控制器" in name else
                              "yellow" if "评论家" in name else
                              "magenta" if "模拟器" in name else "")
        print(colored)
        self.log_buffer.append(("agent", f"[{name}] {msg}"))

    def detail(self, msg):
        """详细信息（仅在 verbose 模式下显示）"""
        if self.verbose:
            dimmed = self._color(f"  {msg}", "dim")
            print(dimmed)
        self.log_buffer.append(("detail", msg))

    def progress(self, current, total, label=""):
        """进度显示"""
        percent = current / total * 100
        bar_len = 30
        filled = int(bar_len * current / total)
        bar = "█" * filled + "░" * (bar_len - filled)
        label_str = f" {label}" if label else ""
        msg = f"  进度: [{bar}] {current}/{total} ({percent:.0f}%){label_str}"
        self.info(msg)

    def section(self, title):
        """分节标题"""
        border = "=" * 55
        self.info("")
        self.info(self._color(border, "bold"))
        self.info(self._color(f"  {title}", "bold"))
        self.info(self._color(border, "bold"))

    def result_table(self, title, results):
        """结果表格"""
        self.section(title)
        for key, value in results.items():
            if isinstance(value, dict):
                self.info(self._color(f"  {key}:", "bold"))
                for k, v in value.items():
                    self.info(f"    {k}: {v}")
            else:
                self.info(f"  {key}: {value}")

    def error(self, msg):
        """错误信息"""
        self.info(self._color(f"  ❌ {msg}", "red"))

    def warning(self, msg):
        """警告信息"""
        self.info(self._color(f"  ⚠️  {msg}", "yellow"))

    def divider(self):
        """分隔线"""
        self.info("-" * 55)

    def get_log(self) -> str:
        """获取完整日志"""
        return "\n".join(
            msg for _, msg in self.log_buffer
        )

    def get_json_log(self) -> list:
        """获取结构化日志"""
        return [{"type": t, "message": msg} for t, msg in self.log_buffer]
