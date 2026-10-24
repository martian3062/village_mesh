param([string]$EngineRoot='E:\U.E\UE_5.8',[switch]$Rebuild)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
Push-Location $Root
try{
    python -m unittest discover -s Tests -v
    if($LASTEXITCODE -ne 0){throw 'Python checks failed'}
    if($Rebuild){
        & "$PSScriptRoot\v25.ps1" -EngineRoot $EngineRoot -Action Build
        & "$PSScriptRoot\package_v25.ps1" -EngineRoot $EngineRoot
    }
    foreach($Condition in @('daylight','rain')){
        foreach($Repeat in 1..3){& "$PSScriptRoot\check_v25_route.ps1" -Condition $Condition -RunId "v25_$Condition$Repeat"}
    }
    & "$PSScriptRoot\check_v25_package.ps1" -RunId packaged_rules -Seconds 180 -Screenshots
    & "$PSScriptRoot\check_v25_package.ps1" -RunId packaged_rendered -Seconds 180 -Learned -Screenshots
    & "$PSScriptRoot\check_v25_package.ps1" -RunId packaged_missing_model -Seconds 120 -MissingModel -Headless
    & "$PSScriptRoot\check_v25_package.ps1" -RunId packaged_soak -Seconds 1800 -Learned
    foreach($Script in @('audit_v25_package.py','summarize_v25.py','write_v25_package_notes.py')){
        python (Join-Path $PSScriptRoot $Script)
        if($LASTEXITCODE -ne 0){throw "V2.5 evidence publication failed: $Script"}
    }
}finally{Pop-Location}
