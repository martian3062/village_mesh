param([Parameter(Mandatory=$true)][string]$EngineRoot)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Map='/Game/VillageMeshV2/Lvl_PandoriV2_WP'
$ActiveEditors=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$ProjectRoot*" })
if ($ActiveEditors.Count) { throw 'Save and close this project in Unreal before packaging; the package profile temporarily changes its plugin descriptor.' }
$OriginalBytes=[System.IO.File]::ReadAllBytes($Project)
$EngineConfig=Join-Path $ProjectRoot 'Config\DefaultEngine.ini'
$OriginalEngineBytes=[System.IO.File]::ReadAllBytes($EngineConfig)
$Profile=Get-Content -LiteralPath (Join-Path $ProjectRoot 'Config\v2_runtime_plugins.json') -Raw | ConvertFrom-Json
$Descriptor=[Text.Encoding]::UTF8.GetString($OriginalBytes) | ConvertFrom-Json
foreach ($Plugin in $Descriptor.Plugins) {
    if ($Plugin.Name -in $Profile.disabled_for_package) { $Plugin.Enabled=$false }
}
try {
    [System.IO.File]::WriteAllText($Project,($Descriptor | ConvertTo-Json -Depth 12),(New-Object Text.UTF8Encoding($false)))
    $PackageEngineText=[Text.Encoding]::UTF8.GetString($OriginalEngineBytes).Replace('/Game/VillageMesh/Lvl_PandoriNijjaran_WP.Lvl_PandoriNijjaran_WP','/Game/VillageMeshV2/Lvl_PandoriV2_WP.Lvl_PandoriV2_WP')
    [System.IO.File]::WriteAllText($EngineConfig,$PackageEngineText,(New-Object Text.UTF8Encoding($false)))
    & "$EngineRoot\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$Project" -noP4 -platform=Win64 -clientconfig=Development -build -cook "-map=$Map" -stage -pak -archive "-archivedirectory=$ProjectRoot\Saved\Packages\V2" -AdditionalCookerOptions=-DisablePython -unattended -utf8output
    if ($LASTEXITCODE -ne 0) { throw "V2 packaging failed with exit code $LASTEXITCODE" }
} finally {
    [System.IO.File]::WriteAllBytes($Project,$OriginalBytes)
    [System.IO.File]::WriteAllBytes($EngineConfig,$OriginalEngineBytes)
}
python (Join-Path $PSScriptRoot 'write_v2_package_notes.py')
if ($LASTEXITCODE -ne 0) { throw 'Package built, but its README/attribution copy failed' }
