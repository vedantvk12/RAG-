import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.db.models import User, Membership, Organization

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "demo@example.com"))
        user = result.scalars().first()
        print("User:", user.id)
        
        result2 = await session.execute(select(Membership).where(Membership.user_id == user.id))
        memberships = result2.scalars().all()
        print("Memberships for user:", memberships)
        
        result3 = await session.execute(select(Membership))
        all_memberships = result3.scalars().all()
        print("All memberships in DB:", [(m.user_id, m.org_id) for m in all_memberships])
        
        result4 = await session.execute(select(Organization))
        orgs = result4.scalars().all()
        print("All orgs in DB:", [o.id for o in orgs])
        
        if not memberships and orgs:
            # Create a membership
            print("Creating membership...")
            m = Membership(user_id=user.id, org_id=orgs[0].id, role="admin")
            session.add(m)
            await session.commit()
            print("Created membership!")

if __name__ == "__main__":
    asyncio.run(main())
