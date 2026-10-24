param([string]$EngineRoot='E:\U.E\UE_5.8')
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Map='/Game/VillageMeshV2/Lvl_PandoriV2_WP'
$ActiveEditors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$ProjectRoot*"})
if($ActiveEditors.Count){throw 'Save and close this project before packaging; the temporary package profile must not race an editor session.'}
$EngineConfig=Join-Path $ProjectRoot 'Config/DefaultEngine.ini'
$GameConfig=Join-Path $ProjectRoot 'Config/DefaultGame.ini'
$OriginalProject=[IO.File]::ReadAllBytes($Project)
$OriginalEngine=[IO.File]::ReadAllBytes($EngineConfig)
$OriginalGame=[IO.File]::ReadAllBytes($GameConfig)
$Profile=Get-Content (Join-Path $ProjectRoot 'Config/v2_runtime_plugins.json') -Raw | ConvertFrom-Json
$Descriptor=[Text.Encoding]::UTF8.GetString($OriginalProject) | ConvertFrom-Json
foreach($Plugin in $Descriptor.Plugins){if($Plugin.Name -in $Profile.disabled_for_package -and $Plugin.Name -ne 'NNERuntimeORT'){$Plugin.Enabled=$false}}
try{
    [IO.File]::WriteAllText($Project,($Descriptor|ConvertTo-Json -Depth 12),(New-Object Text.UTF8Encoding($false)))
    $EngineText=[Text.Encoding]::UTF8.GetString($OriginalEngine).Replace('/Game/VillageMesh/Lvl_PandoriNijjaran_WP.Lvl_PandoriNijjaran_WP','/Game/VillageMeshV2/Lvl_PandoriV2_WP.Lvl_PandoriV2_WP')
    [IO.File]::WriteAllText($EngineConfig,$EngineText,(New-Object Text.UTF8Encoding($false)))
    $GameText=[Text.Encoding]::UTF8.GetString($OriginalGame)+"`n[/Script/UnrealEd.ProjectPackagingSettings]`n+DirectoriesToAlwaysStageAsNonUFS=(Path=`"V25`")`n+DirectoriesToAlwaysCook=(Path=`"/Game/VillageMeshV25`")`n"
    [IO.File]::WriteAllText($GameConfig,$GameText,(New-Object Text.UTF8Encoding($false)))
    & "$EngineRoot\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$Project" -noP4 -platform=Win64 -clientconfig=Development -build -cook "-map=$Map" -stage -pak -archive "-archivedirectory=$ProjectRoot\Saved\Packages\V25" -AdditionalCookerOptions=-DisablePython -unattended -utf8output
    if($LASTEXITCODE -ne 0){throw "V2.5 package failed with exit $LASTEXITCODE"}
}finally{
    [IO.File]::WriteAllBytes($Project,$OriginalProject);[IO.File]::WriteAllBytes($EngineConfig,$OriginalEngine);[IO.File]::WriteAllBytes($GameConfig,$OriginalGame)
}
$Output=Join-Path $ProjectRoot 'Saved/Packages/V25/Windows'
@'
@echo off
start "" "%~dp0rural_pardeep.exe" -VillageV25 -windowed -ResX=1440 -ResY=900 -ForceRes "-ExecCmds=sg.ViewDistanceQuality 3,sg.ShadowQuality 3,sg.GlobalIlluminationQuality 3,sg.ReflectionQuality 3,r.ScreenPercentage 67,t.MaxFPS 60"
'@ | Set-Content -LiteralPath (Join-Path $Output 'Play_V25.cmd') -Encoding ASCII
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'LICENSE') -Destination (Join-Path $Output 'SOURCE_LICENSE.txt')
python (Join-Path $PSScriptRoot 'readme_sections.py') export-notices (Join-Path $Output 'THIRD_PARTY_NOTICES.txt')
if($LASTEXITCODE -ne 0){throw 'Package built, but notice export failed'}
Write-Output "V2.5 Windows Development package: $Output"
python (Join-Path $PSScriptRoot 'write_v25_package_notes.py')
if($LASTEXITCODE -ne 0){throw 'Package built, but package documentation failed'}
