param(
    [ValidateSet('Prepare','Turban','Character','Refine','Verify')][string]$Action='Character',
    [string]$EngineRoot='E:\U.E\UE_5.8'
)
$ErrorActionPreference='Continue' # Native Unreal progress can arrive on stderr in Windows PowerShell.
$Root=Split-Path $PSScriptRoot -Parent
$Project=Join-Path $Root 'rural_pardeep.uproject'
$Active=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like '*rural_pardeep.uproject*'})
if($Active.Count){throw 'Save and close this project before rebuilding its character assets.'}
$Started=[DateTime]::UtcNow
if($Action -eq 'Character'){
    $Arguments=@($Project,'/Engine/Maps/Templates/Template_Default',"-ExecutePythonScript=$PSScriptRoot/build_pardeep_character_editor.py",'-unattended','-RenderOffscreen','-nosound',"-abslog=$Root/Saved/Logs/PardeepCharacterBuild.log",
        '-ini:Engine:[DevOptions.Shaders]:ShaderCompilerCoreCountThreshold=64',
        '-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=14',
        '-ini:Engine:[/Script/Engine.RendererSettings]:r.RayTracing=False',
        '-ExecCmds=r.Streaming.PoolSize 512,r.Shadow.Virtual.Enable 0,r.Lumen.DiffuseIndirect.Allow 0,r.Lumen.Reflections.Allow 0,t.MaxFPS 10')
    $Process=Start-Process -FilePath "$EngineRoot/Engine/Binaries/Win64/UnrealEditor.exe" -ArgumentList ($Arguments|ForEach-Object {'"'+$_+'"'}) -WindowStyle Hidden -PassThru
    $ProcessHandle=$Process.Handle;$Process.WaitForExit()
    $Report=Get-Item -LiteralPath "$Root/Saved/PardeepPlayer/character_build.json"
    if(-not $Report -or $Report.LastWriteTimeUtc -lt $Started -or -not (Get-Content $Report.FullName -Raw|ConvertFrom-Json).passed){throw 'Character assembly failed or its report is stale'}
    $BuildEvidence=Get-Content $Report.FullName -Raw|ConvertFrom-Json
    $BuildEvidence | Add-Member -NotePropertyName assembly_editor_exit_code -NotePropertyValue $Process.ExitCode -Force
    $BuildEvidence | Add-Member -NotePropertyName assembly_editor_clean_exit -NotePropertyValue ($null -ne $Process.ExitCode -and $Process.ExitCode -eq 0) -Force
    $BuildEvidence | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $Report.FullName -Encoding UTF8
    # Accept saved output only after a separate process can reload every asset.
    if($null -eq $Process.ExitCode -or $Process.ExitCode -ne 0){Write-Warning "Assembly editor exit code: $($Process.ExitCode). Checking saved assets in a fresh process."}
    & "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" $Project -run=pythonscript "-script=$PSScriptRoot/validate_pardeep_saved.py" -unattended -NullRHI -nosound "-abslog=$Root/Saved/Logs/PardeepSavedAssetCheck.log"
    if($LASTEXITCODE -ne 0){throw 'Saved character reload failed'}
    $Report=Get-Item -LiteralPath "$Root/Saved/PardeepPlayer/saved_asset_check.json"
}else{
    $Script=switch($Action){'Prepare'{'prepare_pardeep_reference.py'} 'Turban'{'build_pardeep_turban.py'} 'Refine'{'refine_pardeep_appearance.py'} 'Verify'{'validate_pardeep_saved.py'}}
    $RHI=if($Action -eq 'Prepare'){'-RenderOffscreen'}else{'-NullRHI'}
    & "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" $Project -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended $RHI -nosound "-abslog=$Root/Saved/Logs/PardeepAppearance_$Action.log"
    if($LASTEXITCODE -ne 0){throw "Pardeep $Action failed"}
    $ReportName=switch($Action){'Refine'{'character_build.json'} 'Verify'{'saved_asset_check.json'} default{'turban_build.json'}}
    $Report=Get-Item -LiteralPath "$Root/Saved/PardeepPlayer/$ReportName"
}
if(-not $Report -or $Report.LastWriteTimeUtc -lt $Started -or -not (Get-Content $Report.FullName -Raw|ConvertFrom-Json).passed){throw 'Appearance result is failed or stale'}
