# Windows: 安装技能到 Claude / Codex / Agents 目录
# 用法:
#   .\install.ps1
#   .\install.ps1 -Link -Force
#   .\install.ps1 -CodexOnly
param(
  [switch]$Link,
  [switch]$Force,
  [switch]$ClaudeOnly,
  [switch]$CodexOnly,
  [switch]$AgentsOnly
)

$ErrorActionPreference = "Stop"
$Src = $PSScriptRoot
$Name = "dingtalk-weekly-report"
$OldName = "weekly-report"

if (-not (Test-Path (Join-Path $Src "SKILL.md"))) {
  Write-Error "找不到 SKILL.md，请在技能包目录运行本脚本"
}

$DoClaude = $true; $DoCodex = $true; $DoAgents = $true
if ($ClaudeOnly) { $DoCodex = $false; $DoAgents = $false }
if ($CodexOnly)  { $DoClaude = $false; $DoAgents = $false }
if ($AgentsOnly) { $DoClaude = $false; $DoCodex = $false }

function Remove-Old($Path) {
  if (Test-Path $Path) {
    Write-Host "⚠ 移除旧技能名: $Path"
    Remove-Item -Recurse -Force $Path
  }
}

function Install-To($Dest, $Label) {
  $Parent = Split-Path $Dest -Parent
  New-Item -ItemType Directory -Force -Path $Parent | Out-Null

  $SrcFull = (Resolve-Path $Src).Path
  if ((Test-Path $Dest) -and -not (Get-Item $Dest).LinkType) {
    $DestFull = (Resolve-Path $Dest).Path
    if ($DestFull -eq $SrcFull) {
      Write-Host "✅ [$Label] 已在安装位置: $Dest"
      return
    }
  }

  if (Test-Path $Dest) {
    $item = Get-Item $Dest -Force
    if ($item.LinkType) {
      $target = $item.Target
      if ($target -is [array]) { $target = $target[0] }
      if ($Link -and ($target -eq $SrcFull -or $target -eq $Src)) {
        Write-Host "✅ [$Label] 软链已对齐: $Dest"
        return
      }
      if (-not $Force) {
        Write-Error "[$Label] 已存在: $Dest 。加 -Force 覆盖，或 -Link -Force"
      }
      Remove-Item -Force $Dest
    } else {
      if (-not $Force) {
        Write-Error "[$Label] 已存在目录: $Dest 。加 -Force 升级"
      }
      Remove-Item -Recurse -Force $Dest
    }
  }

  if ($Link) {
    New-Item -ItemType SymbolicLink -Path $Dest -Target $SrcFull | Out-Null
    Write-Host "✅ [$Label] 已软链: $Dest -> $SrcFull"
  } else {
    Copy-Item -Recurse $Src $Dest
    Write-Host "✅ [$Label] 已安装: $Dest"
  }
}

if ($DoClaude) {
  Remove-Old (Join-Path $env:USERPROFILE ".claude\skills\$OldName")
  Install-To (Join-Path $env:USERPROFILE ".claude\skills\$Name") "Claude"
}

if ($DoCodex) {
  $CodexHome = Join-Path $env:USERPROFILE ".codex"
  if ((Test-Path $CodexHome) -or $CodexOnly) {
    New-Item -ItemType Directory -Force -Path (Join-Path $CodexHome "skills") | Out-Null
    Remove-Old (Join-Path $CodexHome "skills\$OldName")
    $PromptOld = Join-Path $CodexHome "prompts\$OldName.md"
    $PromptNew = Join-Path $CodexHome "prompts\$Name.md"
    if (Test-Path $PromptOld) { Remove-Item -Force $PromptOld; Write-Host "⚠ 移除旧 Codex prompt: $PromptOld" }
    if (Test-Path $PromptNew) { Remove-Item -Force $PromptNew; Write-Host "⚠ 移除过时 Codex prompt 桥接: $PromptNew" }
    Install-To (Join-Path $CodexHome "skills\$Name") "Codex"
  } else {
    Write-Host "ℹ 未检测到 ~/.codex，跳过 Codex skills"
  }
}

if ($DoAgents) {
  $Agents = Join-Path $env:USERPROFILE ".agents"
  if (Test-Path $Agents) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Agents "skills") | Out-Null
    Remove-Old (Join-Path $Agents "skills\$OldName")
    Install-To (Join-Path $Agents "skills\$Name") "Agents"
  }
}

Write-Host ""
Write-Host "下一步:"
Write-Host "  1) .\bootstrap.ps1"
Write-Host "  2) 编辑 `$WORK\config.json"
Write-Host "  3) 打开 Claude/Codex 运行 /dingtalk-weekly-report"
