param(
    [ValidateSet('Preflight','Inspect','Create','Style','Wardrobe','Rig','Textures','Assemble','Edit')][string]$Action='Preflight',
    [string]$EngineRoot='E:\U.E\UE_5.8'
)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $Root 'rural_pardeep.uproject'
$Script=Join-Path $PSScriptRoot 'build_metahuman_pilot.py'
$LogDir=Join-Path $Root 'Saved/Logs'
[void](New-Item -ItemType Directory -Path $LogDir -Force)
Push-Location $Root
try {
    if($Action -eq 'Preflight'){
        python Scripts/metahuman_pilot_config.py --engine-root $EngineRoot
        if($LASTEXITCODE -ne 0){throw 'MetaHuman Core Data is not ready. See Saved/MetaHumanPilot/preflight.json.'}
        return
    }
    $Active=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$Root*"})
    if($Active.Count){throw 'Close this project before running a pilot build stage.'}
    if($Action -notin @('Inspect','Create')){
        python Scripts/metahuman_pilot_config.py --engine-root $EngineRoot
        if($LASTEXITCODE -ne 0){throw 'Install the required Core Data before opening or editing the pilot.'}
    }
    $Arguments=@($Project,"-MHPilotAction=$Action",'-nosound',"-abslog=$LogDir\MetaHumanPilot_$Action.log")
    if($Action -eq 'Edit'){
        $Arguments+=@('/Game/VillageMeshV3/Lvl_PandoriV3_WP',"-ExecutePythonScript=$Script")
        Start-Process -FilePath "$EngineRoot\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList ($Arguments|ForEach-Object {'"'+$_+'"'})
        return
    }
    $Started=[DateTime]::UtcNow
    $Arguments+=@('-run=pythonscript',"-script=$Script",'-unattended')
    if($Action -in @('Inspect','Create')){$Arguments+='-NullRHI'}else{$Arguments+='-RenderOffscreen'}
    & "$EngineRoot\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" @Arguments
    if($LASTEXITCODE -ne 0){throw "MetaHuman $Action stage failed. Read the matching Saved/Logs/MetaHumanPilot log."}
    $Report=Get-Item -LiteralPath (Join-Path $Root ('Saved/MetaHumanPilot/'+$Action.ToLowerInvariant()+'.json'))
    if($Report.LastWriteTimeUtc -lt $Started -or -not (Get-Content $Report.FullName -Raw|ConvertFrom-Json).passed){throw 'Pilot report is failed or stale.'}
}finally{Pop-Location}
