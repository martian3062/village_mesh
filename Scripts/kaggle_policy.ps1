param(
    [ValidateSet('Prepare','Run','Status','Logs','Readback','Download')][string]$Action='Status'
)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Cli=Join-Path $Root 'Saved/Kaggle/venv/Scripts/kaggle.exe'
$CredentialDir=Join-Path $env:LOCALAPPDATA 'VillageMesh/Kaggle'
$TokenPath=Join-Path $CredentialDir 'access_token'
if(-not (Test-Path -LiteralPath $Cli)){throw 'Install kaggle==2.2.5 in Saved/Kaggle/venv. See README.md#kaggle.'}
if(-not (Test-Path -LiteralPath $TokenPath)){throw 'Put the project Kaggle token in the local credential file described in README.md#kaggle.'}
$OldToken=$env:KAGGLE_API_TOKEN
$OldConfig=$env:KAGGLE_CONFIG_DIR
$OldUtf8=$env:PYTHONUTF8
Push-Location $Root
try {
    $env:KAGGLE_API_TOKEN=[System.IO.File]::ReadAllText($TokenPath).Trim()
    $env:KAGGLE_CONFIG_DIR=$CredentialDir
    $env:PYTHONUTF8='1'
    $Job=Join-Path $Root 'Saved/Kaggle/job'
    $RunFile=Join-Path $Root 'Saved/Kaggle/run.json'
    if($Action -eq 'Prepare'){
        $Probe=Join-Path $Root 'Saved/Kaggle/auth-probe'
        [void](New-Item -ItemType Directory -Path $Probe -Force)
        & $Cli kernels init -p $Probe
        if($LASTEXITCODE -ne 0){throw 'Kaggle authentication did not pass.'}
        $Owner=((Get-Content (Join-Path $Probe 'kernel-metadata.json') -Raw|ConvertFrom-Json).id -split '/')[0]
        python Scripts/build_kaggle_policy_job.py --owner $Owner
        if($LASTEXITCODE -ne 0){throw 'Kaggle source packaging failed.'}
        return
    }
    if($Action -eq 'Run'){
        $Metadata=Get-Content (Join-Path $Job 'kernel-metadata.json') -Raw|ConvertFrom-Json
        if($Metadata.is_private -ne $true -or $Metadata.enable_gpu -ne $true){throw 'This runner requires a private GPU job.'}
        $Lines=@(& $Cli kernels push -p $Job --accelerator NvidiaTeslaT4 --timeout 1800)
        $Code=$LASTEXITCODE
        $Lines|ForEach-Object {Write-Output $_}
        if($Code -ne 0){throw 'Kaggle did not accept the GPU job.'}
        $Version=[regex]::Match(($Lines -join "`n"),'Kernel version (\d+)')
        if(-not $Version.Success){throw 'Push returned no version; inspect the CLI result before downloading.'}
        [ordered]@{kernel=$Metadata.id;version=[int]$Version.Groups[1].Value;private=$true;requested_accelerator='NvidiaTeslaT4';submitted_at_utc=[DateTime]::UtcNow.ToString('o');status='submitted'}|ConvertTo-Json|Set-Content -LiteralPath $RunFile -Encoding UTF8
        return
    }
    $Run=Get-Content $RunFile -Raw|ConvertFrom-Json
    $Reference=$Run.kernel+'/'+$Run.version
    if($Action -eq 'Status'){
        & $Cli kernels status $Reference
    }elseif($Action -eq 'Logs'){
        & $Cli kernels logs $Reference
    }elseif($Action -eq 'Readback'){
        $Destination=Join-Path $Root ('Saved/Kaggle/readback/v'+$Run.version)
        [void](New-Item -ItemType Directory -Path $Destination -Force)
        & $Cli kernels pull $Reference -p $Destination -m
    }else{
        $Destination=Join-Path $Root ('Saved/Kaggle/results/v'+$Run.version)
        [void](New-Item -ItemType Directory -Path $Destination -Force)
        & $Cli kernels output $Reference -p $Destination --file-pattern 'village_mesh_results/.*'
    }
    if($LASTEXITCODE -ne 0){throw "Kaggle $Action failed."}
}finally{
    $env:KAGGLE_API_TOKEN=$OldToken
    $env:KAGGLE_CONFIG_DIR=$OldConfig
    $env:PYTHONUTF8=$OldUtf8
    Pop-Location
}
