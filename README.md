# Task Scheduler System (ATM & SysAid)

A comprehensive, fair, auditable task scheduling system with interactive web UI for operational tasks:
- **ATM monitoring (daily)**: Morning reporter (A) and Mid-day+Night reporter (B) with rest rule for B.
- **SysAid monitoring (weekly)**: Maker/Checker pair with fairness and office-presence checks.

## Features

### Core Functionality
- ✅ **Fairness**: Equal assignment distribution across team members over rolling window
- ✅ **Rest Rules**: Automatic rest day assignment after B-shift (configurable)
- ✅ **Office Presence Check**: SysAid assignees must be in office for all days of their week
- ✅ **Unavailability Handling**: Respects vacation, training, and sick leave
- ✅ **Cooldown Rules**: Prevents consecutive heavy shifts (B-shift cooldown)
- ✅ **Audit Trail**: Complete log of assignment decisions and tie-breaks

### Interactive Web UI
- 🎨 **Modern React Frontend**: Beautiful, responsive interface
- 📊 **Dashboard**: Overview of schedules and team
- 👥 **Team Management**: Add/edit members, manage availability
- 📅 **Schedule Generator**: Generate schedules with date picker
- 📋 **Schedule View**: Visual calendar view of assignments
- 📈 **Fairness Tracking**: Visual representation of assignment distribution

### Backend & Database
- 🚀 **FastAPI Backend**: Modern, fast REST API
- 💾 **SQLite Database**: Persistent storage (easily upgradeable to PostgreSQL)
- 🔄 **Real-time Updates**: Live data synchronization

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+ and npm

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
. .venv/Scripts/Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start backend server
python run_server.py
# Or: uvicorn task_scheduler.api:app --reload --port 8000
```

Backend will be available at: http://localhost:8000
API docs at: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## Quick Start

1. **Start Backend**:
   ```bash
   python run_server.py
   ```

2. **Start Frontend** (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open Browser**: Navigate to http://localhost:3000

4. **Initialize Database** (first time only):
   ```bash
   python init_db.py
   ```

## Usage

### Web UI

1. **Dashboard**: View recent schedules and statistics
2. **Team Management**: 
   - Add team members
   - Set office days
   - Add unavailable periods (vacation, training, etc.)
3. **Generate Schedule**: 
   - Select date range
   - Click "Generate Schedule"
   - View and export schedule
4. **Fairness View**: Track assignment distribution across team

### CLI (Alternative)

```bash
# Generate schedule via CLI
python -m task_scheduler.cli generate \
  --team data/team.yaml \
  --config data/config.yaml \
  --start 2025-11-03 \
  --out out/schedule.csv
```

## Project Structure

```
task scheduler/
├── task_scheduler/          # Python package
│   ├── api.py              # FastAPI backend
│   ├── database.py         # Database models
│   ├── scheduler.py        # Core scheduling logic
│   ├── models.py           # Data models
│   ├── config.py           # Configuration
│   ├── loader.py           # Data loading
│   ├── export.py           # Export functionality
│   └── cli.py              # CLI interface
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   └── services/       # API services
│   └── package.json
├── data/                   # Configuration files
│   ├── config.yaml
│   └── team.yaml
├── out/                    # Output files
├── task_scheduler.db       # SQLite database
├── requirements.txt        # Python dependencies
└── README.md
```

## API Endpoints

- `GET /api/team-members` - List all team members
- `POST /api/team-members` - Create team member
- `PUT /api/team-members/{id}` - Update team member
- `DELETE /api/team-members/{id}` - Delete team member
- `POST /api/unavailable-periods` - Add unavailable period
- `POST /api/schedules/generate` - Generate new schedule
- `GET /api/schedules` - List all schedules
- `GET /api/schedules/{id}` - Get schedule details
- `GET /api/fairness` - Get fairness counts
- `GET /api/config` - Get configuration

See http://localhost:8000/docs for interactive API documentation.

## Configuration

### Backend Configuration (`data/config.yaml`)
```yaml
timezone: "Africa/Addis_Ababa"
fairness_window_days: 90
atm:
  rest_rule_enabled: true
  b_cooldown_days: 2
```

### Database

The system uses SQLite by default. To use PostgreSQL:

1. Update `task_scheduler/database.py`:
   ```python
   db = Database("postgresql://user:password@localhost/task_scheduler")
   ```

2. Install PostgreSQL adapter:
   ```bash
   pip install psycopg2-binary
   ```

## Operational Rules

### ATM Monitoring Rules
- **Daily roles**: Two assigned per day (A = Morning, B = Mid-day+Night)
- **Rest rule**: B-shift assignee gets next calendar day off
- **No double duty**: Same person cannot be both A and B on same day
- **Cooldown**: Minimum days between B-shift assignments (configurable)

### SysAid Monitoring Rules
- **Weekly pair**: Maker and Checker assigned for entire week (Mon-Sun)
- **Office presence**: Both must be in office (not resting/unavailable) for all days
- **Distinct roles**: Maker ≠ Checker
- **Fairness**: Equal rotation of maker/checker roles over time

## Development

### Backend Development
```bash
# Run with auto-reload
uvicorn task_scheduler.api:app --reload --port 8000
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Database Migrations
Currently using SQLAlchemy's `create_all()`. For production, consider using Alembic:
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Notes

- All times default to `Africa/Addis_Ababa` timezone (configurable)
- Rest rule can be disabled in configuration
- SysAid assignees are validated for office presence across entire week
- System handles edge cases (insufficient members, conflicts) with warnings
- Database is automatically initialized on first API startup

## Troubleshooting

- **Database errors**: Run `python init_db.py` to initialize
- **CORS errors**: Check that backend allows frontend origin in `api.py`
- **Port conflicts**: Change ports in `run_server.py` and `frontend/vite.config.js`
