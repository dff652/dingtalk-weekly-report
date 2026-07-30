# SPDX-License-Identifier: Apache-2.0
# 首次建 $WORK 运行环境（Windows PowerShell）
# 用法:
#   .\bootstrap.ps1
#   .\bootstrap.ps1 -Work "$env:USERPROFILE\weekly-report-data"
#   .\bootstrap.ps1 -ForceVenv
#   .\bootstrap.ps1 -Diagnose
param(
  [string]$Work = "",
  [switch]$ForceVenv,
  [switch]$Diagnose
)

$ErrorActionPreference = "Stop"
$Skill = $PSScriptRoot
$DtwrDir = Join-Path $env:USERPROFILE ".config\dtwr"
$RootFile = Join-Path $DtwrDir "root"
if (-not $Work) {
  if ($env:DTWR_HOME) {
    $Work = $env:DTWR_HOME
  } elseif (Test-Path $RootFile) {
    $Work = (Get-Content -Raw $RootFile).Trim()
  } else {
    $Work = Join-Path $env:USERPROFILE "weekly-report-data"
  }
}
$Work = [System.IO.Path]::GetFullPath($Work)
$SkillPrefix = $Skill.TrimEnd('\') + '\'
$WorkPrefix = $Work.TrimEnd('\') + '\'
if ($WorkPrefix.StartsWith($SkillPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
    $SkillPrefix.StartsWith($WorkPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
  Write-Error "`$WORK 必须与技能/源码目录分离: $Work"
}

if ($Diagnose -and -not (Test-Path $Work)) {
  Write-Error "工作目录不存在: $Work（首次安装请运行 bootstrap.ps1）"
}
New-Item -ItemType Directory -Force -Path (Join-Path $Work "output") | Out-Null
$LogFile = Join-Path $Work "output\bootstrap.log"
$Started = [System.Diagnostics.Stopwatch]::StartNew()
$CurrentStage = "启动"
$Completed = $false
Start-Transcript -Path $LogFile -Append -Force | Out-Null

function Set-Stage([string]$Name) {
  $script:CurrentStage = $Name
  Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ==> $Name"
}

try {
  Write-Host ""
  Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] bootstrap_start diagnose=$Diagnose force_venv=$ForceVenv"
  Write-Host "==> `$WORK = $Work"
  Write-Host "==> `$SKILL = $Skill"
  Write-Host "==> 日志 = $LogFile"

  $VenvDir = Join-Path $Work ".venv"
  $Py = Join-Path $VenvDir "Scripts\python.exe"
  $RuntimeCheck = Join-Path $Skill "scripts\runtime_check.py"
  $Requirements = Join-Path $Skill "requirements-runtime.txt"

  if ($Diagnose) {
    Set-Stage "检查现有运行环境（不安装）"
    if (-not (Test-Path $Py)) {
      Write-Error "找不到 venv python: $VenvDir。修复请运行 bootstrap.ps1"
    }
    & $Py $RuntimeCheck $Requirements
    if ($LASTEXITCODE -ne 0) {
      Write-Error "运行环境体检失败；修复请运行 bootstrap.ps1"
    }
    Write-Host "✅ 环境可复用；更新 Skill 不需要重装或重跑 bootstrap"
    $Completed = $true
    return
  }

  New-Item -ItemType Directory -Force -Path (Join-Path $Work "weeks") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $Work "output\shots") | Out-Null

  Set-Stage "检查私有配置"
  $Config = Join-Path $Work "config.json"
  $Example = Join-Path $Skill "assets\config.example.json"
  if (-not (Test-Path $Config)) {
    Copy-Item $Example $Config
    Write-Host "✅ 已写入 $Config（AI 首次调用会主动引导；本机可运行 --guided）"
  } else {
    Write-Host "ℹ 保留已有 config.json"
  }

  if ($ForceVenv -and (Test-Path $VenvDir)) {
    Write-Host "⚠ -ForceVenv: 删除 $VenvDir"
    Remove-Item -Recurse -Force $VenvDir
  }

  Set-Stage "检查 Python 与浏览器运行环境"
  $RuntimeReady = $false
  if (-not $ForceVenv -and (Test-Path $Py)) {
    & $Py $RuntimeCheck $Requirements
    $RuntimeReady = ($LASTEXITCODE -eq 0)
  }
  if ($RuntimeReady) {
    Write-Host "✅ 复用现有 .venv 与 Chromium；Skill 更新不会重复安装环境"
  } else {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
      Write-Error "运行环境需要创建/修复，但未找到 uv。请看 https://docs.astral.sh/uv/getting-started/installation/"
    }
    if (-not (Test-Path $Py)) {
      Set-Stage "创建 Python venv"
      Push-Location $Work
      try {
        uv venv .venv
        if ($LASTEXITCODE -ne 0) { Write-Error "uv venv 失败" }
      } finally {
        Pop-Location
      }
    }
    if (-not (Test-Path $Py)) {
      Write-Error "找不到 venv python: $Py"
    }

    Set-Stage "同步 Python 运行依赖"
    uv pip install --python $Py -r $Requirements
    if ($LASTEXITCODE -ne 0) { Write-Error "Python 依赖安装失败" }
    Set-Stage "校验/补齐 Chromium（缓存命中时不会重复下载）"
    & $Py -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { Write-Error "Chromium 安装失败" }
    Set-Stage "复验修复后的运行环境"
    & $Py $RuntimeCheck $Requirements
    if ($LASTEXITCODE -ne 0) { Write-Error "修复后运行环境仍未通过" }
  }

  Set-Stage "写入工作目录指针"
  New-Item -ItemType Directory -Force -Path $DtwrDir | Out-Null
  Set-Content -Path $RootFile -Value $Work -NoNewline -Encoding utf8
  Write-Host "✅ 已写 $RootFile → $Work"

  Write-Host ""
  Write-Host "bootstrap 完成。"
  Write-Host "  更新 Skill: 不要重跑 bootstrap；先用 -Diagnose 检查"
  Write-Host "  排查日志: $LogFile"
  Write-Host "  查看日志: Get-Content -Tail 80 `"$LogFile`""
  Write-Host "  缺项:   & `"$Py`" `"$Skill\scripts\configure.py`" --missing"
  Write-Host "  配置:   & `"$Py`" `"$Skill\scripts\configure.py`" --guided"
  Write-Host "  登录:   & `"$Py`" `"$Skill\scripts\fill_form.py`" --login-web  # 127.0.0.1；远程使用端口转发"
  Write-Host "  截图兜底: & `"$Py`" `"$Skill\scripts\fill_form.py`" --login"
  Write-Host "  URL兜底: 用户本人在交互终端运行 fill_form.py --login-url（隐藏输入）"
  Write-Host "  AI: Claude 用 /dingtalk-weekly-report；Codex 用 `$dingtalk-weekly-report 或从 /skills 选择"
  Write-Host "  可选: Windows 计划任务每日运行 fill_form.py --keepalive"
  $Completed = $true
} finally {
  $Started.Stop()
  if ($Completed) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] bootstrap_result=PASS elapsed=$([math]::Round($Started.Elapsed.TotalSeconds, 2))s log=$LogFile"
  } else {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] bootstrap_result=FAIL stage=$CurrentStage elapsed=$([math]::Round($Started.Elapsed.TotalSeconds, 2))s"
    Write-Host "排查日志: $LogFile"
  }
  Stop-Transcript | Out-Null
}
