<#
.SYNOPSIS
    简体中文译文端到端加载验证（无需编译）。

.DESCRIPTION
    用官方 daily 构建的 widelands.exe 加载本仓库的 data/ 目录，跑 verify_zh.lua，
    确认 .po 译文经 tinygettext 真实加载并返回中文。退出码 0 表示通过。

    判定方式与上游的 regression_test.py 一致：**盯 stdout.txt，不等进程退出**。
    verify_zh.lua 末尾的 wl.ui.MapView():close() 只是关掉地图视图回到主菜单，
    游戏进程会停在那儿等输入，永远不会自己退出。上游的回归测试同样是靠在
    日志里找 "All Tests passed." 然后杀进程来判定的。

    三个必需参数的由来：
      --skip_check_datadir_version  源码 checkout 没有构建时生成的 data/datadirversion
      --datadir_for_testing         测试地图 plain.wmf 的自定义部族资源按仓库根解析
      --homedir                     隔离配置与存档，避免污染真实游戏目录

.EXAMPLE
    .\i18n-zh\run-verify.ps1
    .\i18n-zh\run-verify.ps1 -Exe D:\somewhere\widelands.exe
#>
[CmdletBinding()]
param(
    [string]$Exe = 'E:\dpp_new\widelands-run\widelands.exe',
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [string]$HomeDir = (Join-Path $env:TEMP 'widelands-zh-verify'),
    [int]$TimeoutSec = 180
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Exe)) {
    Write-Error "找不到 widelands.exe：$Exe`n从 https://github.com/widelands/widelands/releases/tag/latest 下载 Widelands-daily-mingw-Release-x64.zip"
}

# 版本必须与工作区 HEAD 匹配，否则 msgid 可能对不上
$head = (& git -C $Repo rev-parse --short HEAD).Trim()
Write-Host "工作区 HEAD: $head"

if (Test-Path $HomeDir) { Remove-Item -Recurse -Force $HomeDir }
New-Item -ItemType Directory -Force -Path $HomeDir | Out-Null
$log = Join-Path $HomeDir 'stdout.txt'

$gameArgs = @(
    "--datadir=$Repo\data"
    '--skip_check_datadir_version'
    "--datadir_for_testing=$Repo"
    "--homedir=$HomeDir"
    "--scenario=$Repo\test\maps\plain.wmf"
    "--script=$Repo\i18n-zh\verify_zh.lua"
    '--language=zh_CN'
    '--nosound'
    '--fail-on-lua-error'
    '--fail-on-errors'
)

$proc = Start-Process -FilePath $Exe -ArgumentList $gameArgs -PassThru

$verdict = $null
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
    if (Test-Path $log) {
        $text = Get-Content $log -Raw -Encoding utf8 -ErrorAction SilentlyContinue
        if ($text -match '# All Tests passed\.') { $verdict = 'pass'; break }
        if ($text -match 'LUA:\s+FAIL|译文加载验证失败') { $verdict = 'fail'; break }
    }
    if ($proc.HasExited) { $verdict = 'exited'; break }
    Start-Sleep -Milliseconds 500
}

# 游戏跑完脚本后会停在主菜单，必须主动收掉
if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }

if (Test-Path $log) {
    Select-String -Path $log -Pattern 'LUA: ' -Encoding utf8 |
        ForEach-Object { $_.Line -replace '^.*LUA: ', '' }
}

Write-Host ''
switch ($verdict) {
    'pass' { Write-Host '验证通过。' -ForegroundColor Green; exit 0 }
    'fail' { Write-Host "验证失败。完整日志：$log" -ForegroundColor Red; exit 1 }
    'exited' {
        Write-Host "游戏在跑完验证脚本前就退出了（退出码 $($proc.ExitCode)）。完整日志：$log" -ForegroundColor Red
        exit 1
    }
    default {
        Write-Host "等待 $TimeoutSec 秒仍未见结论，已强制结束。完整日志：$log" -ForegroundColor Red
        exit 1
    }
}
