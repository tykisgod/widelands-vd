<#
.SYNOPSIS
    以中文启动 Widelands，等窗口出现后抓屏，然后关闭游戏。

.DESCRIPTION
    用于验收字体缺字与按钮文本溢出——这两类问题静态校验覆盖不到。

    Widelands 走 OpenGL 渲染，PrintWindow 抓出来往往是全黑，因此这里把窗口
    置于前台后用 CopyFromScreen 按窗口矩形抓取屏幕。

.EXAMPLE
    .\i18n-zh\screenshot.ps1 -Out shot.png -WaitSeconds 25
#>
[CmdletBinding()]
param(
    [string]$Out = 'zh-main-menu.png',
    [int]$WaitSeconds = 25,
    # 抓屏前依次点击的位置，相对窗口客户区，格式 "x,y"。用于打开子界面。
    [string[]]$Click = @(),
    [string]$Lang = 'zh_CN',
    [int]$Width = 1280,
    [int]$Height = 800,
    [string]$Exe = 'E:\dpp_new\widelands-run\widelands.exe',
    [string]$Repo = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int x, int y, int d, int e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int t, bool repaint);
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT { public int Left, Top, Right, Bottom; }
}
'@

# 高 DPI 屏幕上，若本进程不声明 DPI 感知，GetWindowRect 返回逻辑像素而
# CopyFromScreen 按物理像素取图，抓出来的画面会被裁掉一块。
[Win]::SetProcessDPIAware() | Out-Null

$homeDir = Join-Path $env:TEMP 'widelands-zh-shot'
if (Test-Path $homeDir) { Remove-Item -Recurse -Force $homeDir }
New-Item -ItemType Directory -Force -Path $homeDir | Out-Null

$wlArgs = @(
    "--datadir=$Repo\data"
    '--skip_check_datadir_version'
    "--homedir=$homeDir"
    "--language=$Lang"
    "--xres=$Width"
    "--yres=$Height"
    '--nosound'
)

Write-Host "启动游戏（$Lang）…"
$proc = Start-Process -FilePath $Exe -ArgumentList $wlArgs -PassThru

try {
    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    $hwnd = [IntPtr]::Zero
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 700
        $proc.Refresh()
        if ($proc.HasExited) { throw "游戏已退出，退出码 $($proc.ExitCode)。日志：$homeDir\stdout.txt" }
        if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
            $hwnd = $proc.MainWindowHandle
            break
        }
    }
    if ($hwnd -eq [IntPtr]::Zero) { throw '等待窗口超时' }

    # 主菜单需要一点时间把字体和贴图都加载完
    Start-Sleep -Seconds 6

    [Win]::ShowWindow($hwnd, 9) | Out-Null      # SW_RESTORE

    # 窗口可能开在屏幕外，挪到原点，否则 CopyFromScreen 会抓到桌面背景。
    # 只移动、不改尺寸——改尺寸不会同步更新 OpenGL 视口，画面会被裁掉。
    $r0 = New-Object Win+RECT
    [Win]::GetWindowRect($hwnd, [ref]$r0) | Out-Null
    [Win]::MoveWindow($hwnd, 0, 0, ($r0.Right - $r0.Left), ($r0.Bottom - $r0.Top), $true) | Out-Null
    [Win]::SetForegroundWindow($hwnd) | Out-Null
    Start-Sleep -Seconds 3

    # Windows 会阻止后台进程抢占前台。若置顶失败就直接报错——否则
    # CopyFromScreen 会抓到桌面上无关的窗口内容。
    for ($try = 0; $try -lt 5 -and [Win]::GetForegroundWindow() -ne $hwnd; $try++) {
        [Win]::SetForegroundWindow($hwnd) | Out-Null
        Start-Sleep -Milliseconds 600
    }
    if ([Win]::GetForegroundWindow() -ne $hwnd) {
        throw '无法把游戏窗口置于前台，已放弃抓屏（避免抓到无关内容）。请手动点一下游戏窗口后重试。'
    }

    $r = New-Object Win+RECT
    [Win]::GetWindowRect($hwnd, [ref]$r) | Out-Null

    foreach ($c in $Click) {
        $xy = $c.Split(',')
        $cx = $r.Left + [int]$xy[0]
        $cy = $r.Top + [int]$xy[1]
        Write-Host "  点击 ($cx, $cy)"
        [Win]::SetCursorPos($cx, $cy) | Out-Null
        Start-Sleep -Milliseconds 400
        [Win]::mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
        Start-Sleep -Milliseconds 80
        [Win]::mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
        Start-Sleep -Seconds 2
    }
    if ($Click.Count -gt 0) {
        Start-Sleep -Seconds 2
        if ([Win]::GetForegroundWindow() -ne $hwnd) {
            throw '点击后游戏窗口失去前台，已放弃抓屏。'
        }
        [Win]::GetWindowRect($hwnd, [ref]$r) | Out-Null
    }
    $w = $r.Right - $r.Left
    $h = $r.Bottom - $r.Top
    if ($w -le 0 -or $h -le 0) { throw "窗口矩形无效：${w}x${h}" }

    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
    $g.Dispose()

    $path = if ([System.IO.Path]::IsPathRooted($Out)) { $Out } else { Join-Path (Get-Location) $Out }
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "已保存 $path（${w}×${h}）"
}
finally {
    if (-not $proc.HasExited) { $proc.Kill(); $proc.WaitForExit(5000) }
}
