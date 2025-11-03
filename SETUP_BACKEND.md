# Backend Setup Instructions

## Python Installation Required

The backend requires Python 3.8+. You need to install Python first.

### Install Python (Windows)

**Option 1: Using winget (Recommended)**
```powershell
winget install -e --id Python.Python.3.11
```

**Option 2: Download from python.org**
1. Visit https://www.python.org/downloads/
2. Download Python 3.11.x for Windows
3. Run installer
4. ✅ Check "Add Python to PATH" during installation

**Option 3: Using Chocolatey**
```powershell
choco install python --version=3.11.9 -y
```

### Disable Microsoft Store Python Alias

1. Open Windows Settings (Win + I)
2. Go to: Apps → Advanced app settings → App execution aliases
3. Turn OFF "App installer" for Python

### Verify Python Installation

```powershell
python --version
# Should show: Python 3.11.x or similar

py --version
# Alternative command
```

## Backend Setup Steps

Once Python is installed, run these commands:

```powershell
# Navigate to project directory
cd "E:\task scheduler"

# Create virtual environment
python -m venv .venv

# Activate virtual environment (PowerShell)
. .\.venv\Scripts\Activate.ps1

# If activation fails, allow scripts:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start backend server
python run_server.py
```

The backend will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Troubleshooting

**"Python was not found"**
- Python is not installed or not in PATH
- Reinstall Python and check "Add to PATH"
- Restart PowerShell after installation

**"Activate.ps1 cannot be loaded"**
- Run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Then try activation again

**"Module not found" errors**
- Make sure virtual environment is activated (you'll see `(.venv)` in prompt)
- Run: `pip install -r requirements.txt` again

**Port 8000 already in use**
- Change port in `run_server.py`: `port=8001`
- Or stop the process using port 8000

