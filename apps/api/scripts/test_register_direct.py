"""
Test registration by directly calling the endpoint and catching detailed errors.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from tasteos_api.models.user import User, UserCreate
from tasteos_api.core.auth import get_password_hash
from tasteos_api.core.database import get_db_session, engine
from sqlmodel import select

async def test_register():
    """Test user registration with detailed error output."""
    print("Testing user registration...")
    
    try:
        user_data = UserCreate(
            email="test@example.com",
            password="test123",
            name="Test User",
            is_active=True,
            plan="free",
            subscription_status="active"
        )
        
        print(f"UserCreate data: {user_data}")
        print(f"Fields: {user_data.model_dump()}")
        
        # Create user object
        hashed_password = get_password_hash(user_data.password)
        print(f"Password hashed successfully")
        
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
            plan=user_data.plan,
            is_active=user_data.is_active,
            subscription_status=user_data.subscription_status,
        )
        
        print(f"User object created: {db_user}")
        print(f"User fields: {db_user.model_dump()}")
        
        # Try to save to database
        async for session in get_db_session():
            # Check if user exists
            result = await session.execute(
                select(User).where(User.email == user_data.email)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"✗ User already exists: {existing.email}")
                return
            
            print("Adding user to session...")
            session.add(db_user)
            
            print("Committing...")
            await session.commit()
            
            print("Refreshing...")
            await session.refresh(db_user)
            
            print(f"✓ User created successfully!")
            print(f"  ID: {db_user.id}")
            print(f"  Email: {db_user.email}")
            print(f"  Name: {db_user.name}")
            break
            
    except Exception as e:
        print(f"\n✗ Error occurred:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_register())
