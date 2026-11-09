<div align="center">
  <h1>Codex 定时唤醒</h1>
  <p><strong>每日多时段、自定义消息，隐藏到托盘后继续计时。</strong></p>
  <p><img alt="Windows" src="https://img.shields.io/badge/platform-Windows-0078D6"> <img alt="源码 V1.8" src="https://img.shields.io/badge/source-V1.8-B56C43"> <a href="https://github.com/hcycyxx/codex-alarm/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/hcycyxx/codex-alarm?color=3B77A1"></a></p>
</div>

Windows 本地桌面程序。只负责定时发送消息，不能直接设置或保证 Codex 的额度重置时间。

## 下载与版本

当前程序为 **V1.8**，下载对应的 **v1.8.0** 版本：

- **[下载可直接运行的 EXE](https://github.com/hcycyxx/codex-alarm/releases/download/v1.8.0/CodexAlarm_v1_8.exe)**，无需 Python。
- **[下载程序、源码与中文说明完整包](https://github.com/hcycyxx/codex-alarm/releases/download/v1.8.0/codex-alarm-v1.8-source-docs-20261109_v2.zip)**
- [查看 Release](https://github.com/hcycyxx/codex-alarm/releases/tag/v1.8.0) · [仓库原 EXE](v1_8/dist/Codex定时唤醒_v1_8.exe)
- [使用说明](v1_8/使用说明_v1_8.md) · [更新日志](CHANGELOG.md)

## 效果预览

![V1.8 定时计划界面（已有截图）](v1_8/preview_tray_button_20261106_111326.png)

仓库已有的 V1.8 界面截图；截图不代表真实发送已经验收。

## 功能

- 每日多个时段，可新增、删除、单独开关，支持滚轮调整时间。
- 默认北京时间 `04:50 / 09:51 / 14:52 / 19:53`，所有时段共用可编辑消息。
- 自动维护专用“定时唤醒”聊天，记录消息提交与模型完成状态。
- 液态玻璃视觉、大字体、可调窗口高度、连续滚动计划列表。
- 隐藏到 Windows 托盘后继续计时，点击图标恢复，右键可显示窗口或退出。

## 使用

1. 先安装并使用 ChatGPT 账号登录 Codex 桌面软件，确认 GPT-6.1 Sol 可用。
2. 下载并运行 [V1.8 EXE](https://github.com/hcycyxx/codex-alarm/releases/download/v1.8.0/CodexAlarm_v1_8.exe)；运行 EXE 不需要安装 Python。
3. 核对时间与消息，点击“检查连接”。
4. 可用“立即试发”核对弹窗后发送，再点击“开启定时”。每次启动默认暂停。
5. 保持电脑开机联网；可点击右上角“隐藏到托盘”。

程序只负责定时发送消息，不能直接设置或保证 Codex 的额度重置时间。实际额度以 Codex 显示为准。

## 运行细节

- 使用本机 Codex app-server 接口，与桌面软件共用本地聊天存储；桌面列表可能需要重新进入或刷新后显示新聊天。
- 当前固定选择 `gpt-6.1-sol`，沿用已有 Codex 服务配置。未调用单独的 OpenAI API Key 登录流程。
- 原专用聊天明确拒绝续写、报已被其他连接占用时，会在本次消息提交前新建同名专用聊天；原聊天保留。
- 超时、断连或已提交后的结果不明不会自动重发。
- 睡眠、关机或退出程序期间不能执行；错过超过两分钟的计划会跳过。没有自动唤醒或开机启动功能。
- 修改计划后需要重新开启定时。启动新版前先关闭旧版。
- V1.8 首次尝试继承旧版设置，新设置与记录保存在 `%LOCALAPPDATA%\CodexAlarm\v1_8`，以新快照保存。运行数据不在仓库中。

## 从源码构建

使用 Windows、Python 3.12，以及 Pillow、PyInstaller：

```powershell
python -m pip install Pillow pyinstaller
python v1_8/codex_alarm_v1_8.py
```

打包：

```powershell
powershell -ExecutionPolicy Bypass -File v1_8/build_v1_8.ps1
```

构建脚本会拒绝覆盖已有 EXE。重新构建时请使用新的输出目录或版本名。

## 版本与验证

仓库保留 V1 至 V1.8 的源码、产物与提交历史。请优先使用 V1.8；各版本的使用说明在对应目录。

V1.8 已做本地托盘图标、隐藏后计时器、恢复、退出清理与界面检查。检查中的发送被替换为本地模拟，没有调用真实模型。实际消息发送与额度变化需要用户自行验收。


## 更新、设置与卸载

更新前退出旧版，新版本保存到新目录，保留旧版便于回退。设置与记录位于 `%LOCALAPPDATA%\CodexAlarm\v1_8`。

卸载前暂停计划并完全退出，再删除程序；个人设置可先备份后自行移除。本工具不增加开机启动项。

## 常见问题

- **到点未发送**：检查程序是否仍运行、定时是否开启、电脑是否处于睡眠，以及 Codex 登录与本机连接状态。
- **发送结果不明**：先核对聊天和记录，避免直接重发。
- **托盘找不到**：检查 Windows 托盘折叠区域，详见 [V1.8 使用说明](v1_8/使用说明_v1_8.md)。

本仓库尚未声明独立的开源许可证，使用和再分发权限请先向作者确认。
