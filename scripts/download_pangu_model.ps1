param(
  [string]$ModelId = "openpangu/openPangu-Embedded-7B-model",
  [string]$LocalDir = "models/openPangu-Embedded-7B-model"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path (Split-Path $LocalDir -Parent) | Out-Null

Write-Host "Installing Git LFS hooks..."
git lfs install

if (Test-Path $LocalDir) {
  Write-Host "Model directory already exists: $LocalDir"
  Write-Host "Pulling latest files..."
  git -C $LocalDir lfs pull
} else {
  Write-Host "Cloning $ModelId into $LocalDir"
  git clone "https://huggingface.co/$ModelId" $LocalDir
}

Write-Host "Done."

