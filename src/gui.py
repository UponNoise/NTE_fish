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
    FishState.START: "启动",
    FishState.INIT_SETUP: "首次换饵",
    FishState.CAST: "抛竿",
    FishState.WAIT_BITE: "定时按F等待",
    FishState.HOOK: "起勾",
    FishState.REELING: "遛鱼(A/D)",
    FishState.COLLECT: "收杆",
    FishState.CHECK_BAIT: "检查鱼饵",
    FishState.SELL_BUY: "出售购买(占位)",
    FishState.STOPPED: "已停止",
}


class FishingBotGUI:
    """钓鱼机器人图形界面"""

    def __init__(self):
        self.bot = FishingBot()
        self._running = False

        # 主窗口
        self.root = tk.Tk()
        self.root.title("异环钓鱼自动化 v2.0 (键鼠)")
        self.root.geometry("720x720")
        self.root.resizable(True, True)

        # 设置机器人回调
        self.bot.set_on_log(self._append_log)
        self.bot.set_on_state_change(self._update_state_display)
        self.bot.set_on_fish_caught(self._update_fish_count)
        self.bot.set_on_stopped(self._on_bot_stopped)

        self._build_ui()
        self._update_state_display(FishState.START, FishState.START)
        self._run_startup_checks()

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
        ttk.Label(basic_frame, text="定时按F间隔 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_bite_f_interval = tk.DoubleVar(value=config.bite_f_interval)
        ttk.Spinbox(
            basic_frame, from_=1.0, to=10.0, increment=0.5,
            textvariable=self.var_bite_f_interval, width=8
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
        ttk.Label(reel_frame, text="遛鱼按键时长 (秒):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.var_reel_press = tk.DoubleVar(value=config.reel_press_duration)
        ttk.Spinbox(
            reel_frame, from_=0.02, to=0.3, increment=0.01,
            textvariable=self.var_reel_press, width=8
        ).grid(row=row, column=1, sticky=tk.W, pady=2)

        ttk.Label(
            reel_frame,
            text="遛鱼: 检测上半屏幕 green_zone 与 float_marker\n"
                 "若 green_zone 在左 → 按 A  |  若 green_zone 在右 → 按 D\n"
                 "保持 float_marker 重叠于 green_zone 上方",
            foreground="gray",
        ).grid(row=row + 1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # ---- 窗口捕获 ----
        win_frame = ttk.Frame(notebook, padding=10)
        notebook.add(win_frame, text="窗口捕获")

        # 窗口捕获开关
        self.var_use_window = tk.BooleanVar(value=config.use_window_capture)
        ttk.Checkbutton(
            win_frame,
            text="启用窗口捕获模式（自动定位 HTGame.exe 游戏窗口）",
            variable=self.var_use_window,
            command=self._on_window_mode_toggle,
        ).pack(anchor=tk.W, pady=5)

        ttk.Label(
            win_frame,
            text="目标进程名:",
        ).pack(anchor=tk.W)
        proc_frame = ttk.Frame(win_frame)
        proc_frame.pack(fill=tk.X, pady=2)
        self.var_process_name = tk.StringVar(value=config.target_process)
        ttk.Entry(
            proc_frame, textvariable=self.var_process_name, width=20
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            proc_frame, text="检测窗口", command=self._detect_window
        ).pack(side=tk.LEFT, padx=5)

        # 窗口信息显示
        self.win_info_frame = ttk.LabelFrame(win_frame, text="游戏窗口信息", padding=8)
        self.win_info_frame.pack(fill=tk.X, pady=10)

        self.lbl_win_status = ttk.Label(
            self.win_info_frame, text="状态: 未检测", foreground="gray"
        )
        self.lbl_win_status.pack(anchor=tk.W)
        self.lbl_win_rect = ttk.Label(
            self.win_info_frame, text="位置: —", foreground="gray"
        )
        self.lbl_win_rect.pack(anchor=tk.W)
        self.lbl_win_size = ttk.Label(
            self.win_info_frame, text="分辨率: —", foreground="gray"
        )
        self.lbl_win_size.pack(anchor=tk.W)

        # ---- 手动捕获区域（窗口模式关闭时使用） ----
        self.manual_region_frame = ttk.LabelFrame(win_frame, text="手动捕获区域", padding=8)
        self.manual_region_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            self.manual_region_frame,
            text="分辨率范围: 800×600 ~ 3840×2160\n格式: left, top, width, height",
            foreground="gray",
        ).pack(anchor=tk.W, pady=2)

        entry_frame = ttk.Frame(self.manual_region_frame)
        entry_frame.pack(fill=tk.X, pady=5)

        ttk.Label(entry_frame, text="L:").pack(side=tk.LEFT, padx=1)
        self.var_region_left = tk.IntVar(value=0)
        ttk.Entry(entry_frame, textvariable=self.var_region_left, width=5).pack(side=tk.LEFT, padx=2)

        ttk.Label(entry_frame, text="T:").pack(side=tk.LEFT, padx=1)
        self.var_region_top = tk.IntVar(value=0)
        ttk.Entry(entry_frame, textvariable=self.var_region_top, width=5).pack(side=tk.LEFT, padx=2)

        ttk.Label(entry_frame, text="W:").pack(side=tk.LEFT, padx=1)
        self.var_region_w = tk.IntVar(value=1920)
        ttk.Entry(entry_frame, textvariable=self.var_region_w, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(entry_frame, text="H:").pack(side=tk.LEFT, padx=1)
        self.var_region_h = tk.IntVar(value=1080)
        ttk.Entry(entry_frame, textvariable=self.var_region_h, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            self.manual_region_frame, text="应用手动区域", command=self._apply_region
        ).pack(pady=5)

        # 初始状态：窗口模式默认启用，隐藏手动区域
        self._on_window_mode_toggle()

        # ---- 环境检查 ----
        env_frame = ttk.Frame(notebook, padding=10)
        notebook.add(env_frame, text="环境检查")

        self.env_text = tk.Text(
            env_frame, height=12, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), bg="#f5f5f5",
        )
        self.env_text.pack(fill=tk.BOTH, expand=True)
        ttk.Button(
            env_frame, text="重新检查环境", command=self._run_startup_checks
        ).pack(pady=5)

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

        # 窗口模式下，检查能否找到游戏窗口
        if config.use_window_capture:
            win_info = self.bot.find_game_window()
            if win_info is None:
                messagebox.showwarning(
                    "窗口未找到",
                    f"未找到 {config.target_process} 的游戏窗口！\n\n"
                    "请先启动游戏，或关闭窗口捕获模式使用手动区域。",
                )
                return

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
        config.bite_f_interval = self.var_bite_f_interval.get()
        config.reel_timeout = self.var_reel_timeout.get()
        config.max_cycles = self.var_max_cycles.get()
        config.bait_low_threshold = self.var_bait_threshold.get()
        config.button_press_duration = self.var_press_duration.get()
        config.reel_press_duration = self.var_reel_press.get()
        config.use_window_capture = self.var_use_window.get()
        config.target_process = self.var_process_name.get()

        # 同步捕获模式到 bot
        self.bot.capture.set_window_mode(
            enabled=config.use_window_capture,
            process_name=config.target_process,
        )
        self._log("[设置] 已应用")

    def _apply_region(self):
        """应用手动捕获区域设置（含分辨率校验）"""
        from config import RESOLUTION_MIN, RESOLUTION_MAX

        left = self.var_region_left.get()
        top = self.var_region_top.get()
        w = self.var_region_w.get()
        h = self.var_region_h.get()

        # 分辨率校验
        if w < RESOLUTION_MIN[0] or h < RESOLUTION_MIN[1]:
            messagebox.showwarning(
                "分辨率过低",
                f"捕获区域不能小于 {RESOLUTION_MIN[0]}×{RESOLUTION_MIN[1]}（当前 {w}×{h}）",
            )
            return
        if w > RESOLUTION_MAX[0] or h > RESOLUTION_MAX[1]:
            messagebox.showwarning(
                "分辨率过高",
                f"捕获区域不能大于 {RESOLUTION_MAX[0]}×{RESOLUTION_MAX[1]}（当前 {w}×{h}）",
            )
            return

        config.capture_region = (left, top, w, h)
        self.bot.capture.set_region(config.capture_region)
        self._log(f"[区域] 手动捕获区域设为 ({left}, {top}, {w}, {h})")

    # ---- 窗口检测 ----

    def _detect_window(self):
        """检测 HTGame.exe 游戏窗口"""
        process_name = self.var_process_name.get()
        self._log(f"[窗口] 正在查找进程 {process_name} ...")

        win_info = self.bot.find_game_window()

        if win_info is None:
            self.lbl_win_status.config(text="状态: ❌ 未找到", foreground="red")
            self.lbl_win_rect.config(text="位置: —")
            self.lbl_win_size.config(text="分辨率: —")
            self._log(f"[窗口] 未找到进程 {process_name}，请确认游戏已启动")
            return

        self.lbl_win_status.config(
            text=f"状态: ✅ 已找到 ({process_name})", foreground="green"
        )
        self.lbl_win_rect.config(
            text=f"位置: left={win_info['left']}, top={win_info['top']}"
        )
        w, h = win_info["width"], win_info["height"]
        self.lbl_win_size.config(text=f"分辨率: {w}×{h}")

        # 回填到手动区域
        self.var_region_left.set(win_info["left"])
        self.var_region_top.set(win_info["top"])
        self.var_region_w.set(w)
        self.var_region_h.set(h)

        self._log(f"[窗口] 已找到: ({win_info['left']}, {win_info['top']}) {w}×{h}")

    def _on_window_mode_toggle(self):
        """窗口捕获模式切换"""
        if self.var_use_window.get():
            self.manual_region_frame.pack_forget()
            self._detect_window()
        else:
            self.manual_region_frame.pack(fill=tk.X, pady=10)

    # ---- 环境检查 ----

    def _run_startup_checks(self):
        """启动时检查运行环境"""
        self.env_text.config(state=tk.NORMAL)
        self.env_text.delete("1.0", tk.END)

        lines = []
        lines.append("═" * 45)
        lines.append("  NTE 异环钓鱼自动化 - 环境检查")
        lines.append("═" * 45)
        lines.append("")

        # 1. Python 版本
        import sys
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        lines.append(f"  Python 版本    : {py_ver}  {'✅' if sys.version_info >= (3, 10) else '❌ 需要 3.10+'}")

        # 2. 依赖检查
        modules = {
            "cv2": "opencv-python",
            "numpy": "numpy",
            "mss": "mss",
            "PIL": "Pillow",
            "win32gui": "pywin32",
            "psutil": "psutil",
        }
        for mod, pkg in modules.items():
            try:
                __import__(mod)
                lines.append(f"  {pkg:<15}: ✅ 已安装")
            except ImportError:
                lines.append(f"  {pkg:<15}: ❌ 未安装 (pip install {pkg})")

        # 3. 管理员权限
        try:
            import ctypes
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
            lines.append(f"  管理员权限    : {'✅ 已启用' if is_admin else '⚠️ 未启用（若游戏用管理员运行，脚本也需管理员运行）'}")
        except Exception:
            lines.append("  管理员权限    : ⚠️ 无法检测")

        # 4. HTGame.exe
        try:
            from src.window_capture import WindowCapture
            wins = WindowCapture.list_game_windows("HTGame.exe")
            if wins:
                lines.append(f"  HTGame.exe      : ✅ 已运行 ({len(wins)} 个窗口)")
                for w in wins:
                    lines.append(f"    └─ {w['title'][:40]}  {w['size']}")
            else:
                lines.append(f"  HTGame.exe      : ⚠️ 未检测到进程（请先启动游戏）")
        except Exception:
            lines.append(f"  HTGame.exe      : ⚠️ 无法检测（pywin32 未安装）")

        lines.append("")
        lines.append("  键鼠模式: 使用 Windows SendInput 扫描码模拟 F/A/D/E + 鼠标点击")

        self.env_text.insert("1.0", "\n".join(lines))
        self.env_text.config(state=tk.DISABLED)

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
