# Experimental capture attempt. UE 5.8.3 offscreen output remained in lit mode
# on the recorded workstation; a zero process exit is NOT Lumen acceptance.
param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [ValidateSet('SurfaceCache','Scene')][string]$View='SurfaceCache'
)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$Evidence=Join-Path $ProjectRoot 'Saved\VillageMeshV2'
$Folder=Join-Path $Evidence "Lumen_$View"
[void](New-Item -ItemType Directory -Force -Path $Folder)
$Manifest=Join-Path $ProjectRoot 'Content\Validation\pilot.json'
$OriginalManifest=[IO.File]::ReadAllBytes($Manifest)
$OriginalImages=@{}
foreach($Index in 1..8) {
    $Name='daylight_{0:00}.png' -f $Index
    $Path=Join-Path $Evidence $Name
    if(Test-Path -LiteralPath $Path){$OriginalImages[$Name]=[IO.File]::ReadAllBytes($Path)}
}
try {
    $Payload=[Text.Encoding]::UTF8.GetString($OriginalManifest) | ConvertFrom-Json
    # Five fixed exteriors plus one view inside each representative room.
    $Cameras=@($Payload.cameras | Select-Object -First 5)
    foreach($Space in $Payload.interiors) {
        $DirectionX=$Space.inside_cm[0]-$Space.entrance_cm[0]
        $DirectionY=$Space.inside_cm[1]-$Space.entrance_cm[1]
        $Cameras += [pscustomobject]@{
            id="interior_$($Space.building_id)"
            position_cm=@($Space.inside_cm[0],$Space.inside_cm[1],($Space.inside_cm[2]+70))
            yaw_degrees=([math]::Atan2($DirectionY,$DirectionX)*180/[math]::PI-50)
            pitch_degrees=-4;fov_degrees=85
        }
    }
    $Payload.cameras=$Cameras
    [IO.File]::WriteAllText($Manifest,($Payload|ConvertTo-Json -Depth 15),(New-Object Text.UTF8Encoding($false)))
    $Mode=if($View -eq 'SurfaceCache'){'SurfaceCache'}else{'LumenScene'}
    $Graphics=Get-Content -LiteralPath (Join-Path $ProjectRoot 'Config\v2_quality.json') -Raw | ConvertFrom-Json
    $Commands=(@($Graphics.cvars)+@('r.ScreenPercentage 100','viewmode visualizelumen',"r.Lumen.Visualize.ViewMode $Mode",'ShowFlag.VisualizeLumen 1'))-join ','
    $Started=[DateTime]::UtcNow
    & "$EngineRoot\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$ProjectRoot\rural_pardeep.uproject" /Game/VillageMeshV2/Lvl_PandoriV2_WP -game -DisablePython -VillageV2Capture=daylight "-VillageRunId=lumen_$View" -RenderOffscreen -unattended -nosound -ResX=1440 -ResY=900 -ForceRes "-ExecCmds=$Commands" "-abslog=$ProjectRoot\Saved\Logs\VillageV2Lumen_$View.log"
    if($LASTEXITCODE -ne 0){throw "Lumen capture failed with exit code $LASTEXITCODE"}
    foreach($Index in 1..8) {
        $Name='daylight_{0:00}.png' -f $Index
        $Capture=Get-Item -LiteralPath (Join-Path $Evidence $Name)
        if($Capture.Length -eq 0 -or $Capture.LastWriteTimeUtc -lt $Started){throw "Missing diagnostic view $Name"}
        Copy-Item -LiteralPath $Capture.FullName -Destination (Join-Path $Folder ('view_{0:00}.png' -f $Index))
    }
    $Cameras | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Folder 'cameras.json') -Encoding UTF8
    Write-Warning "Experimental $View captures written to $Folder. The recorded UE 5.8.3 run stayed in lit mode; do not treat process success as Lumen coverage acceptance."
} finally {
    [IO.File]::WriteAllBytes($Manifest,$OriginalManifest)
    foreach($Name in $OriginalImages.Keys){[IO.File]::WriteAllBytes((Join-Path $Evidence $Name),$OriginalImages[$Name])}
}
