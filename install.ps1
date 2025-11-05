Write-Host "Setting up virtual environment and installing dependencies..." -ForegroundColor Cyan

# Create venv if it does not exist
if (-Not (Test-Path ".venv")) {
  python -m venv .venv
}

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Upgrade pip and install deps
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Done. Next time, just run: .\\run.ps1" -ForegroundColor Green


