# Granular Permissions
class Permissions:
    # Booking
    BOOK_SELF = "book_self"
    BOOK_FOR_OTHERS = "book_for_others"
    BOOK_ANYONE = "book_anyone"
    VIEW_SELF_BOOKINGS = "view_self_bookings"
    VIEW_TEAM_BOOKINGS = "view_team_bookings"
    VIEW_ALL_BOOKINGS = "view_all_bookings"

    # Policy & Admin
    MANAGE_POLICIES = "manage_policies"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_USERS = "manage_users"


# Group -> Permissions Mapping
# In a real app, this might be stored in DB, but code-level is fine for strict control.
GROUP_PERMISSION_MAP: dict[str, set[str]] = {
    "travel_admin": {
        Permissions.BOOK_ANYONE,
        Permissions.VIEW_ALL_BOOKINGS,
        Permissions.MANAGE_POLICIES,
        Permissions.VIEW_ANALYTICS,
        Permissions.MANAGE_USERS,
    },
    "executive_assistant": {
        Permissions.BOOK_FOR_OTHERS,
        Permissions.VIEW_TEAM_BOOKINGS,
        Permissions.BOOK_SELF,
        Permissions.VIEW_SELF_BOOKINGS,
    },
    "employee": {Permissions.BOOK_SELF, Permissions.VIEW_SELF_BOOKINGS},
    "manager": {
        Permissions.BOOK_SELF,
        Permissions.VIEW_SELF_BOOKINGS,
        Permissions.VIEW_TEAM_BOOKINGS,
        Permissions.VIEW_ANALYTICS,
    },
}


def get_permissions_for_groups(groups: list[str]) -> set[str]:
    """
    Combine permissions from all groups a user belongs to.
    """
    permissions = set()
    for group in groups:
        # Normalize group name (e.g., case-insensitive matching)
        perms = GROUP_PERMISSION_MAP.get(group.lower())
        if perms:
            permissions.update(perms)

    # Default permissions for everyone (optional)
    perms = GROUP_PERMISSION_MAP.get("employee")
    if perms:
        permissions.update(perms)

    return permissions
