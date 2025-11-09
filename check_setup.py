"""Quick diagnostic script to check if the setup is correct."""

import os
from pathlib import Path

print("=" * 60)
print("Task Scheduler Setup Diagnostic")
print("=" * 60)

# Check .env file
env_path = Path(".env")
if env_path.exists():
    print("✅ .env file exists")
    with open(env_path) as f:
        content = f.read()
        if "DATABASE_URL" in content:
            print("✅ DATABASE_URL found in .env")
            # Don't print the actual URL for security
            for line in content.splitlines():
                if "DATABASE_URL" in line and not line.strip().startswith("#"):
                    print(f"   {line.split('=')[0]} is set")
        else:
            print("❌ DATABASE_URL not found in .env")
            print("   Add: DATABASE_URL=sqlite:///./task_scheduler.db")
else:
    print("❌ .env file NOT found")
    print("   Creating .env file with SQLite configuration...")
    with open(env_path, "w") as f:
        f.write("DATABASE_URL=sqlite:///./task_scheduler.db\n")
    print("   ✅ Created .env file")

# Check database file (if SQLite)
db_path = Path("task_scheduler.db")
if db_path.exists():
    print(f"✅ Database file exists: {db_path}")
    size = db_path.stat().st_size
    print(f"   Size: {size:,} bytes")
else:
    print("⚠️  Database file not found (will be created on first run)")

# Check if backend can import
print("\nChecking backend imports...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv loaded")
    
    from task_scheduler.database import db
    print("✅ Database module imported")
    
    # Try to get a session (this will initialize the database)
    try:
        session = db.get_session()
        print("✅ Database connection successful")
        session.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Check your DATABASE_URL in .env file")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Run: pip install -r requirements.txt")

# Check frontend
print("\nChecking frontend...")
frontend_path = Path("frontend")
if frontend_path.exists():
    print("✅ frontend directory exists")
    
    package_json = frontend_path / "package.json"
    if package_json.exists():
        print("✅ package.json exists")
    else:
        print("❌ package.json not found")
    
    node_modules = frontend_path / "node_modules"
    if node_modules.exists():
        print("✅ node_modules exists (dependencies installed)")
    else:
        print("⚠️  node_modules not found")
        print("   Run: cd frontend && npm install")
else:
    print("❌ frontend directory not found")

print("\n" + "=" * 60)
print("Diagnostic complete!")
print("=" * 60)
print("\nNext steps:")
print("1. If .env was created, restart the backend server")
print("2. If database connection failed, check DATABASE_URL in .env")
print("3. If frontend dependencies missing, run: cd frontend && npm install")
print("4. Start backend: python run_server.py")
print("5. Start frontend: cd frontend && npm run dev")
print("6. Open browser: http://localhost:3000")

