"""
钓鱼机器人 GUI - 基于 tkinter
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from datetime import datetime

from config import config, BotConfig
from src.fishing_bot import FishingBot
from src.state_machine import FishState


# 状态中文映射
STATE_NAMES: dict[FishState, str] = {
    FishState.IDLE: "空闲",
    FishState.CASTING: "抛竿",
    FishState.WAITING_BITE: "等待上钩",
    FishState.HOOKING: "起勾",
    FishState.REELING: "遛鱼",
    FishState.CHECKING_BAIT: "检查鱼饵",
    FishState.SELLING: "出售渔获",
    FishState.BUYING_BAIT: "购买鱼饵",
    FishState.STOPPED: "已停止",
}


class FishingBotGUI:
    """钓鱼机器人图形界面"""

    def __init__(self):
        self.bot = FishingBot()
        self._running = False

        # 主窗口
        self.root = tk.Tk()
        self.root.title("异环钓鱼自动化 v1.0")
        self.root.geometry("700x650")
        self.root.resizable(True, True)

        # 设置机器人回调
        self.bot.set_on_log(self._append_log)
        self.bot.set_on_state_change(self._update_state_display)
        self.bot.set_on_fish_caught(self._update_fish_count)
        self.bot.set_on_stopped(self._on_bot_stopped)

        self._build_ui()
        self._update_state_display(FishState.IDLE, FishState.IDLE)

    # ---- UI 构建 ----

    def _build_ui(self):
        # 顶部控制栏
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)

        self.btn_start = ttk.Button(
            control_frame, text="▶ 开始钓鱼", command=self._on_start
        )
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(
            control_frame, text="⏹ 停止", command=self._on_stop, state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )

        # 状态显示
        ttk.Label(control_frame, text="当前状态:").pack(side=tk.LEFT, padx=5)
        self.lbl_state = ttk.Label(control_frame, text="空闲", font=("", 10, "bold"))
        self.lbl_state.pack(side=tk.LEFT, padx=5)

        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )

        ttk.Label(control_frame, text="已钓:").pack(side=tk.LEFT, padx=5)
        self.lbl_fish = ttk.Label(control_frame, text="0", font=("", 10, "bold"))
        self.lbl_fish.pack(side=tk.LEFT, padx=2)

        ttk.Label(control_frame, text="循环:").pack(side=tk.LEFT, padx=5)
        self.lbl_cycle = ttk.Label(control_frame, text="0", font=("", 10, "bold"))
        self.lbl_cycle.pack(side=tk.LEFT, padx=2)

        # 设置面板
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ---- 基本设置 ----
        basic_frame = ttk.Frame(notebook, padding=10)
        notebook.add(basic_frame, text="基本设置")

        row = 0
        ttk.Label(basic_frame, text="屏幕捕获间隔 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_interval = tk.DoubleVar(value=config.screen_capture_interval)
        ttk.Spinbox(
            basic_frame, from_=0.05, to=1.0, increment=0.05,
            textvariable=self.var_interval, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(basic_frame, text="模板匹配阈值:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_threshold = tk.DoubleVar(value=config.match_threshold)
        ttk.Spinbox(
            basic_frame, from_=0.5, to=1.0, increment=0.05,
            textvariable=self.var_threshold, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(basic_frame, text="鱼上钩等待超时 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_bite_timeout = tk.DoubleVar(value=config.bite_timeout)
        ttk.Spinbox(
            basic_frame, from_=5, to=120, increment=5,
            textvariable=self.var_bite_timeout, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(basic_frame, text="遛鱼超时 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_reel_timeout = tk.DoubleVar(value=config.reel_timeout)
        ttk.Spinbox(
            basic_frame, from_=10, to=180, increment=10,
            textvariable=self.var_reel_timeout, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(basic_frame, text="最大循环次数 (0=无限):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_max_cycles = tk.IntVar(value=config.max_cycles)
        ttk.Spinbox(
            basic_frame, from_=0, to=9999, increment=10,
            textvariable=self.var_max_cycles, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(basic_frame, text="鱼饵不足阈值:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_bait_threshold = tk.IntVar(value=config.bait_low_threshold)
        ttk.Spinbox(
            basic_frame, from_=0, to=99, increment=1,
            textvariable=self.var_bait_threshold, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(basic_frame, text="按键持续时间 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_press_duration = tk.DoubleVar(value=config.button_press_duration)
        ttk.Spinbox(
            basic_frame, from_=0.05, to=1.0, increment=0.05,
            textvariable=self.var_press_duration, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Button(basic_frame, text="应用设置", command=self._apply_settings).grid(
            row=row, column=0, columnspan=2, pady=10
        )

        # ---- 遛鱼设置 ----
        reel_frame = ttk.Frame(notebook, padding=10)
        notebook.add(reel_frame, text="遛鱼设置")

        row = 0
        ttk.Label(reel_frame, text="遛鱼轻触最短 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_reel_min = tk.DoubleVar(value=config.reel_press_min)
        ttk.Spinbox(
            reel_frame, from_=0.01, to=0.3, increment=0.01,
            textvariable=self.var_reel_min, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(reel_frame, text="遛鱼轻触最长 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_reel_max = tk.DoubleVar(value=config.reel_press_max)
        ttk.Spinbox(
            reel_frame, from_=0.03, to=0.5, increment=0.01,
            textvariable=self.var_reel_max, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        row += 1
        ttk.Label(reel_frame, text="死区比例 (0~1):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_dead_zone = tk.DoubleVar(value=config.reel_dead_zone_ratio)
        ttk.Spinbox(
            reel_frame, from_=0.0, to=0.8, increment=0.05,
            textvariable=self.var_dead_zone, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        ttk.Label(
            reel_frame,
            text="死区：浮标在绿色区域中心附近\n此比例范围内时不操作，减少抖动",
            foreground="gray",
        ).grid(row=row + 1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # ---- 捕获区域 ----
        region_frame = ttk.Frame(notebook, padding=10)
        notebook.add(region_frame, text="捕获区域")

        ttk.Label(
            region_frame,
            text="设置屏幕捕获区域（留空使用全屏）：\n格式: left, top, width, height",
        ).pack(anchor=tk.W, pady=5)

        region_entry_frame = ttk.Frame(region_frame)
        region_entry_frame.pack(fill=tk.X, pady=5)

        ttk.Label(region_entry_frame, text="Left:").pack(side=tk.LEFT, padx=2)
        self.var_region_left = tk.IntVar(value=0)
        ttk.Entry(region_entry_frame, textvariable=self.var_region_left, width=6).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Label(region_entry_frame, text="Top:").pack(side=tk.LEFT, padx=2)
        self.var_region_top = tk.IntVar(value=0)
        ttk.Entry(region_entry_frame, textvariable=self.var_region_top, width=6).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Label(region_entry_frame, text="Width:").pack(side=tk.LEFT, padx=2)
        self.var_region_w = tk.IntVar(value=1920)
        ttk.Entry(region_entry_frame, textvariable=self.var_region_w, width=6).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Label(region_entry_frame, text="Height:").pack(side=tk.LEFT, padx=2)
        self.var_region_h = tk.IntVar(value=1080)
        ttk.Entry(region_entry_frame, textvariable=self.var_region_h, width=6).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Button(
            region_frame, text="应用捕获区域", command=self._apply_region
        ).pack(pady=10)

        ttk.Label(
            region_frame,
            text="提示：可以使用区域捕获来提高识别精度和性能",
            foreground="gray",
        ).pack(anchor=tk.W)

        # ---- 日志区域 ----
        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ---- 事件处理 ----

    def _on_start(self):
        if self._running:
            return
        self._apply_settings()
        self._running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("运行中...")
        self.bot.start()

    def _on_stop(self):
        self.bot.stop()
        self._on_bot_stopped()

    def _on_bot_stopped(self):
        self._running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("已停止")

    def _apply_settings(self):
        """应用 GUI 设置到全局配置"""
        config.screen_capture_interval = self.var_interval.get()
        config.match_threshold = self.var_threshold.get()
        config.bite_timeout = self.var_bite_timeout.get()
        config.reel_timeout = self.var_reel_timeout.get()
        config.max_cycles = self.var_max_cycles.get()
        config.bait_low_threshold = self.var_bait_threshold.get()
        config.button_press_duration = self.var_press_duration.get()
        config.reel_press_min = self.var_reel_min.get()
        config.reel_press_max = self.var_reel_max.get()
        config.reel_dead_zone_ratio = self.var_dead_zone.get()
        self._log("[设置] 已应用")

    def _apply_region(self):
        """应用捕获区域设置"""
        left = self.var_region_left.get()
        top = self.var_region_top.get()
        w = self.var_region_w.get()
        h = self.var_region_h.get()
        config.capture_region = (left, top, w, h)
        self.bot.capture.set_region(config.capture_region)
        self._log(f"[区域] 捕获区域设为 ({left}, {top}, {w}, {h})")

    def _append_log(self, msg: str):
        """追加日志（线程安全）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"

        def _do():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, line)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

        self.root.after(0, _do)

    def _update_state_display(self, old: FishState, new: FishState):
        """更新状态显示（线程安全）"""
        name = STATE_NAMES.get(new, new.name)

        def _do():
            self.lbl_state.config(text=name)
            self.lbl_cycle.config(text=str(self.bot.state_machine.cycle_count))

        self.root.after(0, _do)

    def _update_fish_count(self, count: int):
        """更新钓鱼计数（线程安全）"""
        def _do():
            self.lbl_fish.config(text=str(count))

        self.root.after(0, _do)

    def _log(self, msg: str):
        """GUI 内部日志"""
        self._append_log(msg)

    # ---- 运行 ----

    def run(self):
        """启动 GUI 主循环"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self._running:
            self.bot.stop()
        self.root.destroy()


def main():
    app = FishingBotGUI()
    app.run()


if __name__ == "__main__":
    main()
