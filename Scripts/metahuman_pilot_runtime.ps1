param(
    [ValidateSet('Play','Check','PIE')][string]$Action='Play',
    [string]$EngineRoot='E:\U.E\UE_5.8',
    [switch]$SkipCompile
)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $Root 'rural_pardeep.uproject'
$Out=Join-Path $Root 'Saved/MetaHumanPilot'
Push-Location $Root
try {
    $Active=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$Root*"})
    if($Active.Count){throw 'Close this project before launching the pilot runtime.'}
    $Assembly=Get-Content (Join-Path $Out 'assemble.json') -Raw|ConvertFrom-Json
    $ProfileHash=(Get-FileHash Assets/MetaHumans/manpreet.json -Algorithm SHA256).Hash.ToLowerInvariant()
    if(-not $Assembly.passed -or $Assembly.profile_sha256 -ne $ProfileHash){throw 'Complete assembly with the current profile before runtime validation.'}
    if(-not $SkipCompile){
        & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" rural_pardeepEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
        if($LASTEXITCODE -ne 0){throw 'Pilot editor build failed'}
    }
    $Map='/Game/VillageMeshV3/Lvl_PandoriV3_WP?game=/Script/rural_pardeep.MetaHumanPilotGameMode'
    $ShaderArguments=@('-ini:Engine:[DevOptions.Shaders]:ShaderCompilerCoreCountThreshold=64','-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=12')
    if($Action -eq 'PIE'){
        $EditorArguments=@($Project,'/Game/VillageMeshV3/Lvl_PandoriV3_WP','-VillageV25','-VillageV3','-V25NoSave','-MHPilotCheck',"-ExecutePythonScript=$PSScriptRoot\open_metahuman_pilot_pie.py","-abslog=$Root\Saved\Logs\MetaHumanPilot_PIE.log",
            '-ExecCmds=r.LumenScene.SurfaceCache.CardTexelDensityScale 50',
            '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bMonitorContentDirectories=False')
        $EditorArguments+=$ShaderArguments
        Start-Process -FilePath "$EngineRoot\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList ($EditorArguments|ForEach-Object {'"'+$_+'"'})
        return
    }
    $RuntimeArguments=@($Project,$Map,'-game','-VillageV25','-VillageV3','-V25NoSave','-DisablePython','-windowed','-ResX=1440','-ResY=900','-ForceRes','-ExecCmds=sg.ViewDistanceQuality 3,sg.ShadowQuality 3,sg.GlobalIlluminationQuality 3,sg.ReflectionQuality 3,r.ScreenPercentage 67,t.MaxFPS 60')
    $RuntimeArguments+=$ShaderArguments
    if($Action -eq 'Play'){
        Start-Process -FilePath "$EngineRoot\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList ($RuntimeArguments|ForEach-Object {'"'+$_+'"'})
        return
    }
    foreach($Mode in @('baseline','character')){
        $Started=[DateTime]::UtcNow
        $Extra=@();if($Mode -eq 'baseline'){$Extra+='-MHPilotBaseline'}
        & "$EngineRoot\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" @RuntimeArguments @Extra -MHPilotCheck -RenderOffscreen -unattended -nosound "-abslog=$Root\Saved\Logs\MetaHumanPilot_Runtime_$Mode.log"
        if($LASTEXITCODE -ne 0){throw "Pilot $Mode runtime failed"}
        $File=Get-Item (Join-Path $Out "runtime_$Mode.json")
        if($File.LastWriteTimeUtc -lt $Started -or -not (Get-Content $File.FullName -Raw|ConvertFrom-Json).passed){throw "Pilot $Mode report failed or is stale"}
    }
    $Baseline=Get-Content (Join-Path $Out 'runtime_baseline.json') -Raw|ConvertFrom-Json
    $Character=Get-Content (Join-Path $Out 'runtime_character.json') -Raw|ConvertFrom-Json
    [ordered]@{
        passed=$true;profile_sha256=$ProfileHash;recorded_at_utc=[DateTime]::UtcNow.ToString('o')
        baseline_p95_ms=$Baseline.frame_p95_ms;character_p95_ms=$Character.frame_p95_ms
        difference_p95_ms=($Character.frame_p95_ms - $Baseline.frame_p95_ms)
        resolution='1440x900';screen_percentage=67;fps_cap=60
        scope='Two local standalone runs at the same mapped street; other applications remain open. Not a packaged build, crowd benchmark or release soak.'
    }|ConvertTo-Json|Set-Content (Join-Path $Out 'runtime_comparison.json') -Encoding UTF8
}finally{Pop-Location}
