# 图像识别素材规范

本目录存放用于图像识别的模板图片。脚本通过 OpenCV 模板匹配来定位屏幕上的 UI 元素。

## 命名规范

推荐使用 **英文小写 + 下划线** 命名，并按场景/功能前缀组织（如 `shop_sell_all.png`、`dialog_confirm.png`、`scene_catch_screen_full.png`）。支持 `.png` / `.jpg` / `.jpeg` 格式。程序仍兼容旧英文名与中文旧名（见“兼容旧名”）。

## 所需素材清单

### 换鱼饵界面

| 文件名 | 用途 | 截图建议 |
|--------|------|----------|
| `exchange_bait.png` | 换鱼饵界面标识 | 换鱼饵界面的特征标题/背景 |
| `bait.png` | 鱼饵选项图标 | 鱼饵物品的图标 |
| `exchange.png` | 确认更换按钮 | "更换"/"确认" 按钮 |

### 钓鱼流程

| 文件名 | 用途 | 截图建议 |
|--------|------|----------|
| `bite_indicator.png` | 鱼上钩指示 | 鱼咬钩时的水花特效或"！"提示 |
| `green_zone.png` | 绿色安全区域 | 遛鱼进度条上的绿色目标区域（仅截区域本身） |
| `float_marker.png` | 黄色浮标 | 进度条上移动的浮标标记（仅截浮标本身） |
| `catch_success.png` | 钓鱼成功 | 收杆成功的提示/图标 |
| `catch_fail.png` | 钓鱼失败 | 收杆失败的提示/图标 |

### 场景辅助

| 文件名 | 用途 | 截图建议 |
|--------|------|----------|
| `scene_catch_screen_full.png` | 收杆结果场景参考 | 完整截图，脚本会裁剪底部 UI 作为辅助模板（仅用于兜底匹配） |

### 商店/出售

| 文件名 | 用途 | 截图建议 |
|--------|------|----------|
| `bait_low_warning.png` | 鱼饵不足警告 | 鱼饵不足时的弹窗或提示文字 |
| `shop_quick_submit.png` | 快捷提交按钮 | 出售流程中的“快捷提交”按钮 |
| `shop_sell_all.png` | 一键出售按钮 | 渔获出售界面的“一键出售”按钮 |
| `dialog_confirm.png` | 确认按钮 | 弹窗中的“确认”按钮 |
| `dialog_close.png` | 关闭按钮 | 弹窗右上角关闭按钮 |
| `shop_fish_warehouse.png` | 渔获仓库入口 | 商店页左侧仓库入口图标 |
| `shop_fish_warehouse_alt.png` | 渔获仓库入口（备用样式） | 备用图标或不同状态下的样式 |
| `shop_go_fishing.png` | 前往钓鱼按钮 | 出售流程中的“前往钓鱼”按钮 |

## 兼容旧名

以下旧文件名仍被识别（新项目建议使用结构化命名）：

| 旧文件名 | 新文件名 |
|----------|----------|
| `sell_all.png` | `shop_sell_all.png` |
| `quick_submit.png` | `shop_quick_submit.png` |
| `confirm.png` | `dialog_confirm.png` |
| `close.png` | `dialog_close.png` |
| `fish_warehouse.png` | `shop_fish_warehouse.png` |
| `fish_warehouse2.png` | `shop_fish_warehouse_alt.png` |
| `go_fishing.png` | `shop_go_fishing.png` |
| `微信截图_20260531175027.png` | `shop_sell_all.png` |
| `微信截图_20260531174925.png` | `shop_quick_submit.png` |
| `微信截图_20260531175512.png` | `dialog_confirm.png` |
| `微信截图_20260531175442.png` | `dialog_close.png` |
| `渔获仓库.png` | `shop_fish_warehouse.png` |
| `渔获仓库2.png` | `shop_fish_warehouse_alt.png` |
| `微信截图_20260531175556.png` | `shop_go_fishing.png` |
| `1.png` | `scene_catch_screen_full.png` |

## 截图要求

1. **分辨率**：程序会尝试多尺度匹配，但素材仍建议来自同一套游戏分辨率/UI 缩放
2. **UI缩放**：确保游戏 UI 缩放尽量与截图时相同
3. **裁剪精确**：尽量仅截取目标元素，减少无关背景
4. **特征唯一**：选择在屏幕上唯一的元素，避免误匹配
5. **格式**：建议使用 PNG 无损格式
6. **进程锁**：脚本仅捕获 HTGame.exe 进程画面，确保截图来自该进程窗口

## 调整匹配阈值

如果识别不准确，可以在 GUI 的「基本设置」中调整「模板匹配阈值」：
- 提高阈值（如 0.85~0.9）：更严格，减少误判但可能漏判
- 降低阈值（如 0.7~0.75）：更宽松，增加识别率但可能误判
