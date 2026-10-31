$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path -LiteralPath '.\dist\Codex定时唤醒_v1_3.exe') { throw 'EXE 已存在，请在新版本中构建，不能覆盖。' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Codex定时唤醒_v1_3 --icon clock_v1_3.ico --version-file version_v1_3.txt --distpath dist --workpath build codex_alarm_v1_3.py
if ($LASTEXITCODE -ne 0) { throw '打包失败' }
