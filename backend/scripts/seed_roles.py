#!/usr/bin/env python3
"""
Seed script to create default system role templates.

Run with: python -m scripts.seed_roles
"""

import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.organization import Organization
from app.models.role_template import RoleTemplate, AccessScope


# Default system role templates
DEFAULT_ROLES = [
    {
        "name": "Employee",
        "description": "Standard employee with basic travel booking capabilities",
        "is_system": True,
        "default_access_scope": AccessScope.SELF,
        "permissions": {
            "book_flights": True,
            "book_hotels": True,
            "book_ground": True,
            "economy_class": True,
            "premium_economy_class": False,
            "business_class": False,
            "first_class": False,
            "view_own_bookings": True,
            "view_team_bookings": False,
            "view_all_bookings": False,
            "approve_travel": False,
            "approve_expenses": False,
            "override_policy": False,
            "view_analytics": False,
            "manage_policies": False,
            "manage_users": False,
            "manage_roles": False,
        }
    },
    {
        "name": "Manager",
        "description": "Team manager with approval authority and business class access",
        "is_system": True,
        "default_access_scope": AccessScope.HIERARCHY,
        "permissions": {
            "book_flights": True,
            "book_hotels": True,
            "book_ground": True,
            "economy_class": True,
            "premium_economy_class": True,
            "business_class": True,  # ✅ Managers get business class
            "first_class": False,
            "view_own_bookings": True,
            "view_team_bookings": True,
            "view_all_bookings": False,
            "approve_travel": True,
            "approve_expenses": True,
            "override_policy": False,
            "view_analytics": True,
            "manage_policies": False,
            "manage_users": False,
            "manage_roles": False,
        }
    },
    {
        "name": "Executive Assistant",
        "description": "Can book for specific individuals assigned to them",
        "is_system": True,
        "default_access_scope": AccessScope.INDIVIDUALS,
        "permissions": {
            "book_flights": True,
            "book_hotels": True,
            "book_ground": True,
            "book_other": True,
            "economy_class": True,
            "premium_economy_class": True,
            "business_class": False,  # ❌ EA doesn't get business class for themselves
            "first_class": False,
            "view_own_bookings": True,
            "view_team_bookings": False,
            "view_all_bookings": False,
            "approve_travel": False,
            "approve_expenses": False,
            "override_policy": False,
            "view_analytics": False,
            "manage_policies": False,
            "manage_users": False,
            "manage_roles": False,
        }
    },
    {
        "name": "Travel Coordinator",
        "description": "Can book and view for specific groups or departments",
        "is_system": True,
        "default_access_scope": AccessScope.GROUP,
        "permissions": {
            "book_flights": True,
            "book_hotels": True,
            "book_ground": True,
            "book_other": True,
            "economy_class": True,
            "premium_economy_class": True,
            "business_class": True,
            "first_class": False,
            "view_own_bookings": True,
            "view_team_bookings": True,
            "view_all_bookings": False,
            "approve_travel": False,
            "approve_expenses": False,
            "override_policy": False,
            "view_analytics": True,
            "manage_policies": False,
            "manage_users": False,
            "manage_roles": False,
        }
    },
    {
        "name": "Travel Admin",
        "description": "Full access to all travel functions across the organization",
        "is_system": True,
        "default_access_scope": AccessScope.ALL,
        "permissions": {
            "book_flights": True,
            "book_hotels": True,
            "book_ground": True,
            "book_other": True,
            "economy_class": True,
            "premium_economy_class": True,
            "business_class": True,
            "first_class": True,
            "view_own_bookings": True,
            "view_team_bookings": True,
            "view_all_bookings": True,
            "approve_travel": True,
            "approve_expenses": True,
            "override_policy": True,
            "view_analytics": True,
            "manage_policies": True,
            "manage_users": True,
            "manage_roles": True,
            "manage_destinations": True,
        }
    },
    {
        "name": "Executive",
        "description": "Senior executive with first class access and policy override",
        "is_system": True,
        "default_access_scope": AccessScope.SELF,
        "permissions": {
            "book_flights": True,
            "book_hotels": True,
            "book_ground": True,
            "book_other": True,
            "economy_class": True,
            "premium_economy_class": True,
            "business_class": True,
            "first_class": True,  # ✅ Executives get first class
            "view_own_bookings": True,
            "view_team_bookings": True,
            "view_all_bookings": False,
            "approve_travel": True,
            "approve_expenses": True,
            "override_policy": True,
            "view_analytics": True,
            "manage_policies": False,
            "manage_users": False,
            "manage_roles": False,
        }
    },
]


async def seed_roles():
    """Seed default role templates for all organizations."""
    async with AsyncSessionLocal() as db:
        # Get all organizations
        result = await db.execute(select(Organization))
        orgs = result.scalars().all()
        
        if not orgs:
            print("No organizations found. Creating a default organization...")
            # This would only happen in fresh installs
            return
        
        for org in orgs:
            print(f"\n📋 Seeding roles for org: {org.name} ({org.id})")
            
            for role_data in DEFAULT_ROLES:
                # Check if role already exists
                stmt = select(RoleTemplate).where(
                    RoleTemplate.org_id == org.id,
                    RoleTemplate.name == role_data["name"],
                    RoleTemplate.is_system == True
                )
                result = await db.execute(stmt)
                existing = result.scalars().first()
                
                if existing:
                    print(f"   ⏭️  {role_data['name']} already exists")
                    continue
                
                role = RoleTemplate(
                    org_id=org.id,
                    name=role_data["name"],
                    description=role_data["description"],
                    is_system=role_data["is_system"],
                    default_access_scope=role_data["default_access_scope"],
                    permissions=role_data["permissions"],
                )
                db.add(role)
                print(f"   ✅ Created: {role_data['name']}")
            
            await db.commit()
        
        print("\n✅ Role seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_roles())
