param([string]$EngineRoot='E:\U.E\UE_5.8')
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Map='/Game/VillageMeshV3/Lvl_PandoriV3_WP'
$Active=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$ProjectRoot*"})
if($Active.Count){throw 'Close this project before using the temporary packaging profile.'}
$Paths=@($Project,(Join-Path $ProjectRoot 'Config/DefaultEngine.ini'),(Join-Path $ProjectRoot 'Config/DefaultGame.ini'))
$Original=@($Paths|ForEach-Object {,[IO.File]::ReadAllBytes($_)})
$Profile=Get-Content (Join-Path $ProjectRoot 'Config/v2_runtime_plugins.json') -Raw|ConvertFrom-Json
$Descriptor=[Text.Encoding]::UTF8.GetString($Original[0])|ConvertFrom-Json
foreach($Plugin in $Descriptor.Plugins){if($Plugin.Name -in $Profile.disabled_for_package -and $Plugin.Name -ne 'NNERuntimeORT'){$Plugin.Enabled=$false}}
try {
    [IO.File]::WriteAllText($Paths[0],($Descriptor|ConvertTo-Json -Depth 12),(New-Object Text.UTF8Encoding($false)))
    $Engine=[Text.Encoding]::UTF8.GetString($Original[1]).Replace('/Game/VillageMesh/Lvl_PandoriNijjaran_WP.Lvl_PandoriNijjaran_WP',"$Map.Lvl_PandoriV3_WP")
    [IO.File]::WriteAllText($Paths[1],$Engine,(New-Object Text.UTF8Encoding($false)))
    $Game=[Text.Encoding]::UTF8.GetString($Original[2])+"`n[/Script/UnrealEd.ProjectPackagingSettings]`n+DirectoriesToAlwaysStageAsNonUFS=(Path=`"V25`")`n+DirectoriesToAlwaysStageAsNonUFS=(Path=`"V3`")`n+DirectoriesToAlwaysCook=(Path=`"/Game/VillageMeshV25`")`n+DirectoriesToAlwaysCook=(Path=`"/Game/VillageMeshV3`")`n+DirectoriesToNeverCook=(Path=`"/Game/VillageMeshV3/Player`")`n"
    [IO.File]::WriteAllText($Paths[2],$Game,(New-Object Text.UTF8Encoding($false)))
    & "$EngineRoot\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$Project" -noP4 -platform=Win64 -clientconfig=Development -build -cook "-map=$Map" -stage -pak -archive "-archivedirectory=$ProjectRoot\Saved\Packages\V3" -AdditionalCookerOptions=-DisablePython -unattended -utf8output
    if($LASTEXITCODE -ne 0){throw 'V3 packaging failed'}
} finally {
    for($i=0;$i -lt $Paths.Count;$i++){[IO.File]::WriteAllBytes($Paths[$i],$Original[$i])}
}
$Output=Join-Path $ProjectRoot 'Saved/Packages/V3/Windows'
@'
@echo off
start "" "%~dp0rural_pardeep.exe" -VillageV25 -VillageV3 -windowed -ResX=1440 -ResY=900 -ForceRes "-ExecCmds=sg.ViewDistanceQuality 3,sg.ShadowQuality 3,sg.GlobalIlluminationQuality 3,sg.ReflectionQuality 3,r.ScreenPercentage 67,t.MaxFPS 60"
'@ | Set-Content -LiteralPath (Join-Path $Output 'Play_V3.cmd') -Encoding ASCII
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'LICENSE') -Destination (Join-Path $Output 'SOURCE_LICENSE.txt')
python (Join-Path $PSScriptRoot 'readme_sections.py') export-notices (Join-Path $Output 'THIRD_PARTY_NOTICES.txt')
if($LASTEXITCODE -ne 0){throw 'Package built, but notice export failed'}
Write-Output "V3 package: $Output"
