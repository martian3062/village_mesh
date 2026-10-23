param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [switch]$OpenEditor
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$Project = Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Builder = Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
$Commandlet = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if (-not (Test-Path -LiteralPath $Builder)) { throw 'EngineRoot must contain Engine\Build\BatchFiles\Build.bat' }
Push-Location $ProjectRoot
try {
    python Scripts\fetch_open_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'CC0 texture download failed' }
    python Scripts\fetch_open_models.py
    if ($LASTEXITCODE -ne 0) { throw 'CC0 vegetation download failed' }
    & $Builder rural_pardeepEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw 'Unreal C++ build failed' }
    & $Commandlet $Project -run=pythonscript "-script=$PSScriptRoot\build_pandori_world.py" -unattended -NullRHI -nosound
    if ($LASTEXITCODE -ne 0) { throw 'World generation failed; inspect Saved\Logs' }
    & "$PSScriptRoot\partition_world.ps1" -EngineRoot $EngineRoot
    if ($OpenEditor) {
        $Editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
        # This switch explicitly requests the visible interactive editor.
        Start-Process -FilePath $Editor -ArgumentList ('"' + $Project + '"')
    }
} finally { Pop-Location }
