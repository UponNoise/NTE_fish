# 异环钓鱼自动化脚本 (NTE Fish Bot)

基于图像识别和虚拟手柄模拟的《异环》游戏钓鱼自动化脚本。

## 功能

- 🎣 自动抛竿（A键）→ 等待上钩 → 起勾（A键）→ 遛鱼（LT/RT扳机）→ 循环
- 🛒 鱼饵不足时自动进入渔获商店出售（X键）→ 购买鱼饵（菜单键）→ 返回继续
- 🖥️ GUI 图形界面，实时显示状态和日志
- 🎯 基于 OpenCV 模板匹配的图像识别
- 🕹️ 虚拟 Xbox 360 手柄模拟（vgamepad + ViGEmBus）
- 🪟 智能窗口捕获：自动定位 HTGame.exe 游戏窗口，无需手动设置区域
- 📐 分辨率约束：800×600 ~ 3840×2160，自动裁剪/校验
- 🐳 Docker 支持：容器化环境便于验证和 CI/CD
- ⚙️ 所有参数可在 GUI 中调整

## 快速开始

### 方式一：一键部署（推荐）

```bash
# 双击运行或命令行执行
setup.bat
```

脚本会自动完成：Python 检查 → 虚拟环境创建 → 依赖安装 → 驱动检测

### 方式二：手动安装

### 前置条件

- Windows 10/11
- Python 3.10+
- [ViGEmBus 驱动](https://github.com/nefarius/ViGEmBus/releases)（虚拟手柄必需）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/UponNoise/NTE_fish.git
cd NTE_fish

# 2. 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
```

## 使用方法

```bash
python main.py
```

1. 启动游戏（HTGame.exe），进入钓鱼准备界面
2. 运行脚本，GUI 启动后会自动检测游戏窗口
3. 检查「窗口捕获」页面确认已找到游戏窗口
4. 点击「开始钓鱼」，脚本将自动循环

### Docker 使用

```bash
# 构建镜像
docker build -t nte-fish-bot .

# 验证环境
docker-compose up
```

> ⚠️ 注意：Docker 仅用于环境验证和 CI/CD。实际操作屏幕/手柄需要在宿主机运行。

## 图像素材

图像素材存放在 `assets/` 目录下，脚本通过模板匹配来识别游戏状态。

**你需要自行截图并提供以下素材**（详见 `assets/README.md`）：

| 文件名 | 用途 | 说明 |
|--------|------|------|
| `cast_prompt` | 抛竿提示 | 识别可抛竿状态的提示图标/文字 |
| `bite_indicator` | 上钩指示 | 鱼上钩时的特效或提示 |
| `progress_bar_bg` | 进度条背景 | 遛鱼界面顶部的进度条背景 |
| `float_marker` | 浮标 | 进度条上左右移动的黄色浮标 |
| `green_zone` | 绿色区域 | 进度条上需要保持浮标在其中的绿色区域 |
| `catch_success` | 收杆成功 | 钓鱼成功后的提示 |
| `bait_low_warning` | 鱼饵不足 | 鱼饵不足的警告提示 |
| `shop_title` | 商店标题 | 商店界面的标题文字/图标 |
| `sell_confirm` | 出售确认 | 出售渔获确认界面 |

## 项目结构

```
NTE_fish/
├── main.py                    # 主入口
├── config.py                  # 全局配置
├── requirements.txt           # Python 依赖
├── README.md                  # 本文件
├── .gitignore
├── assets/                    # 图像识别素材
│   └── README.md              # 素材命名规范
└── src/
    ├── __init__.py
    ├── gui.py                 # GUI 界面 (tkinter)
    ├── fishing_bot.py         # 机器人主逻辑
    ├── state_machine.py       # 状态机
    ├── screen_capture.py      # 屏幕捕获 (mss)
    ├── image_recognizer.py    # 图像识别 (OpenCV)
    └── input_simulator.py     # 手柄模拟 (vgamepad)
```

## 遛鱼机制

游戏在屏幕上方显示一个进度条：
- **黄色浮标** 在进度条上左右移动
- **绿色区域** 是目标区间
- 脚本通过识别浮标和绿色区域的相对位置，自动按下 **LT**（向左）或 **RT**（向右）使浮标保持在绿色区域内

## 注意事项

- 需要安装 ViGEmBus 驱动才能使用虚拟手柄功能
- 图像素材需要与你的游戏画面分辨率/UI缩放一致
- 建议在窗口化或无边窗口模式下运行游戏，便于截屏
- 首次使用请先在 GUI 中调整各项参数

## License

MIT
