param([string]$out="C:\work\game-patch\reka-ko\work\shot.png",[int]$x=-1,[int]$y=-1,[string]$keys="",[int]$wait=0)
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @"
using System;using System.Runtime.InteropServices;
public class W{[DllImport("user32.dll")]public static extern bool SetProcessDPIAware();[DllImport("user32.dll")]public static extern bool SetCursorPos(int x,int y);[DllImport("user32.dll")]public static extern void mouse_event(int f,int dx,int dy,int d,int e);
[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")]public static extern bool GetClientRect(IntPtr h,out RECT r);[DllImport("user32.dll")]public static extern bool ClientToScreen(IntPtr h,ref POINT p);
public struct RECT{public int L,T,R,B;}public struct POINT{public int X,Y;}}
"@
[W]::SetProcessDPIAware()|Out-Null
$p=Get-Process Reka -ErrorAction Stop|Where-Object {$_.MainWindowHandle -ne 0}|Select-Object -First 1;$h=$p.MainWindowHandle
[W]::SetForegroundWindow($h)|Out-Null;Start-Sleep -Milliseconds 300
$r=New-Object W+RECT;[W]::GetClientRect($h,[ref]$r)|Out-Null
$pt=New-Object W+POINT;[W]::ClientToScreen($h,[ref]$pt)|Out-Null
$ox=$pt.X;$oy=$pt.Y;$w=$r.R;$ht=$r.B
if($x -ge 0){[W]::SetCursorPos($ox+$x+3,$oy+$y+3)|Out-Null;Start-Sleep -Milliseconds 500;[W]::SetCursorPos($ox+$x,$oy+$y)|Out-Null;Start-Sleep -Milliseconds 600;[W]::mouse_event(2,0,0,0,0);Start-Sleep -Milliseconds 150;[W]::mouse_event(4,0,0,0,0);Start-Sleep -Milliseconds 900}
if($keys){[Windows.Forms.SendKeys]::SendWait($keys);Start-Sleep -Milliseconds 800}
if($wait){Start-Sleep -Seconds $wait}
$bmp=New-Object Drawing.Bitmap $w,$ht
$g=[Drawing.Graphics]::FromImage($bmp);$g.CopyFromScreen($ox,$oy,0,0,(New-Object Drawing.Size $w,$ht))
$bmp.Save($out)
Write-Output "client $ox,$oy ${w}x${ht}"
