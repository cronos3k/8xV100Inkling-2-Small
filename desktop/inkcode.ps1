# OpenCode on this PC, connected to Inkling-2-Small on the V100 box.
#   inkcode                     interface in the current directory
#   inkcode  <project dir>      interface in that directory
#   inkcode  run "task"         one task without the interface
#   inkcode  -stop              close the tunnel to the box
# Everything (program, config, sessions, cache) lives in this folder; the global OpenCode is not touched.
$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$box    = if ($env:V100_HOST) { $env:V100_HOST } else { 'user@v100-box' }
$remote = 18142
if ($env:INK_LLM_PORT) { $remote = [int]$env:INK_LLM_PORT } else {
  try { $r = (& ssh -o BatchMode=yes -o ConnectTimeout=8 $box 'cat /srv/archive-a/volta-ink2/run/engine.port' 2>$null); if ($r -match '^\d+$') { $remote = [int]$r } } catch {}
}
$run    = Join-Path $root 'run'
$pidFile  = Join-Path $run 'ink-tunnel.pid'
$portFile = Join-Path $run 'ink-tunnel.port'
New-Item -ItemType Directory -Force $run | Out-Null

function Tunnel-Pid {
  if (-not (Test-Path $pidFile)) { return $null }
  $p = [int](Get-Content $pidFile)
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$p" -ErrorAction SilentlyContinue
  # only our own tunnel counts: an ssh process whose command line carries our forward
  if ($proc -and $proc.Name -eq 'ssh.exe' -and $proc.CommandLine -like "*:127.0.0.1:$remote*") { return $p }
  return $null
}
function Port-Free([int]$port) {
  try { $l = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $port); $l.Start(); $l.Stop(); return $true } catch { return $false }
}
function Llm-Answers([int]$port) {
  try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$port/v1/models").Content -like '*inkling-2-small*' } catch { $false }
}

if ($args.Count -ge 1 -and $args[0] -eq '-stop') {
  $p = Tunnel-Pid
  if ($p) { Stop-Process -Id $p -Force; Write-Host "tunnel closed (pid $p)" } else { Write-Host 'no tunnel running' }
  Remove-Item $pidFile, $portFile -ErrorAction SilentlyContinue
  exit 0
}

$port = $null
if ((Tunnel-Pid) -and (Test-Path $portFile)) { $port = [int](Get-Content $portFile) }
if (-not $port -or -not (Llm-Answers $port)) {
  $old = Tunnel-Pid; if ($old) { Stop-Process -Id $old -Force }
  $port = $null
  foreach ($c in 48062..48081) { if (Port-Free $c) { $port = $c; break } }
  if (-not $port) { Write-Host 'no free local port in 48062-48081'; exit 1 }
  $ssh = Start-Process ssh -WindowStyle Hidden -PassThru -ArgumentList @(
    '-N', '-o', 'BatchMode=yes', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30',
    '-L', "127.0.0.1:${port}:127.0.0.1:${remote}", $box)
  Set-Content $pidFile $ssh.Id; Set-Content $portFile $port
  $ok = $false
  foreach ($i in 1..20) { Start-Sleep -Milliseconds 500; if ($ssh.HasExited) { break }; if (Llm-Answers $port) { $ok = $true; break } }
  if (-not $ok) {
    if (-not $ssh.HasExited) { Stop-Process -Id $ssh.Id -Force }
    Remove-Item $pidFile, $portFile -ErrorAction SilentlyContinue
    Write-Host "Inkling-2-Small on $box does not answer on port $remote."
    Write-Host "Start it with the launcher V100 Inkling - 5, or: ssh $box /srv/archive-a/volta-ink2/coder/ink-start.sh"
    exit 1
  }
}

$cfg = Join-Path $run 'ink.opencode.json'
$json = (Get-Content (Join-Path $root 'opencode.inkling.template.json') -Raw).Replace('__PORT__', "$port")
[IO.File]::WriteAllText($cfg, $json, (New-Object Text.UTF8Encoding($false)))

$env:OPENCODE_CONFIG = $cfg
$env:OPENCODE_CONFIG_CONTENT = $json   # inline config has the highest priority: a project opencode.json (F:opencode.json exists) cannot redirect the model
$env:OPENCODE_DISABLE_AUTOUPDATE = '1'
$env:XDG_CONFIG_HOME = Join-Path $root 'config'
$env:XDG_DATA_HOME   = Join-Path $root 'data'
$env:XDG_STATE_HOME  = Join-Path $root 'state'
$env:XDG_CACHE_HOME  = Join-Path $root 'cache'
& (Join-Path $root 'app\node_modules\opencode-ai\bin\opencode.exe') @args
exit $LASTEXITCODE
