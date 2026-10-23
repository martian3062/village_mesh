param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [ValidateSet('Build','Partition','HLOD','Audit','Play','Capture','Route','Interactions','Soak','Package')][string]$Action='Play',
    [ValidateSet('daylight','evening','overcast','rain')][string]$Condition='daylight',
    [ValidateSet('playable','capture')][string]$Quality='playable',
    [string]$RunId='local',
    [switch]$SkipCompile,
    [switch]$Headless
)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
$Commandlet=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Map='/Game/VillageMeshV2/Lvl_PandoriV2_WP'
if (-not (Test-Path -LiteralPath $Editor)) { throw 'Invalid EngineRoot' }
if ($Action -eq 'Capture' -and $Headless) { throw 'Capture requires rendering; omit -Headless.' }
Push-Location $ProjectRoot
try {
    if ($Action -eq 'Build') {
        python Scripts\prepare_v2.py --audit-only
        if ($LASTEXITCODE -ne 0) { throw 'V2 data audit failed' }
        python Scripts\fetch_open_assets.py
        if ($LASTEXITCODE -ne 0) { throw 'Texture verification failed' }
        python Scripts\fetch_open_models.py
        if ($LASTEXITCODE -ne 0) { throw 'Model verification failed' }
        if (-not $SkipCompile) {
            & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" rural_pardeepEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
            if ($LASTEXITCODE -ne 0) { throw 'C++ build failed' }
        }
        & $Commandlet $Project -run=pythonscript "-script=$PSScriptRoot\build_v2_world.py" -unattended -NullRHI -nosound "-abslog=$ProjectRoot\Saved\Logs\VillageV2Build.log"
        if ($LASTEXITCODE -ne 0) { throw 'V2 generation failed' }
        $Action='Partition'
    }
    if ($Action -eq 'Partition') {
        & $Commandlet $Project -run=WorldPartitionConvertCommandlet /Game/VillageMeshV2/Lvl_PandoriV2 -ConversionSuffix -SCCProvider=None -unattended -AllowCommandletRendering -NullRHI -nosound "-abslog=$ProjectRoot\Saved\Logs\VillageV2Partition.log"
    } elseif ($Action -eq 'HLOD') {
        & $Commandlet $Project $Map -run=WorldPartitionBuilderCommandlet -Builder=WorldPartitionHLODsBuilder -SetupHLODs -BuildHLODs -AllowCommandletRendering -unattended -nosound -SCCProvider=None "-abslog=$ProjectRoot\Saved\Logs\VillageV2HLOD.log"
    } elseif ($Action -eq 'Audit') {
        & $Commandlet $Project -run=pythonscript "-script=$PSScriptRoot\validate_open_world.py" -VillageV2 -unattended -NullRHI -nosound "-abslog=$ProjectRoot\Saved\Logs\VillageV2Audit.log"
    } elseif ($Action -eq 'Package') {
        & "$PSScriptRoot\package_v2.ps1" -EngineRoot $EngineRoot
    } else {
        $RunArgs=@($Project,$Map,'-game','-DisablePython','-nosplash','-windowed','-ResX=1440','-ResY=900','-ForceRes')
        $Graphics=Get-Content -LiteralPath (Join-Path $ProjectRoot 'Config\v2_quality.json') -Raw | ConvertFrom-Json
        $Scale=if($Quality -eq 'capture'){$Graphics.capture_screen_percentage}else{$Graphics.playable_screen_percentage}
        $Commands=(@($Graphics.cvars)+@("r.ScreenPercentage $Scale"))-join ','
        if($Action -eq 'Play'){$Commands+=",t.MaxFPS $($Graphics.interactive_max_fps)"}
        $RunArgs += "-ExecCmds=$Commands"
        if ($Action -ne 'Play') {
            $RunArgs += @("-VillageV2$Action=$Condition","-VillageRunId=$RunId",'-unattended','-nosound')
            if ($Headless) { $RunArgs+='-NullRHI' } else { $RunArgs+='-RenderOffscreen' }
        }
        $RunStartedUtc=[DateTime]::UtcNow
        if ($Action -eq 'Play') {
            # Play explicitly requests the visible interactive game window.
            $QuotedArgs=$RunArgs | ForEach-Object { '"'+$_+'"' }
            Start-Process -FilePath $Editor -ArgumentList $QuotedArgs
            return
        }
        & $Commandlet @RunArgs
        if ($Action -eq 'Capture' -and $LASTEXITCODE -eq 0) {
            foreach ($Index in 1..8) {
                $CapturePath=Join-Path $ProjectRoot ('Saved\VillageMeshV2\{0}_{1:00}.png' -f $Condition,$Index)
                $Capture=Get-Item -LiteralPath $CapturePath -ErrorAction Stop
                if ($Capture.Length -eq 0 -or $Capture.LastWriteTimeUtc -lt $RunStartedUtc) { throw "Missing or stale capture: $CapturePath" }
            }
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "V2 $Action exited with code $LASTEXITCODE; inspect Saved\Logs" }
} finally { Pop-Location }
