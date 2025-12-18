import asyncio
import uuid
import sys
import os

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete

from app.core.config import settings
from app.models.employee import Employee, DirectoryGroup, employee_groups
from app.models.organization import Organization
from app.models.booking import Booking, BookingTraveler
from app.models.approval import ApprovalRequest

# FORCE CORRECT PORT from config or hardcode valid one
# settings.DATABASE_URL should be correct based on previous view_file
DATABASE_URL = settings.DATABASE_URL
print(f"Connecting to {DATABASE_URL}")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def setup():
    async with AsyncSessionLocal() as session:
        print("Cleaning up old data...")
        await session.execute(delete(ApprovalRequest))
        await session.execute(delete(BookingTraveler))
        await session.execute(delete(Booking))
        await session.execute(delete(employee_groups))
        await session.execute(delete(Employee))
        await session.execute(delete(DirectoryGroup))
        await session.execute(delete(Organization))
        await session.commit()
        
        print("Creating Organization...")
        org = Organization(name="Acme Corp")
        session.add(org)
        await session.flush()
        
        print("Creating Groups...")
        g_emp = DirectoryGroup(
            org_id=org.id, 
            name="employee", 
            external_group_id="grp_emp"
        )
        g_mgr = DirectoryGroup(
            org_id=org.id, 
            name="manager", 
            external_group_id="grp_mgr"
        )
        session.add_all([g_emp, g_mgr])
        await session.flush()
        
        print("Creating Employees...")
        # Bob - Manager
        bob = Employee(
            org_id=org.id,
            email="bob@corporate.com",
            full_name="Bob Manager",
            first_name="Bob",
            last_name="Manager",
            status="active"
        )
        session.add(bob)
        await session.flush()
        
        # Add Bob to manager group
        await session.execute(
            employee_groups.insert().values(employee_id=bob.id, group_id=g_mgr.id)
        )
        
        # Alice - Employee (reports to Bob)
        alice = Employee(
            org_id=org.id,
            email="alice@corporate.com",
            full_name="Alice Employee",
            first_name="Alice",
            last_name="Employee",
            status="active",
            manager_id=bob.id
        )
        session.add(alice)
        await session.flush()
        
        # Add Alice to employee group
        await session.execute(
            employee_groups.insert().values(employee_id=alice.id, group_id=g_emp.id)
        )
        
        # Charlie - Employee (Self-manager case - though logic prevents managing self, we need someone without manager to test error or someone managing themselves if we want to catch that bug)
        # Let's make Charlie report to himself to test "Self-Approval Block" strongly? 
        # Or simply test user trying to approve their own booking even if they are a manager.
        # Let's make Charlie a Manager who reports to Bob, but we will test him trying to approve his OWN booking.
        charlie = Employee(
            org_id=org.id,
            email="charlie@corporate.com",
            full_name="Charlie Lead",
            first_name="Charlie",
            last_name="Lead",
            status="active",
            manager_id=bob.id 
        )
        session.add(charlie)
        await session.flush()
        
        # Make Charlie a manager too (so he has access to inbox)
        await session.execute(
            employee_groups.insert().values(employee_id=charlie.id, group_id=g_mgr.id)
        )

        # Dave - Self Managing (for testing edge case)
        dave = Employee(
            org_id=org.id,
            email="dave@corporate.com",
            full_name="Dave Self",
            first_name="Dave",
            last_name="Self",
            status="active"
        )
        session.add(dave)
        await session.flush()
        dave.manager_id = dave.id
        session.add(dave)
        
        # Dave needs manager group to access approve endpoint
        await session.execute(
            employee_groups.insert().values(employee_id=dave.id, group_id=g_mgr.id)
        )

        await session.commit()
        print("Setup Complete.")

if __name__ == "__main__":
    asyncio.run(setup())
