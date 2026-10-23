param(
    [ValidateSet('Route','Interactions','Capture','Soak')][string]$Action='Route',
    [ValidateSet('daylight','evening','overcast','rain')][string]$Condition='daylight',
    [ValidateSet('playable','capture')][string]$Quality='playable',
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$RunId='packaged',
    [ValidateRange(1,120)][int]$SoakMinutes=30
)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$PackageRoot=Join-Path $ProjectRoot 'Saved\Packages\V2\Windows'
$Binary=Join-Path $PackageRoot 'rural_pardeep\Binaries\Win64\rural_pardeep.exe'
$EvidenceRoot=Join-Path $ProjectRoot 'Saved\VillageMeshV2'
if (-not (Test-Path -LiteralPath $Binary)) { throw 'Build the V2 Development package first.' }
[void](New-Item -ItemType Directory -Force -Path $EvidenceRoot)
$Graphics=Get-Content -LiteralPath (Join-Path $ProjectRoot 'Config\v2_quality.json') -Raw | ConvertFrom-Json
$Scale=if($Quality -eq 'capture'){$Graphics.capture_screen_percentage}else{$Graphics.playable_screen_percentage}
$Commands=(@($Graphics.cvars)+@("r.ScreenPercentage $Scale"))-join ','
$Log=Join-Path $ProjectRoot "Saved\Logs\VillageV2Packaged_${Action}_${RunId}.log"
$Arguments=@(
    '-windowed','-ResX=1440','-ResY=900','-ForceRes',
    '-RenderOffscreen','-unattended','-nosound',"-VillageV2$Action=$Condition",
    "-VillageRunId=$RunId","-VillageSoakMinutes=$SoakMinutes",
    "`"-ExecCmds=$Commands`"","`"-abslog=$Log`""
)
$Started=Get-Date
$Process=Start-Process -FilePath $Binary -ArgumentList $Arguments -PassThru -WindowStyle Hidden
$Nvidia=Get-Command nvidia-smi -ErrorAction SilentlyContinue
$Samples=[Collections.Generic.List[object]]::new()
while (-not $Process.HasExited) {
    if ($Nvidia) {
        $Gpu=& $Nvidia.Source --query-gpu=memory.used,temperature.gpu,power.draw,utilization.gpu --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -eq 0) {
            $Samples.Add([pscustomobject]@{wall_seconds=[math]::Round(((Get-Date)-$Started).TotalSeconds,2);adapter_csv=$Gpu})
        }
    }
    Start-Sleep -Seconds 10
    $Process.Refresh()
}
$Process.WaitForExit()
$Mode=$Action.ToLowerInvariant()
$ReportName="${Mode}_${Condition}_${RunId}.json"
$ReportPath=Join-Path $PackageRoot "rural_pardeep\Saved\VillageMeshV2\$ReportName"
if (Test-Path -LiteralPath $ReportPath) { Copy-Item -LiteralPath $ReportPath -Destination (Join-Path $EvidenceRoot $ReportName) }
$Record=[ordered]@{
    action=$Action;run_id=$RunId;exit_code=$Process.ExitCode;wall_seconds=((Get-Date)-$Started).TotalSeconds
    binary_sha256=(Get-FileHash -LiteralPath $Binary -Algorithm SHA256).Hash.ToLowerInvariant()
    package_utoc_sha256=(Get-FileHash -LiteralPath (Join-Path $PackageRoot 'rural_pardeep\Content\Paks\rural_pardeep-Windows.utoc') -Algorithm SHA256).Hash.ToLowerInvariant()
    resolution=@(1440,900);render_scale_percent=$Scale;uncapped=$true;cvars=$Commands
    gpu_columns='adapter_memory_MiB, temperature_C, power_W, utilization_percent'
    gpu_scope='Whole adapter including other applications; not process VRAM or separate GPU frame timing.'
    gpu_samples=$Samples
}
$Record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $EvidenceRoot "package_monitor_${Mode}_${RunId}.json") -Encoding UTF8
if ($Process.ExitCode -ne 0) { throw "Packaged $Action failed with exit code $($Process.ExitCode); inspect $Log" }
if (-not (Test-Path -LiteralPath $ReportPath)) { throw "Packaged process exited without its diagnostic report: $ReportPath" }
$Report=Get-Content -LiteralPath $ReportPath -Raw | ConvertFrom-Json
if (-not $Report.passed) { throw "Packaged diagnostic failed: $($Report.reason)" }
if ($Report.editor_build -or $Report.map -ne 'Lvl_PandoriV2_WP') { throw 'The package did not launch its expected V2 default map in a standalone game build.' }
if ($Action -eq 'Capture') {
    foreach ($Index in 1..8) {
        $Name='{0}_{1:00}.png' -f $Condition,$Index
        $Capture=Get-Item -LiteralPath (Join-Path (Split-Path $ReportPath -Parent) $Name)
        if ($Capture.Length -eq 0 -or $Capture.LastWriteTime -lt $Started) { throw "Missing or stale packaged capture: $Name" }
        Copy-Item -LiteralPath $Capture.FullName -Destination (Join-Path $EvidenceRoot "packaged_$Name")
    }
}
Write-Output "Packaged $Action passed: $ReportPath"
