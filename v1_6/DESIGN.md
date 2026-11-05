---
name: Codex 定时唤醒 V1.6
colors:
  foreground: '#17243b'
  muted: '#3e5069'
  primary: '#0065d8'
  switch: '#31bd70'
  surface: '#e5edf7'
typography:
  body:
    fontFamily: Microsoft YaHei UI
    fontSize: 19px
  time:
    fontFamily: Segoe UI
    fontSize: 39px
rounded:
  window: 16px
  panel: 28px
spacing:
  window: 30px
---

# V1.6 已确认界面

延续 V1.5 的大字体、柔和渐变和玻璃面板。顶部系统白条合入背景，右上角窗口按钮使用一致的矢量描线。Windows 原生处理拖动、调整大小、最小化与最大化，应用负责绘制顶部。

计划管理位于“每日发送计划”右上角，新增、删除均有文字按钮。四条为一页，超过四条显示页码与前后页；不会为了增加行数缩小字号。零计划时显示说明与新增入口，删除按钮禁用。计划弹窗复用滚轮。

默认窗口900×920，最小790×900；窗口放大时字体、点击区域和开关同步放大，最高1.5倍。记录区保持有限高度。
