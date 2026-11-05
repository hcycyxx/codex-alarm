$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path -LiteralPath '.\dist\Codex定时唤醒_v1_6.exe') { throw 'EXE 已存在，不能覆盖。请在新版本目录构建。' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Codex定时唤醒_v1_6 --icon clock_v1_6.ico --version-file version_v1_6.txt --distpath dist --workpath build codex_alarm_v1_6.py
if ($LASTEXITCODE -ne 0) { throw '打包失败' }
