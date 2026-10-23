param([Parameter(Mandatory=$true)][string]$EngineRoot)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$LegacyEvidence=Join-Path $ProjectRoot 'Saved\VillageMeshGenerated'
$Evidence=Join-Path $ProjectRoot 'Saved\VillageMeshV2'
[void](New-Item -ItemType Directory -Force -Path $Evidence)
# The shared V1 smoke runner writes these two files. Preserve their exact bytes.
$Original=@{}
foreach ($Name in @('runtime_smoke.json','overview.png')) {
    $Path=Join-Path $LegacyEvidence $Name
    if(Test-Path -LiteralPath $Path){$Original[$Name]=[IO.File]::ReadAllBytes($Path)}
}
try {
    $Graphics=Get-Content -LiteralPath (Join-Path $ProjectRoot 'Config\v2_quality.json') -Raw | ConvertFrom-Json
    $Commands=(@($Graphics.cvars)+@("r.ScreenPercentage $($Graphics.playable_screen_percentage)"))-join ','
    & "$EngineRoot\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$ProjectRoot\rural_pardeep.uproject" /Game/VillageMeshV2/Lvl_PandoriV2_WP -game -DisablePython -VillageMeshSmoke -VillageMeshOverview -RenderOffscreen -unattended -nosound -ResX=1440 -ResY=900 -ForceRes "-ExecCmds=$Commands" "-abslog=$ProjectRoot\Saved\Logs\VillageV2Smoke.log"
    if($LASTEXITCODE -ne 0){throw "V2 smoke failed with exit code $LASTEXITCODE"}
    foreach ($Name in @('runtime_smoke.json','overview.png')) {
        Copy-Item -LiteralPath (Join-Path $LegacyEvidence $Name) -Destination (Join-Path $Evidence $Name)
    }
    $Report=Get-Content -LiteralPath (Join-Path $Evidence 'runtime_smoke.json') -Raw | ConvertFrom-Json
    if(-not $Report.passed){throw 'V2 physics smoke did not pass'}
} finally {
    foreach($Name in $Original.Keys){[IO.File]::WriteAllBytes((Join-Path $LegacyEvidence $Name),$Original[$Name])}
}
