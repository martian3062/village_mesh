param(
    [ValidateSet('Build','Check','Play','Editor')][string]$Action='Play',
    [string]$EngineRoot='E:\U.E\UE_5.8',
    [switch]$SkipCompile
)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $Root 'rural_pardeep.uproject'
$Cmd=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$Editor=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe'
$Map='/Game/VillageMeshV3/Lvl_PandoriV3_Pardeep_WP'
Push-Location $Root
try {
    if($Action -eq 'Build'){
        $Active=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$Root*"})
        if($Active.Count){throw 'Save and close this project before building the village copy.'}
        python Scripts/village_streets.py
        if($LASTEXITCODE -ne 0){throw 'Street geometry failed'}
        if(-not $SkipCompile){
            & "$EngineRoot/Engine/Build/BatchFiles/Build.bat" rural_pardeepEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
            if($LASTEXITCODE -ne 0){throw 'Player compile failed'}
        }
        & $Cmd $Project -run=pythonscript "-script=$PSScriptRoot/build_village_streets.py" -unattended -NullRHI -nosound "-abslog=$Root/Saved/Logs/VillageStreetsBuild.log"
        if($LASTEXITCODE -ne 0){throw 'Village street asset build failed'}
        & $Cmd $Project -run=WorldPartitionConvertCommandlet /Game/VillageMeshV3/Lvl_PandoriV3_Pardeep -ConversionSuffix -SCCProvider=None -unattended -AllowCommandletRendering -NullRHI -nosound "-abslog=$Root/Saved/Logs/VillageStreetsPartition.log"
        if($LASTEXITCODE -ne 0){throw 'Village partition conversion failed'}
        return
    }
    $Args=@($Project,$Map,'-VillageV25','-VillageV3','-V25NoSave','-DisablePython',
        '-ini:Engine:[DevOptions.Shaders]:ShaderCompilerCoreCountThreshold=64',
        '-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=12')
    if($Action -eq 'Editor'){
        Start-Process -FilePath $Editor -ArgumentList ($Args|ForEach-Object {'"'+$_+'"'})
        return
    }
    $Args+=@('-game','-windowed','-ResX=1440','-ResY=900','-ForceRes',
        '-ExecCmds=r.ScreenPercentage 67,t.MaxFPS 60,r.LumenScene.SurfaceCache.CardTexelDensityScale 50')
    if($Action -eq 'Play'){
        Start-Process -FilePath $Editor -ArgumentList ($Args|ForEach-Object {'"'+$_+'"'})
        return
    }
    $Started=[DateTime]::UtcNow
    & $Cmd @Args -PardeepCheck -RenderOffscreen -unattended -nosound "-abslog=$Root/Saved/Logs/PardeepRuntime.log"
    if($LASTEXITCODE -ne 0){throw 'Third-person runtime check failed'}
    $Report=Get-Item -LiteralPath Saved/PardeepPlayer/runtime_check.json
    if($Report.LastWriteTimeUtc -lt $Started -or -not (Get-Content $Report.FullName -Raw|ConvertFrom-Json).passed){throw 'Runtime report failed or is stale'}
}finally{Pop-Location}
