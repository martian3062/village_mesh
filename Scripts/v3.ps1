param(
    [string]$EngineRoot='E:\U.E\UE_5.8',
    [ValidateSet('Build','Partition','Editor','Play','Check','Package')][string]$Action='Play',
    [switch]$SkipCompile,
    [switch]$ForceReimport
)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Cmd=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$Editor=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe'
$Map='/Game/VillageMeshV3/Lvl_PandoriV3_WP'
Push-Location $ProjectRoot
try {
    if($Action -eq 'Build') {
        python Scripts/v3_layout.py
        if($LASTEXITCODE -ne 0){throw 'V3 layout failed'}
        python Scripts/v3_geometry.py
        if($LASTEXITCODE -ne 0){throw 'V3 geometry generation failed'}
        if(-not $SkipCompile){
            & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" rural_pardeepEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
            if($LASTEXITCODE -ne 0){throw 'V3 native compile failed'}
        }
        $BuildStarted=[DateTime]::UtcNow
        $ImportArgs=@();if($ForceReimport){$ImportArgs+='-V3ForceReimport'}
        & $Cmd $Project -run=pythonscript "-script=$PSScriptRoot\build_v3_world.py" -unattended -NullRHI -nosound @ImportArgs "-abslog=$ProjectRoot\Saved\Logs\V3Build.log"
        if($LASTEXITCODE -ne 0){throw 'V3 world build failed'}
        $BuildReport=Get-Item -LiteralPath Saved/VillageMeshV3/build_report.json
        if($BuildReport.LastWriteTimeUtc -lt $BuildStarted){throw 'V3 build report is stale'}
        $Action='Partition'
    }
    if($Action -eq 'Partition') {
        & $Cmd $Project -run=WorldPartitionConvertCommandlet /Game/VillageMeshV3/Lvl_PandoriV3 -ConversionSuffix -SCCProvider=None -unattended -AllowCommandletRendering -NullRHI -nosound "-abslog=$ProjectRoot\Saved\Logs\V3Partition.log"
        if($LASTEXITCODE -ne 0){throw 'V3 partition failed'}
        return
    }
    if($Action -eq 'Package'){& "$PSScriptRoot\package_v3.ps1" -EngineRoot $EngineRoot;return}
    if($Action -eq 'Editor'){
        Start-Process -FilePath $Editor -ArgumentList @(('"'+$Project+'"'),$Map,'-DisablePython')
        return
    }
    $Arguments=@($Project,$Map,'-game','-VillageV25','-VillageV3','-DisablePython','-windowed','-ResX=1440','-ResY=900','-ForceRes','-ExecCmds=sg.ViewDistanceQuality 3,sg.ShadowQuality 3,sg.GlobalIlluminationQuality 3,sg.ReflectionQuality 3,r.ScreenPercentage 67,t.MaxFPS 60')
    if($Action -eq 'Play'){Start-Process -FilePath $Editor -ArgumentList ($Arguments|ForEach-Object {'"'+$_+'"'});return}
    $Started=[DateTime]::UtcNow
    & $Cmd @Arguments -V3Check -V25NoSave -RenderOffscreen -unattended -nosound "-abslog=$ProjectRoot\Saved\Logs\V3Check.log"
    if($LASTEXITCODE -ne 0){throw 'V3 runtime exited with failure'}
    $Report=Get-Item -LiteralPath Saved/VillageMeshV3/runtime_check.json
    if($Report.LastWriteTimeUtc -lt $Started -or -not (Get-Content $Report.FullName -Raw|ConvertFrom-Json).passed){throw 'V3 runtime report failed or stale'}
}finally{Pop-Location}
