param(
    [ValidateSet('daylight','rain')][string]$Condition='daylight',
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$RunId='v25_route1'
)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Package=Join-Path $Root 'Saved/Packages/V25/Windows'
$Binary=Join-Path $Package 'rural_pardeep/Binaries/Win64/rural_pardeep.exe'
$Graphics=Get-Content (Join-Path $Root 'Config/v2_quality.json') -Raw|ConvertFrom-Json
$Commands=(@($Graphics.cvars)+@('r.ScreenPercentage 67','t.MaxFPS 60'))-join ','
$Log=Join-Path $Root "Saved/Logs/V25Route_$RunId.log"
$Arguments=@('-VillageV25','-V25NoSave',"-VillageV2Route=$Condition","-VillageRunId=$RunId",'-RenderOffscreen','-unattended','-nosound','-ResX=1440','-ResY=900','-ForceRes',"`"-ExecCmds=$Commands`"","`"-abslog=$Log`"")
$Started=[DateTime]::UtcNow
if(-not('V25TestPower' -as [type])){Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public static class V25TestPower { [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags); }'}
[void][V25TestPower]::SetThreadExecutionState([uint32]2147483649)
try{
$Process=Start-Process -FilePath $Binary -ArgumentList $Arguments -WindowStyle Hidden -PassThru
if(-not $Process.WaitForExit(600000)){Stop-Process -Id $Process.Id;throw "V2.5 traversal exceeded 10 minutes: $RunId"}
}finally{[void][V25TestPower]::SetThreadExecutionState([uint32]2147483648)}
if($Process.ExitCode -ne 0){throw "V2.5 traversal failed: $RunId"}
$File=Get-Item (Join-Path $Package "rural_pardeep/Saved/VillageMeshV2/route_${Condition}_$RunId.json")
if($File.LastWriteTimeUtc -lt $Started){throw 'Stale traversal evidence'}
$Report=Get-Content $File.FullName -Raw|ConvertFrom-Json
if(-not $Report.passed -or $Report.editor_build -or -not $Report.rendered){throw 'Standalone traversal did not pass'}
if($Report.wall_seconds -gt 300 -or $Report.max_frame_ms -gt 60000){throw 'Traversal was interrupted or suspended'}
if(-not(Select-String -LiteralPath $Log -SimpleMatch 'V25_START residents=8 plots=4 policy=ORT CPU ready' -Quiet)){throw 'The traversal did not run the V2.5 simulation and CPU model'}
$Target=Join-Path $Root 'Saved/VillageMeshV25';[void](New-Item -ItemType Directory -Force -Path $Target)
Copy-Item -LiteralPath $File.FullName -Destination $Target
[ordered]@{run_id=$RunId;exe_sha256=(Get-FileHash $Binary).Hash.ToLowerInvariant();fps_cap=60;cvars=$Commands;condition=$Condition}|ConvertTo-Json|Set-Content (Join-Path $Target "monitor_route_$RunId.json") -Encoding UTF8
Write-Output "V2.5 traversal passed: $RunId"
