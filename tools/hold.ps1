# Hold a key in the running game: hold.ps1 -key 0x57 -ms 1500 (scan-code based, so raw input sees it)
param([int]$key=0x57,[int]$ms=1000)
Add-Type @"
using System;using System.Runtime.InteropServices;
public class K{[DllImport("user32.dll")]public static extern void keybd_event(byte v,byte s,int f,int e);[DllImport("user32.dll")]public static extern uint MapVirtualKey(uint c,uint t);
[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);}
"@
$p=Get-Process Reka|Where-Object {$_.MainWindowHandle -ne 0}|Select-Object -First 1
[K]::SetForegroundWindow($p.MainWindowHandle)|Out-Null;Start-Sleep -Milliseconds 200
$s=[byte][K]::MapVirtualKey($key,0)
[K]::keybd_event($key,$s,0,0);Start-Sleep -Milliseconds $ms;[K]::keybd_event($key,$s,2,0)
