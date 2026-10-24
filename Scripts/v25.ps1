param(
    [string]$EngineRoot='E:\U.E\UE_5.8',
    [ValidateSet('Build','Play','Check','Package')][string]$Action='Play',
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$RunId='local',
    [ValidateRange(30,7200)][int]$Seconds=120,
    [switch]$Learned,[switch]$MissingModel,[switch]$Headless,[switch]$Screenshots
)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
$Cmd=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
Push-Location $ProjectRoot
try {
    if($Action -eq 'Build'){
        python Scripts/prepare_v25.py
        if($LASTEXITCODE -ne 0){throw 'V2.5 input validation failed'}
        & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" rural_pardeepEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
        if($LASTEXITCODE -ne 0){throw 'V2.5 compile failed'}
        & $Cmd $Project -run=pythonscript "-script=$PSScriptRoot\build_v25_assets.py" -unattended -NullRHI -nosound "-abslog=$ProjectRoot\Saved\Logs\V25Assets.log"
        if($LASTEXITCODE -ne 0){throw 'V2.5 model/material import failed'}
        return
    }
    if($Action -eq 'Package'){ & "$PSScriptRoot\package_v25.ps1" -EngineRoot $EngineRoot;return }
    $Graphics=Get-Content Config/v2_quality.json -Raw | ConvertFrom-Json
    $Commands=(@($Graphics.cvars)+@('r.ScreenPercentage 67'))-join ','
    $Arguments=@($Project,'/Game/VillageMeshV2/Lvl_PandoriV2_WP','-game','-VillageV25','-DisablePython','-windowed','-ResX=1440','-ResY=900','-ForceRes')
    if($Learned){$Arguments+='-V25Learned'}
    if($MissingModel){$Arguments+='-V25MissingModel'}
    if($Screenshots){$Arguments+='-V25Screenshots'}
    if($Action -eq 'Play'){
        $Arguments+='-ExecCmds='+$Commands+',t.MaxFPS 60'
        Start-Process -FilePath $Editor -ArgumentList ($Arguments|ForEach-Object {'"'+$_+'"'})
    }else{
        $Arguments+=@('-V25Check',"-V25Seconds=$Seconds","-V25Run=$RunId",'-unattended','-nosound',"-ExecCmds=$Commands","-abslog=$ProjectRoot\Saved\Logs\V25_$RunId.log")
        if($Headless){$Arguments+='-NullRHI'}else{$Arguments+='-RenderOffscreen'}
        $CheckStarted=[DateTime]::UtcNow
        & $Cmd @Arguments
        if($LASTEXITCODE -ne 0){throw "V2.5 runtime check failed: $RunId"}
        $Report=Get-Item -LiteralPath (Join-Path $ProjectRoot "Saved/VillageMeshV25/runtime_$RunId.json")
        if($Report.LastWriteTimeUtc -lt $CheckStarted){throw 'Stale V2.5 check report'}
        if(-not (Get-Content $Report.FullName -Raw|ConvertFrom-Json).passed){throw "V2.5 diagnostic reported a failure: $RunId"}
    }
}finally{Pop-Location}
