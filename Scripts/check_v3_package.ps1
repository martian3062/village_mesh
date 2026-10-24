$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Package=Join-Path $Root 'Saved/Packages/V3/Windows'
$Binary=Join-Path $Package 'rural_pardeep/Binaries/Win64/rural_pardeep.exe'
$Log=Join-Path $Root 'Saved/Logs/V3PackagedCheck.log'
$Args=@('-VillageV25','-VillageV3','-V3Check','-V25NoSave','-RenderOffscreen','-unattended','-nosound','-ResX=1440','-ResY=900','-ForceRes','"-ExecCmds=sg.ViewDistanceQuality 3,sg.ShadowQuality 3,sg.GlobalIlluminationQuality 3,sg.ReflectionQuality 3,r.ScreenPercentage 67,t.MaxFPS 60"',"`"-abslog=$Log`"")
$Started=[DateTime]::UtcNow
if(-not('V3TestPower' -as [type])){Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public static class V3TestPower { [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags); }'}
[void][V3TestPower]::SetThreadExecutionState([uint32]2147483649)
try {
    $Process=Start-Process -FilePath $Binary -ArgumentList $Args -WindowStyle Hidden -PassThru
    while(-not $Process.HasExited){
        if(([DateTime]::UtcNow-$Started).TotalSeconds -gt 480){Stop-Process -Id $Process.Id;throw 'V3 check timed out'}
        Start-Sleep -Seconds 5;$Process.Refresh()
    }
    $Process.WaitForExit()
}finally{[void][V3TestPower]::SetThreadExecutionState([uint32]2147483648)}
if($Process.ExitCode -ne 0){throw "V3 check failed: $($Process.ExitCode)"}
$Evidence=Join-Path $Package 'rural_pardeep/Saved/VillageMeshV3'
$Report=Get-Item -LiteralPath (Join-Path $Evidence 'runtime_check.json')
if($Report.LastWriteTimeUtc -lt $Started){throw 'Stale V3 runtime report'}
$Result=Get-Content $Report.FullName -Raw|ConvertFrom-Json
if(-not $Result.passed -or $Result.elapsed_seconds -lt 168 -or $Result.elapsed_seconds -gt 194){throw 'Runtime failed or continuity was interrupted'}
$Dest=Join-Path $Root 'Docs/V3'
Copy-Item -LiteralPath $Report.FullName -Destination (Join-Path $Dest 'runtime_packaged.json')
foreach($I in 0..11){
    $Image=Get-Item -LiteralPath (Join-Path $Evidence ('view_{0:00}.png' -f $I))
    if($Image.LastWriteTimeUtc -lt $Started){throw 'Stale V3 screenshot'}
    Copy-Item -LiteralPath $Image.FullName -Destination $Dest
}
[ordered]@{exe_sha256=(Get-FileHash $Binary).Hash.ToLowerInvariant();started_at_utc=$Started.ToString('o');finished_at_utc=[DateTime]::UtcNow.ToString('o');rendering='D3D12 1440x900 67% render scale, 60 FPS cap';scope='Standalone Development on this workstation; other applications open'}|ConvertTo-Json|Set-Content (Join-Path $Dest 'runtime_build.json') -Encoding UTF8
Write-Output 'V3 standalone atlas, nine public sites, residential lane, animals and grounded-player check passed.'
