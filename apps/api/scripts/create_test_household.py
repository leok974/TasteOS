"""
Create a test household for the dev user.
"""
import asyncio
from sqlalchemy import select
from tasteos_api.core.database import engine
from sqlmodel.ext.asyncio.session import AsyncSession
from tasteos_api.models.user import User
from tasteos_api.models.household import Household, HouseholdMembership

async def main():
    async with AsyncSession(engine) as session:
        # Find the dev user
        result = await session.execute(
            select(User).where(User.email == "dev@tasteos.local")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("❌ User dev@tasteos.local not found")
            return

        print(f"✓ Found user: {user.email} (ID: {user.id})")

        # Check if user already has a household
        result = await session.execute(
            select(HouseholdMembership).where(HouseholdMembership.user_id == user.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✓ User already has a household membership: {existing.household_id}")
            return

        # Create a new household
        household = Household(
            name="Dev Household",
            owner_id=user.id
        )
        session.add(household)
        await session.flush()

        print(f"✓ Created household: {household.name} (ID: {household.id})")

        # Create membership
        membership = HouseholdMembership(
            household_id=household.id,
            user_id=user.id,
            role="owner"
        )
        session.add(membership)

        await session.commit()
        print(f"✓ Added user as owner of household")
        print(f"\nHousehold ID: {household.id}")

if __name__ == "__main__":
    asyncio.run(main())
