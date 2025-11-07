# How to Seed the Database

This guide explains how to seed the database with team members from the YAML file.

## Prerequisites

1. Make sure your `.env` file is configured with `DATABASE_URL`
2. Ensure the virtual environment is activated
3. Make sure `data/team.yaml` exists with your team members

## Steps to Seed Database

### Option 1: Using Python directly

```powershell
# Activate virtual environment (if not already activated)
.\.venv\Scripts\Activate.ps1

# Run the init script
python init_db.py
```

### Option 2: Using PowerShell script

```powershell
# From the project root
python init_db.py
```

## What the Script Does

1. **Creates database tables** (if they don't exist)
2. **Loads team members** from `data/team.yaml`
3. **Creates user accounts** for each team member with:
   - Username: Same as member ID
   - Password: Randomly generated (displayed in console)
   - Role: "member"
   - Must change password: Yes (forced on first login)
4. **Adds unavailable periods** if specified in YAML
5. **Skips existing members** (won't duplicate)

## Output

The script will display:
- Each member added with their temporary password
- Summary of added/skipped members
- Any errors encountered

## Example Output

```
Creating database tables...
Loading team members from YAML...
  Added member: Yosief Dagnachew (ZB/ISS/101) - Password: aB3$kL9mN2
  Added member: Temesegen Abate (ZB/ISS/102) - Password: xY7#pQ4rS8
  ...

Database initialized!
  - Added: 12 new team members
  - Skipped: 0 existing members
  - Total: 12 team members

Note: User accounts have been created with temporary passwords.
      Members should change their passwords on first login.
```

## Important Notes

- **Passwords are displayed in the console** - save them securely!
- Members must change their password on first login
- If a member already exists, it will be skipped (won't overwrite)
- The script is safe to run multiple times (idempotent)

## Troubleshooting

### Error: "data/team.yaml not found"
- Make sure the `data/team.yaml` file exists
- Check that you're running from the project root directory

### Error: Database connection failed
- Check your `.env` file has the correct `DATABASE_URL`
- Ensure PostgreSQL is running
- Verify database credentials

### Members not appearing
- Check the console output for errors
- Verify the YAML file format is correct
- Check database connection

