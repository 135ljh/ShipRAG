param(
  [switch]$All,
  [int]$Limit = 0,
  [switch]$ClearNeo4j
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

if (!(Test-Path "pangu\.env")) {
  Copy-Item "pangu\config.example.env" "pangu\.env"
  Write-Host "Created pangu\.env from template. Please edit Neo4j credentials if needed."
}

$extractArgs = @("pangu\extract_triples.py")
if ($All) {
  $extractArgs += "--all"
}
if ($Limit -gt 0) {
  $extractArgs += @("--limit", "$Limit")
}

python @extractArgs
python pangu\build_graph_data.py

if ($ClearNeo4j) {
  python pangu\import_neo4j.py --clear
} else {
  python pangu\import_neo4j.py
}

