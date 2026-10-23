param([Parameter(Mandatory=$true)][string]$EngineRoot)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$Commandlet = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Project = Join-Path $ProjectRoot 'rural_pardeep.uproject'
# The source map is preserved. No DeleteSourceLevels or source-control mutation.
& $Commandlet $Project -run=WorldPartitionConvertCommandlet /Game/VillageMesh/Lvl_PandoriNijjaran -ConversionSuffix -SCCProvider=None -unattended -AllowCommandletRendering -NullRHI -nosound "-abslog=$ProjectRoot\Saved\Logs\VillageMeshPartition.log"
if ($LASTEXITCODE -ne 0) { throw 'World Partition conversion failed; source map is preserved' }
