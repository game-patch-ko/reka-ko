# Copy the built patch into the game (keeping the original once in work/backup) and start it windowed.
param([switch]$NoDeploy)
$game='F:\SteamLibrary\steamapps\common\Reka'
$root='C:\work\game-patch\reka-ko'
$rel='Reka_Data\resources.assets'
if(-not $NoDeploy){
  $bak="$root\work\backup\$rel"
  if(-not (Test-Path $bak)){New-Item -ItemType Directory -Force (Split-Path $bak)|Out-Null;Copy-Item "$game\$rel" $bak}
  Copy-Item "$root\work\out\$rel" "$game\$rel" -Force
}
$env:SteamAppId='1737870';$env:SteamGameId='1737870'
Start-Process "$game\Reka.exe" -ArgumentList '-screen-fullscreen','0','-screen-width','1600','-screen-height','900' -WorkingDirectory $game
