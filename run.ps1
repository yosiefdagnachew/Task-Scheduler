param(
  [int]$Port = 8000
)

if (-Not (Test-Path ".venv")) {
  Write-Host "Virtual env not found. Run .\\install.ps1 first." -ForegroundColor Yellow
  exit 1
}

. .\.venv\Scripts\Activate.ps1

$env:PORT=$Port
python run_server.py


