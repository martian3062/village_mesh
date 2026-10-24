param(
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$RunId='packaged',
    [ValidateRange(30,7200)][int]$Seconds=120,
    [switch]$Learned,[switch]$MissingModel,[switch]$Headless,[switch]$Screenshots,
    [ValidateRange(0,120)][int]$MaxFPS=60
)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Package=Join-Path $Root 'Saved/Packages/V25/Windows'
$Binary=Join-Path $Package 'rural_pardeep/Binaries/Win64/rural_pardeep.exe'
if(-not(Test-Path -LiteralPath $Binary)){throw 'Build the V2.5 package first'}
$Quality=Get-Content (Join-Path $Root 'Config/v2_quality.json') -Raw|ConvertFrom-Json
$Commands=(@($Quality.cvars)+@('r.ScreenPercentage 67',"t.MaxFPS $MaxFPS"))-join ','
$Log=Join-Path $Root "Saved/Logs/V25Packaged_$RunId.log"
$Args=@('-VillageV25','-V25Check',"-V25Run=$RunId","-V25Seconds=$Seconds",'-unattended','-nosound','-ResX=1440','-ResY=900','-ForceRes',"`"-ExecCmds=$Commands`"","`"-abslog=$Log`"")
if($Learned){$Args+='-V25Learned'}
if($MissingModel){$Args+='-V25MissingModel'}
if($Screenshots){$Args+='-V25Screenshots'}
if($Headless){$Args+='-NullRHI'}else{$Args+='-RenderOffscreen'}
$Started=[DateTime]::UtcNow
if(-not('V25TestPower' -as [type])){Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public static class V25TestPower { [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags); }'}
# Keep the system awake only while this check runs; leave the display policy alone.
[void][V25TestPower]::SetThreadExecutionState([uint32]2147483649)
try{
$Process=Start-Process -FilePath $Binary -ArgumentList $Args -WindowStyle Hidden -PassThru
$Samples=[Collections.Generic.List[object]]::new()
$Nvidia=Get-Command nvidia-smi -ErrorAction SilentlyContinue
while(-not $Process.HasExited){
    if(([DateTime]::UtcNow-$Started).TotalSeconds -gt $Seconds+300){Stop-Process -Id $Process.Id;throw "V2.5 check exceeded its duration plus 300-second startup allowance: $RunId"}
    if($Nvidia){$Value=& $Nvidia.Source --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits 2>$null;if($LASTEXITCODE -eq 0){$Samples.Add([pscustomobject]@{seconds=([DateTime]::UtcNow-$Started).TotalSeconds;adapter_mib_temperature_c=$Value})}}
    Start-Sleep -Seconds 10;$Process.Refresh()
}
$Process.WaitForExit()
}finally{[void][V25TestPower]::SetThreadExecutionState([uint32]2147483648)}
$Report=Join-Path $Package "rural_pardeep/Saved/VillageMeshV25/runtime_$RunId.json"
if($Process.ExitCode -ne 0){throw "V2.5 check failed with exit $($Process.ExitCode); inspect $Log"}
$Item=Get-Item -LiteralPath $Report
if($Item.LastWriteTimeUtc -lt $Started){throw 'Stale check report'}
$Result=Get-Content $Report -Raw|ConvertFrom-Json
if(-not $Result.passed -or $Result.editor_build){throw 'Standalone check did not pass'}
if($Result.wall_seconds -lt $Seconds -or $Result.wall_seconds -gt $Seconds+10 -or $Result.max_frame_ms -gt 60000){throw 'Run was interrupted or suspended; it is not continuous-session evidence'}
$Evidence=Join-Path $Root 'Saved/VillageMeshV25';[void](New-Item -ItemType Directory -Force -Path $Evidence)
Copy-Item -LiteralPath $Report -Destination $Evidence
if($Screenshots){foreach($Name in @('dialogue.png','farms_rain.png')){
    $Image=Get-Item -LiteralPath (Join-Path (Split-Path $Report -Parent) $Name)
    if($Image.LastWriteTimeUtc -lt $Started){throw "Stale screenshot: $Name"}
    Copy-Item -LiteralPath $Image.FullName -Destination $Evidence
}}
[ordered]@{run_id=$RunId;exe_sha256=(Get-FileHash $Binary).Hash.ToLowerInvariant();fps_cap=$MaxFPS;cvars=$Commands;gpu_scope='whole adapter, includes other applications';samples=$Samples}|ConvertTo-Json -Depth 6|Set-Content (Join-Path $Evidence "monitor_$RunId.json") -Encoding UTF8
Write-Output "V2.5 packaged check passed: $RunId"
