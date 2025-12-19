[CmdletBinding()]
param(
  [string]$StandardsRoot = "C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Standards",
  [string]$IncomingDir = "C:\_Sandbox\incoming_json",
  [switch]$CopyOnly
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }
}

function Ensure-TextFile([string]$Path, [string]$Content) {
  if (-not (Test-Path -LiteralPath $Path)) {
    $dir = Split-Path -Path $Path -Parent
    Ensure-Dir $dir
    New-Item -ItemType File -Path $Path -Value $Content | Out-Null
  }
}

function Place-Json([string]$FileName, [string]$DestPath) {
  $src = Join-Path $IncomingDir $FileName
  if (-not (Test-Path -LiteralPath $src)) {
    Write-Host "Missing: $src"
    return
  }
  $destDir = Split-Path -Path $DestPath -Parent
  Ensure-Dir $destDir
  if ($CopyOnly) {
    Copy-Item -LiteralPath $src -Destination $DestPath -Force
  } else {
    Move-Item -LiteralPath $src -Destination $DestPath -Force
  }
  Write-Host "Placed: $FileName -> $DestPath"
}

$cadRoot   = Join-Path $StandardsRoot "CAD\DataDictionary"
$rmsRoot   = Join-Path $StandardsRoot "RMS\DataDictionary"
$crossRoot = Join-Path $StandardsRoot "CAD_RMS\DataDictionary"

$dirs = @(
  "$cadRoot\current\schema", "$cadRoot\current\defaults", "$cadRoot\current\domains",
  "$cadRoot\archive", "$cadRoot\templates", "$cadRoot\scripts",
  "$rmsRoot\current\schema", "$rmsRoot\current\defaults", "$rmsRoot\current\domains",
  "$rmsRoot\archive", "$rmsRoot\templates", "$rmsRoot\scripts",
  "$crossRoot\current\schema", "$crossRoot\archive", "$crossRoot\scripts"
)

$dirs | ForEach-Object { Ensure-Dir $_ }

$readme = @"
DataDictionary

Purpose
- Store field maps, schemas, defaults, and domain lists for CAD and RMS exports.
- Store cross-system merge policy for CAD + RMS ETL.

Folders
- current\schema: field maps, field schema, merge policy
- current\defaults: per-field default rules
- current\domains: per-field allowed values
- archive: dated snapshots
"@

$summary = @"
Status
- Structure initialized.
- Place the latest JSON files into schema folders.
"@

$changelog = @"
CHANGELOG

Unreleased
- Initial scaffolding.
"@

Ensure-TextFile (Join-Path $cadRoot   "README.md")    $readme
Ensure-TextFile (Join-Path $cadRoot   "SUMMARY.md")   $summary
Ensure-TextFile (Join-Path $cadRoot   "CHANGELOG.md") $changelog

Ensure-TextFile (Join-Path $rmsRoot   "README.md")    $readme
Ensure-TextFile (Join-Path $rmsRoot   "SUMMARY.md")   $summary
Ensure-TextFile (Join-Path $rmsRoot   "CHANGELOG.md") $changelog

Ensure-TextFile (Join-Path $crossRoot "README.md")    $readme
Ensure-TextFile (Join-Path $crossRoot "SUMMARY.md")   $summary
Ensure-TextFile (Join-Path $crossRoot "CHANGELOG.md") $changelog

Place-Json "cad_field_map_latest.json"             "$cadRoot\current\schema\cad_field_map.json"
Place-Json "cad_fields_schema_latest.json"         "$cadRoot\current\schema\cad_fields_schema.json"

Place-Json "rms_field_map_latest.json"             "$rmsRoot\current\schema\rms_field_map.json"
Place-Json "rms_fields_schema_latest.json"         "$rmsRoot\current\schema\rms_fields_schema.json"

Place-Json "cad_to_rms_field_map_latest.json"      "$crossRoot\current\schema\cad_to_rms_field_map.json"
Place-Json "rms_to_cad_field_map_latest.json"      "$crossRoot\current\schema\rms_to_cad_field_map.json"
Place-Json "cad_rms_merge_policy_latest.json"      "$crossRoot\current\schema\cad_rms_merge_policy.json"

Write-Host "Done."
