param(
    [Parameter(Mandatory=$true)][string]$ArtifactFolder,
    [Parameter(Mandatory=$true)][string]$EvidenceFolder,
    [string]$OutputFile = '.\Cactu-Runtime-Validation.wsb'
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $EvidenceFolder | Out-Null
function Escape([string]$Path) { return [Security.SecurityElement]::Escape((Resolve-Path -LiteralPath $Path).Path) }
$artifacts = Escape $ArtifactFolder
$evidence = Escape $EvidenceFolder
$scripts = Escape $PSScriptRoot
@"
<Configuration>
  <Networking>Disable</Networking>
  <VGpu>Disable</VGpu>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <MappedFolders>
    <MappedFolder><HostFolder>$artifacts</HostFolder><SandboxFolder>C:\CactuArtifacts</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>$scripts</HostFolder><SandboxFolder>C:\CactuScripts</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>$evidence</HostFolder><SandboxFolder>C:\CactuEvidence</SandboxFolder><ReadOnly>false</ReadOnly></MappedFolder>
  </MappedFolders>
</Configuration>
"@ | Set-Content -Encoding UTF8 $OutputFile
Write-Host 'Open the WSB on an eligible Windows 11 host, or use a separate clean x64 VM.'
Write-Host 'Run Test-CleanWindowsRuntime.ps1 -Phase Missing first. Install the official prerequisite interactively yourself, then run -Phase Installed in the SAME guest.'
Write-Host 'Obtain the official installer separately beforehand; this helper never downloads or runs it.'
