"""Initialize the database with sample data."""

# IMPORTANT: Load .env BEFORE importing database module
from dotenv import load_dotenv
load_dotenv()

from task_scheduler.database import db, TeamMemberDB, UnavailablePeriod, User
from datetime import date
from task_scheduler.loader import load_team
from passlib.context import CryptContext
import secrets
import string

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def generate_password(length: int = 10) -> str:
    """Generate a random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def init_database():
    """Initialize database with team members from YAML."""
    print("Creating database tables...")
    db.create_tables()
    
    print("Loading team members from YAML...")
    try:
        members = load_team("data/team.yaml")
        session = db.get_session()
        
        # Clear existing data (optional - comment out if you want to keep existing data)
        # session.query(UnavailablePeriod).delete()
        # session.query(TeamMemberDB).delete()
        
        added_count = 0
        skipped_count = 0
        
        for member in members:
            # Check if member already exists
            existing = session.query(TeamMemberDB).filter(TeamMemberDB.id == member.id).first()
            if existing:
                print(f"  Member {member.name} ({member.id}) already exists, skipping...")
                skipped_count += 1
                continue
            
            db_member = TeamMemberDB(
                id=member.id,
                name=member.name,
                office_days=member.office_days,
                email=getattr(member, 'email', None)  # Support email if in YAML
            )
            session.add(db_member)
            
            # Create user account for this member
            temp_password = generate_password()
            user = User(
                username=member.id,
                password_hash=get_password_hash(temp_password),
                role="member",
                member_id=member.id,
                must_change_password=True,
                email=getattr(member, 'email', None)
            )
            session.add(user)
            print(f"  Added member: {member.name} ({member.id}) - Password: {temp_password}")
            
            # Add unavailable dates
            for unavailable_date in member.unavailable_dates:
                period = UnavailablePeriod(
                    member_id=member.id,
                    start_date=unavailable_date,
                    end_date=unavailable_date,
                    reason="Unavailable"
                )
                session.add(period)
            
            # Add unavailable ranges
            for start, end in member.unavailable_ranges:
                period = UnavailablePeriod(
                    member_id=member.id,
                    start_date=start,
                    end_date=end,
                    reason="Unavailable range"
                )
                session.add(period)
            
            added_count += 1
        
        session.commit()
        session.close()
        
        print(f"\nDatabase initialized!")
        print(f"  - Added: {added_count} new team members")
        print(f"  - Skipped: {skipped_count} existing members")
        print(f"  - Total: {len(members)} team members")
        print("\nNote: User accounts have been created with temporary passwords.")
        print("      Members should change their passwords on first login.")
    except FileNotFoundError:
        print("Warning: data/team.yaml not found. Skipping team member seeding.")
        print("You can add team members manually through the web interface.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        print("Continuing without YAML data...")

if __name__ == "__main__":
    init_database()

