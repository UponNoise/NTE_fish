# 异环钓鱼自动化脚本 (NTE Fish Bot)

基于图像识别和 Windows 键鼠模拟的《异环》游戏钓鱼自动化脚本。

## 功能

- 🎣 启动后直接尝试换饵并抛竿（F键）→ 等待上钩 → 起勾（F键）→ 遛鱼（A/D键）→ 循环
- 🛒 识别出售/确认/返回钓鱼相关按钮，尽量自动处理出售流程
- 🔄 首次自动换饵：E键 → 识别 bait → 点击 exchange
- 🖥️ GUI 图形界面，实时显示状态和日志
- 🎯 基于 OpenCV 的多尺度模板匹配，支持中文素材文件名
- ⌨️ 键鼠模拟：支持 scan_code / vk / keybd_event 三种 Windows 输入方式
- 🪟 智能窗口捕获：自动定位 HTGame.exe 游戏窗口
- 📐 分辨率约束：800×600 ~ 3840×2160
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

如果游戏以管理员身份运行，请优先使用 `run_admin.bat` 启动脚本。

1. 启动游戏（HTGame.exe），站到可钓鱼的位置
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

> ⚠️ Docker 仅用于环境验证和 CI/CD。实际操作屏幕/键鼠需要在 Windows 宿主机运行。

## 图像素材

图像素材存放在 `assets/` 目录下，脚本通过模板匹配来识别游戏状态。

**你需要自行截图并提供以下素材**（详见 `assets/README.md`）：

| 文件名 | 用途 | 说明 |
|--------|------|------|
| `bite_indicator` | 上钩指示 | 鱼上钩时的特效或提示 |
| `float_marker` | 浮标 | 进度条上左右移动的黄色浮标 |
| `green_zone` | 绿色区域 | 进度条上需要保持浮标在其中的绿色区域 |
| `catch_success` | 收杆成功 | 钓鱼成功后的提示 |
| `bait_low_warning` | 鱼饵不足 | 鱼饵不足的警告提示 |
| `bait` / `exchange` | 换饵 | 鱼饵图标和更换按钮 |

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
    └── input_simulator.py     # Windows 键鼠输入模拟
```

## 遛鱼机制

游戏屏幕上半部分显示绿色的 `green_zone` 和黄色的 `float_marker`，脚本检测二者在 x 轴上的相对位置：
- **green_zone 在左** → 按 **A**（向左调整）
- **green_zone 在右** → 按 **D**（向右调整）
- 保持 `float_marker` 重叠于 `green_zone` 上方，直到识别到 `catch_success` 或 `catch_fail`

## 注意事项

- 若游戏以管理员身份运行，脚本也需要以管理员身份运行，否则 Windows 会拦截模拟输入
- 若 F/A/D/E 仍无效，在 GUI 中把「输入方式」从 `scan_code` 切到 `vk` 或 `keybd_event` 试一次
- 图像素材建议与你的游戏画面分辨率/UI 缩放一致；程序会自动尝试多尺度匹配
- 建议在窗口化或无边窗口模式下运行游戏，便于截屏
- 首次使用请先在 GUI 中调整各项参数

## License

MIT
