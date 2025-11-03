# Quick Start Guide

## Complete Setup in 5 Steps

### 1. Backend Setup (Terminal 1)

```bash
# Create and activate virtual environment
python -m venv .venv
. .venv/Scripts/Activate.ps1  # Windows PowerShell
# OR: source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start backend server
python run_server.py
```

Backend runs on: **http://localhost:8000**

### 2. Frontend Setup (Terminal 2)

```bash
cd frontend

# Install dependencies
npm install

# Start frontend server
npm run dev
```

Frontend runs on: **http://localhost:3000**

### 3. Open Browser

Navigate to: **http://localhost:3000**

### 4. First Steps

1. **Team Management**: Add your team members
   - Click "Team" in navigation
   - Click "Add Member"
   - Fill in name, ID, and select office days
   - Save

2. **Add Unavailability**: Mark vacation/training periods
   - Click calendar icon next to a member
   - Add start/end dates and reason
   - Save

3. **Generate Schedule**: Create your first schedule
   - Click "Generate" in navigation
   - Select date range (defaults to next week)
   - Click "Generate Schedule"
   - View the schedule

4. **Check Fairness**: Monitor assignment distribution
   - Click "Fairness" in navigation
   - View visual representation of assignments

### 5. Verify Everything Works

- ✅ Backend API: http://localhost:8000/docs (interactive API docs)
- ✅ Frontend UI: http://localhost:3000 (main application)
- ✅ Database: `task_scheduler.db` file created in project root

## Troubleshooting

**Backend won't start?**
- Check Python version: `python --version` (need 3.8+)
- Check if port 8000 is available
- Run `python init_db.py` first

**Frontend won't start?**
- Check Node.js version: `node --version` (need 16+)
- Delete `frontend/node_modules` and run `npm install` again
- Check if port 3000 is available

**Database errors?**
- Delete `task_scheduler.db` and run `python init_db.py` again

**CORS errors?**
- Make sure backend is running on port 8000
- Check `task_scheduler/api.py` CORS settings

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8000/docs
- Customize configuration in `data/config.yaml`

