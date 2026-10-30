# Codex 定时唤醒
<!-- impeccable:product-schema 1 -->

## Platform
adaptive

## Stack
Windows 原生桌面 EXE；实现技术由开发选择，使用 Python 标准库与 Tk，免安装运行。

## Users
Jack，Windows 上的 Codex 桌面用户。

## Product Purpose
按用户指定的时间，在专用“定时唤醒”聊天向 GPT-6.1 发送用户自定义消息。

## Capabilities and Constraints
每天重复，默认 05:00；支持编辑消息、开启及暂停、发送记录。保持电脑开机并登录 Codex。首版交付用户实际试发，开发期间不发送真实消息。不承诺控制额度重置。新增 V1 文件，不覆盖既有产物，本地 Git 提交。

## Brand Commitments
中文、苹果风格、手机闹钟式滚轮时间选择；最小化、最大化、关闭在右上角。

## Operating Context
使用本机 Codex 官方 app-server 协议及同一用户会话目录，不自动切换账号或服务。启动时默认暂停，用户明确开启后才定时发送。
