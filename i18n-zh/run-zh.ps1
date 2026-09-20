<#
.SYNOPSIS
    以简体中文启动 Widelands，直接读取本仓库的译文。

.DESCRIPTION
    改完 .po 后重启游戏即可看到效果，无需编译，也无需把文件拷到别处。

    重要：不要直接双击 widelands-run\widelands.exe。
    daily 构建的 zip 只含可执行文件，不含 data/ 目录；找不到 datadir 时
    Widelands 只记录错误却不退出（src/wlapplication.cc:1739），随后解引用
    空指针崩溃（表现为"0x... 指令引用了 0x...40 内存，该内存不能为 read"）。
    必须通过本脚本启动，由它传入 --datadir。

.PARAMETER Lang
    语言代码，默认 zh_CN。传 en 可对照英文原文。

.PARAMETER Windowed
    窗口模式启动，便于与编辑器并排对照。

.EXAMPLE
    .\i18n-zh\run-zh.ps1
    .\i18n-zh\run-zh.ps1 -Lang en          # 对照英文
    .\i18n-zh\run-zh.ps1 -Windowed
#>
[CmdletBinding()]
param(
    [string]$Lang = 'zh_CN',
    [string]$Exe = 'E:\dpp_new\widelands-run\widelands.exe',
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [switch]$Windowed
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Exe)) {
    Write-Error @"
找不到 widelands.exe：$Exe

下载官方 daily 构建（约 30 MB）：
  gh release download latest --repo widelands/widelands ``
     --pattern 'Widelands-daily-mingw-Release-x64.zip'
解压后把 widelands.exe 放到上述路径，或用 -Exe 指定实际位置。
"@
}

$dataDir = Join-Path $Repo 'data'
if (-not (Test-Path (Join-Path $dataDir 'i18n\translations'))) {
    Write-Error "仓库数据目录不完整：$dataDir"
}

# 二进制与工作区 HEAD 不一致时 msgid 可能对不上，先提示
$head = (& git -C $Repo rev-parse --short HEAD).Trim()
Write-Host "工作区 HEAD : $head"
Write-Host "语言        : $Lang"
Write-Host "数据目录    : $dataDir"
Write-Host ''

$wlArgs = @(
    "--datadir=$dataDir"
    '--skip_check_datadir_version'   # 源码 checkout 无构建期生成的 data/datadirversion
    "--language=$Lang"
)
if ($Windowed) { $wlArgs += '--fullscreen=false' }

& $Exe @wlArgs
exit $LASTEXITCODE
