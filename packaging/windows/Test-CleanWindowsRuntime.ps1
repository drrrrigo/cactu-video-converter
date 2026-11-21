param(
    [Parameter(Mandatory=$true)][ValidateSet('Missing','Installed')][string]$Phase,
    [Parameter(Mandatory=$true)][string]$ArtifactFolder,
    [string]$EvidenceFolder = 'C:\CactuEvidence'
)
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitProcess) { throw 'Use x64 Windows PowerShell.' }
$os = Get-CimInstance Win32_OperatingSystem
if ([int]$os.BuildNumber -lt 22000) { throw 'A clean Windows 11 x64 guest is required.' }
$dlls = @('msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','vcruntime140.dll','vcruntime140_1.dll')
$zip = @(Get-ChildItem -LiteralPath $ArtifactFolder -Filter 'CactuVideoConverter-Portable-*.zip')
$setup = @(Get-ChildItem -LiteralPath $ArtifactFolder -Filter 'CactuVideoConverter-Setup-*.exe')
if ($zip.Count -ne 1 -or $setup.Count -ne 1) { throw 'Provide exactly one portable ZIP and one Setup EXE.' }
$identity = [ordered]@{ portable=(Get-FileHash $zip[0].FullName).Hash; setup=(Get-FileHash $setup[0].FullName).Hash }
$machine = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography').MachineGuid
$hash = [Security.Cryptography.SHA256]::Create()
$guest = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($machine))).Replace('-','')
New-Item -ItemType Directory -Force -Path $EvidenceFolder | Out-Null
$missingReceipt = Join-Path $EvidenceFolder 'runtime-missing.json'
$receipt = [ordered]@{ phase=$Phase; artifacts=$identity; guest_identity_sha256=$guest; os_build=$os.BuildNumber; clean_windows_test=$true; automatic_runtime_install=$false; manual_desktop_acceptance=$false; bundled_microsoft_runtime_files=0 }
$versions = [ordered]@{}
foreach ($dll in $dlls) {
    $file = Join-Path ([Environment]::SystemDirectory) $dll
    $versions[$dll] = if (Test-Path -LiteralPath $file) { (Get-Item -LiteralPath $file).VersionInfo.FileVersion } else { $null }
}
if ($Phase -eq 'Missing') {
    if (@($versions.Values | Where-Object { $null -ne $_ }).Count -ne 0) {
        throw 'Not a missing-runtime baseline: VC DLLs already exist. Use a fresh VM; do not remove system DLLs.'
    }
} else {
    if (-not (Test-Path -LiteralPath $missingReceipt)) { throw 'Run Missing in this same clean guest before installing the official prerequisite.' }
    $prior = Get-Content -Raw $missingReceipt | ConvertFrom-Json
    if ($prior.guest_identity_sha256 -ne $guest -or $prior.artifacts.portable -ne $identity.portable -or $prior.artifacts.setup -ne $identity.setup) {
        throw 'Guest or exact artifact identities differ from the successful missing-runtime baseline.'
    }
}
function Run-Process([string]$File, [string]$Arguments) {
    $p = Start-Process -FilePath $File -ArgumentList $Arguments -PassThru
    if (-not $p.WaitForExit(180000)) { $p.Kill(); throw "Timed out: $([IO.Path]::GetFileName($File))" }
    $p.Refresh(); return $p.ExitCode
}
$temp = Join-Path $env:TEMP ('Cactu runtime qualification ü ' + [Guid]::NewGuid())
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    Expand-Archive -LiteralPath $zip[0].FullName -DestinationPath $temp
    $portable = Join-Path $temp 'CactuVideoConverter'
    $forbidden = @(Get-ChildItem -LiteralPath $portable -Recurse -File | Where-Object { $_.Name -match '^(msvcp|vcruntime)\d+.*\.dll$' })
    if ($forbidden.Count) { throw 'Portable still contains Microsoft runtime DLLs.' }
    $launcher = Join-Path $portable 'CactuVideoConverter.exe'
    $probe = Run-Process $launcher '--check-prerequisites'
    $installed = Join-Path $temp 'installed'
    $exit = Run-Process $setup[0].FullName ('/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="{0}"' -f $installed)
    $receipt.probe_exit = $probe; $receipt.installer_exit = $exit
    if ($Phase -eq 'Missing') {
        if ($probe -ne 10 -or $exit -eq 0 -or (Test-Path (Join-Path $installed 'CactuVideoConverter.exe'))) { throw 'Missing prerequisite did not block launch and installation.' }
    } else {
        if ($probe -ne 0 -or $exit -ne 0) { throw 'Prerequisite present but launch/installation check failed.' }
        $env:QT_QPA_PLATFORM = 'offscreen'
        foreach ($item in @(@('portable',$portable),@('installed',$installed))) {
            $resultFolder = Join-Path $temp ($item[0] + '-result')
            $code = Run-Process (Join-Path $item[1] 'CactuVideoConverter.exe') ('--release-smoke "{0}"' -f $resultFolder)
            if ($code -ne 0) { throw 'Frozen conversion smoke failed.' }
            $report = Get-Content -Raw (Join-Path $resultFolder 'smoke-result.json') | ConvertFrom-Json
            foreach ($key in @('ok','frozen','runtime_bundled','faststart','original_unchanged','quick_preview','embedded_subtitle_queue','loudness_queue')) {
                if ($report.$key -ne $true) { throw "Missing frozen evidence: $key" }
            }
            $report.PSObject.Properties.Remove('path')
            $receipt[($item[0] + '_smoke')] = $report
        }
        $forbidden = @(Get-ChildItem -LiteralPath $installed -Recurse -File | Where-Object { $_.Name -match '^(msvcp|vcruntime)\d+.*\.dll$' })
        if ($forbidden.Count) { throw 'Installer delivered Microsoft runtime DLLs.' }
        $code = Run-Process (Join-Path $installed 'unins000.exe') '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
        if ($code -ne 0 -or (Test-Path (Join-Path $installed 'CactuVideoConverter.exe'))) { throw 'Uninstallation failed.' }
        $receipt.uninstall = 'PASS'
    }
    $receipt.system_dll_versions = $versions
    $receipt.result = 'PASS'
    $name = if ($Phase -eq 'Missing') { 'runtime-missing.json' } else { 'runtime-installed.json' }
    $receipt | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 (Join-Path $EvidenceFolder $name)
    Write-Host "PASS: $Phase. Evidence saved. Microsoft runtime installation was not automated."
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force
}
