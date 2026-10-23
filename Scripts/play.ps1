param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [switch]$Smoke,
    [switch]$Overview,
    [switch]$Headless
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$Project = Join-Path $ProjectRoot 'rural_pardeep.uproject'
$Editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
$RunArgs = @($Project,'/Game/VillageMesh/Lvl_PandoriNijjaran_WP','-game','-DisablePython','-nosplash','-windowed','-ResX=1440','-ResY=900','-ForceRes')
# Python and MCP authoring startup scripts are editor-only; gameplay is native C++.
if ($Smoke) { $RunArgs += @('-VillageMeshSmoke','-unattended','-nosound') }
if ($Overview) { $RunArgs += '-VillageMeshOverview' }
if ($Headless) { $RunArgs += '-NullRHI' }
elseif ($Smoke) { $RunArgs += '-RenderOffscreen' }
& $Editor @RunArgs
if ($LASTEXITCODE -ne 0) { throw "Unreal exited with code $LASTEXITCODE" }
