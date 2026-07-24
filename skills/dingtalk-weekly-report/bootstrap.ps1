# 首次建 $WORK 运行环境（Windows PowerShell）
# 用法:
#   .\bootstrap.ps1
#   .\bootstrap.ps1 -Work "$env:USERPROFILE\weekly-report-data"
#   .\bootstrap.ps1 -ForceVenv
param(
  [string]$Work = $(if ($env:DTWR_HOME) { $env:DTWR_HOME } else { Join-Path $env:USERPROFILE "weekly-report-data" }),
  [switch]$ForceVenv
)

$ErrorActionPreference = "Stop"
$Skill = $PSScriptRoot
$Work = [System.IO.Path]::GetFullPath($Work)

Write-Host "==> `$WORK = $Work"
Write-Host "==> `$SKILL = $Skill"

New-Item -ItemType Directory -Force -Path (Join-Path $Work "weeks") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Work "output\shots") | Out-Null

$Config = Join-Path $Work "config.json"
$Example = Join-Path $Skill "assets\config.example.json"
if (-not (Test-Path $Config)) {
  Copy-Item $Example $Config
  Write-Host "✅ 已写入 $Config（请编辑 name / form_project / attach_project 等）"
} else {
  Write-Host "ℹ 保留已有 config.json"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Error "未找到 uv。请先安装: https://docs.astral.sh/uv/getting-started/installation/ （Windows 推荐 irm https://astral.sh/uv/install.ps1 | iex）"
}

$VenvDir = Join-Path $Work ".venv"
if ($ForceVenv -and (Test-Path $VenvDir)) {
  Write-Host "⚠ -ForceVenv: 删除 $VenvDir"
  Remove-Item -Recurse -Force $VenvDir
}

$Py = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $Py)) {
  Write-Host "==> uv venv"
  Push-Location $Work
  try { uv venv .venv } finally { Pop-Location }
}
if (-not (Test-Path $Py)) {
  Write-Error "找不到 venv python: $Py"
}

Write-Host "==> 安装 playwright"
uv pip install --python $Py -r (Join-Path $Skill "requirements-runtime.txt")
Write-Host "==> 安装 Chromium"
& $Py -m playwright install chromium

$DtwrDir = Join-Path $env:USERPROFILE ".config\dtwr"
New-Item -ItemType Directory -Force -Path $DtwrDir | Out-Null
$RootFile = Join-Path $DtwrDir "root"
Set-Content -Path $RootFile -Value $Work -NoNewline -Encoding utf8
Write-Host "✅ 已写 $RootFile → $Work"

Write-Host ""
Write-Host "bootstrap 完成。"
Write-Host "  下一步: 编辑 $Config"
Write-Host "  登录:   & `"$Py`" `"$Skill\scripts\fill_form.py`" --login-url '<h3yun entry/auth 链接>'"
Write-Host "  或打开 AI 工具运行 /dingtalk-weekly-report"
Write-Host "  可选: Windows 计划任务每日运行 fill_form.py --keepalive"
