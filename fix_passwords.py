"""Script to fix invalid password hashes in the database."""

from dotenv import load_dotenv
load_dotenv()

from task_scheduler.database import db
from task_scheduler.api import get_password_hash
from sqlalchemy.orm import Session

def fix_passwords():
    """Check and fix password hashes in the database."""
    session = db.get_session()
    try:
        from task_scheduler.database import User
        
        users = session.query(User).all()
        print(f"Found {len(users)} users in database")
        
        fixed_count = 0
        for user in users:
            if not user.password_hash:
                print(f"User '{user.username}' has no password hash - skipping")
                continue
            
            # Check if password_hash is a valid bcrypt hash
            if not user.password_hash.startswith(('$2a$', '$2b$', '$2y$', '$2x$')):
                print(f"User '{user.username}' has invalid password hash format")
                print(f"  Current hash: {user.password_hash[:50]}...")
                print(f"  Length: {len(user.password_hash)} bytes")
                
                # If it's longer than 72 bytes, it might be a plain password
                if len(user.password_hash.encode('utf-8')) > 72:
                    print(f"  WARNING: Password hash is longer than 72 bytes!")
                    print(f"  This might be a plain password stored by mistake.")
                    print(f"  You need to reset this user's password manually.")
                    print(f"  Use the /api/auth/register endpoint or update the database directly.")
                else:
                    # Try to re-hash it (if it's a short plain password)
                    print(f"  Attempting to re-hash...")
                    try:
                        # If it's a plain password, hash it
                        new_hash = get_password_hash(user.password_hash)
                        user.password_hash = new_hash
                        session.commit()
                        print(f"  ✅ Fixed: Re-hashed password")
                        fixed_count += 1
                    except Exception as e:
                        print(f"  ❌ Failed to re-hash: {e}")
                        session.rollback()
            else:
                # Valid bcrypt hash
                hash_bytes = len(user.password_hash.encode('utf-8'))
                print(f"User '{user.username}' has valid bcrypt hash ({hash_bytes} bytes)")
        
        print(f"\nFixed {fixed_count} password(s)")
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Password Hash Fixer")
    print("=" * 60)
    fix_passwords()

