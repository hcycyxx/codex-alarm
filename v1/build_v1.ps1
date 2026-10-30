$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path -LiteralPath '.\dist\Codex定时唤醒_v1.exe') { throw 'V1 EXE 已存在。请在新版本目录构建，不能覆盖。' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Codex定时唤醒_v1 --icon clock_v1.ico --version-file version_v1.txt --distpath dist --workpath build codex_alarm_v1.py
if ($LASTEXITCODE -ne 0) { throw '打包失败' }
