"""Initialize the database with sample data."""

from task_scheduler.database import db, TeamMemberDB, UnavailablePeriod
from datetime import date
from task_scheduler.loader import load_team
from dotenv import load_dotenv

load_dotenv()

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
        
        for member in members:
            # Check if member already exists
            existing = session.query(TeamMemberDB).filter(TeamMemberDB.id == member.id).first()
            if existing:
                print(f"  Member {member.name} already exists, skipping...")
                continue
            
            db_member = TeamMemberDB(
                id=member.id,
                name=member.name,
                office_days=member.office_days
            )
            session.add(db_member)
            
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
            
            print(f"  Added member: {member.name}")
        
        session.commit()
        session.close()
        
        print(f"\nDatabase initialized with {len(members)} team members!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("Continuing without YAML data...")

if __name__ == "__main__":
    init_database()

