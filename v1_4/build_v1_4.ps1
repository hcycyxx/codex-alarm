$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path -LiteralPath '.\dist\Codex定时唤醒_v1_4.exe') { throw 'EXE 已存在，不能覆盖。请使用新版本。' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Codex定时唤醒_v1_4 --icon clock_v1_4.ico --version-file version_v1_4.txt --distpath dist --workpath build codex_alarm_v1_4.py
if ($LASTEXITCODE -ne 0) { throw '打包失败' }
