# Troubleshooting Guide

## Issue: Backend and Frontend Running But No Data Displayed

### Step 1: Check Backend is Running
1. Open browser and go to: **http://localhost:8000/docs**
2. You should see the FastAPI interactive documentation
3. If you see an error, check the backend terminal for error messages

### Step 2: Check Database Configuration
The most common issue is missing `DATABASE_URL` environment variable.

**Solution:**
1. Create a `.env` file in the project root (`E:\task_scheduler\.env`)
2. Add one of these lines:

   **For SQLite (easiest):**
   ```
   DATABASE_URL=sqlite:///./task_scheduler.db
   ```

   **For PostgreSQL:**
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/iss_task_schedule
   ```

3. Restart the backend server

### Step 3: Initialize Database
If the database is empty or not initialized:

```bash
python init_db.py
```

This will:
- Create all database tables
- Optionally load team members from `data/team.yaml` if it exists

### Step 4: Check Frontend Port
The frontend should be running on **http://localhost:3000** (as configured in `vite.config.js`)

If Vite is running on a different port (like 5173), you have two options:

**Option A: Use the port Vite shows**
- Check the terminal where you ran `npm run dev`
- It will show something like: `Local: http://localhost:5173/`
- Use that URL instead

**Option B: Force port 3000**
- Stop the frontend (Ctrl+C)
- Make sure port 3000 is not in use
- Restart: `npm run dev`

### Step 5: Check Browser Console
1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Look for errors like:
   - `Network Error` - Backend not reachable
   - `401 Unauthorized` - Need to login
   - `500 Internal Server Error` - Backend error
   - `CORS error` - Port mismatch

### Step 6: Test API Connection
1. Open browser and go to: **http://localhost:8000/api/health**
2. You should see: `{"status": "healthy", "database": "connected"}`
3. If you see an error, check the backend terminal

### Step 7: Check Authentication
Most endpoints require authentication. If you're not logged in:

1. Go to: **http://localhost:3000/login**
2. If no users exist, create one:
   - Go to: **http://localhost:8000/docs**
   - Find `/api/auth/register` endpoint
   - Click "Try it out"
   - Enter username, password, role (e.g., "admin")
   - Click "Execute"
3. Then login with those credentials

### Step 8: Verify Proxy is Working
The frontend uses a proxy to connect to the backend. Check `frontend/vite.config.js`:

```js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

If the frontend is on a different port, make sure the proxy target is correct.

### Common Errors and Solutions

**Error: "DATABASE_URL is not set"**
- Solution: Create `.env` file with `DATABASE_URL=sqlite:///./task_scheduler.db`

**Error: "Cannot connect to backend server"**
- Check backend is running: `http://localhost:8000/docs`
- Check backend terminal for errors
- Verify port 8000 is not blocked by firewall

**Error: "401 Unauthorized"**
- You need to login first
- Go to `/login` page
- Or create a user via `/api/auth/register`

**Error: "Network Error" or "ECONNREFUSED"**
- Backend is not running or not accessible
- Check backend terminal
- Verify backend is on port 8000
- Check firewall settings

**Error: "CORS policy"**
- Frontend and backend ports don't match CORS settings
- Backend allows: `http://localhost:3000` and `http://localhost:5173`
- Make sure frontend is on one of these ports

### Quick Diagnostic Commands

**Check if backend is responding:**
```powershell
curl http://localhost:8000/api/health
# Or in browser: http://localhost:8000/api/health
```

**Check if database file exists (SQLite):**
```powershell
Test-Path task_scheduler.db
```

**Check backend logs:**
- Look at the terminal where you ran `python run_server.py`
- Should show: "Uvicorn running on http://127.0.0.1:8000"
- Should show: "Database initialized successfully"

**Check frontend logs:**
- Look at the terminal where you ran `npm run dev`
- Should show: "Local: http://localhost:3000/"
- Check browser console (F12) for errors

