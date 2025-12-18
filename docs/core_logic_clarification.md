# Corporate Travel App — Core Logic Clarification
(Applies to: https://bugle-glaze-62467952.figma.site/)

---

## Implementation Status Summary

| Section | Status | Notes |
|---------|--------|-------|
| 1.1 Employee Data | ✅ Complete | Full name, job title, email, department, employee ID, division, cost center, phone |
| 1.2 Hierarchy | ✅ Complete | manager_id relationship with recursive traversal |
| 1.3 Visibility | ✅ Complete | AccessControl class enforces hierarchy-based visibility |
| 2.1 Approval Modes | ✅ Complete | ALWAYS_ASK / ONLY_WHEN_NECESSARY stored per Organization |
| 2.2 Cost Controls | ✅ Complete | max_amount in policy_settings |
| 2.3 Travel Class | ✅ Complete | business_class_titles in policy_settings |
| 2.4 Advance Booking | ✅ Complete | min_advance_days in policy_settings |
| 3.1 Hierarchy First | ✅ Complete | Permissions tied to Employee.manager_id hierarchy |
| 3.2 Role-Based Capabilities | ✅ Complete | Permissions class with granular capabilities |
| 3.3 Acting On Behalf Of | ⚠️ Partial | Manager→Team works. EA→Boss delegation needs explicit table |
| 3.4 Role Templates | ⚠️ Partial | Hardcoded in code. DB-driven roles for Phase 2 |

---

## 1. Employees (Data, Hierarchy & Visibility)

### 1.1 Employee Data (from ERP)

**Implemented Fields:**
| Field | DB Column | Source |
|-------|-----------|--------|
| Full name | `full_name`, `first_name`, `last_name` | SCIM `name` |
| Job title / position | `job_title` | SCIM `title` |
| Email address | `email` | SCIM `emails[]` |
| Department / team | `department` | SCIM enterprise extension |
| Employee ID | `external_user_id` | SCIM `userName` or `externalId` |
| Division | `division` | SCIM enterprise extension |
| Cost Center | `cost_center` | SCIM enterprise extension |
| Phone | `phone_number` | SCIM `phoneNumbers[]` |

**Additional Available (if ERP provides):**
- Manager ID (`manager_id` via `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User.manager`)
- Location / Office Address
- Employment Type (full-time, contractor)

### 1.2 Hierarchy as the Core Structure

**Implementation:**
- `Employee.manager_id` → Foreign key to parent Employee
- `Employee.subordinates` → Relationship to all direct reports
- Recursive traversal in `BookingStateMachine.submit_draft()` climbs up to 5 levels

**Approval Flow:**
```
Analyst.manager_id → Manager
Manager.manager_id → Director  
Director.manager_id → CEO
CEO.manager_id → NULL (top level)
```

**Edge Cases Handled:**
- If direct manager is `inactive` → Routes to their manager (skip-level)
- If no active manager in chain → Returns error: "Approval required but no active manager found"

### 1.3 Employee Visibility (Permission-Based)

**Implementation:** `app/core/access_control.py`

| Permission | Visibility |
|------------|------------|
| `VIEW_ALL_BOOKINGS` | See everyone in org |
| `VIEW_TEAM_BOOKINGS` | See self + all subordinates (recursive) |
| `VIEW_SELF_BOOKINGS` | See only self |

**Key Method:** `AccessControl.get_viewable_employees()`
- Returns `None` for global access
- Returns `List[int]` of employee IDs for restricted access

---

## 2. Policies (Approval Logic & Controls)

### 2.1 Approval Mode Configuration

**Storage:** `Organization.approval_mode` (Enum)
- `ALWAYS_ASK` → Every booking requires approval
- `ONLY_WHEN_NECESSARY` → Approval only when rules violated

**Implementation:** `app/services/policy_engine.py`

### 2.2 Cost Controls

**Storage:** `Organization.policy_settings["max_amount"]`
- Default: $1000

**Logic:**
```python
if booking.total_amount > max_amount:
    violations.append("Max Cost Exceeded")
```

### 2.3 Travel Class Eligibility

**Storage:** `Organization.policy_settings["business_class_titles"]`
- Default: `["CEO", "CTO", "CFO", "Director"]`

**Logic:**
```python
if travel_class in ["business", "first"]:
    for traveler in travelers:
        if traveler.job_title not in allowed_titles:
            violations.append("Travel Class Violation")
```

### 2.4 Advance Booking Rules

**Storage:** `Organization.policy_settings["min_advance_days"]`
- Default: 7 days

**Logic:**
```python
days_ahead = (booking.start_date - now).days
if days_ahead < min_advance_days:
    violations.append("Advance Booking Violation")
```

### 2.5 Policy Summary

| Mode | Violations | Result |
|------|------------|--------|
| ALWAYS_ASK | Any | `approval_required = True` |
| ONLY_WHEN_NECESSARY | None | `approval_required = False` |
| ONLY_WHEN_NECESSARY | Any | `approval_required = True` |

---

## 3. Permissions (The Most Critical Layer)

### 3.1 Hierarchy First

**Dependency Chain:**
```
ERP Sync (SCIM) 
    → Employee.manager_id populated
        → AccessControl can calculate subordinates
            → Permissions can be evaluated
                → Visibility enforced
                    → Policy checks run
```

### 3.2 Role-Based Capabilities

**Current Permissions:** `app/core/permissions.py`

| Permission | Description |
|------------|-------------|
| `BOOK_SELF` | Can create bookings for self |
| `BOOK_FOR_OTHERS` | Can book for subordinates |
| `BOOK_ANYONE` | Admin: Can book for anyone |
| `VIEW_SELF_BOOKINGS` | Can see own bookings |
| `VIEW_TEAM_BOOKINGS` | Can see team bookings |
| `VIEW_ALL_BOOKINGS` | Can see all org bookings |
| `MANAGE_POLICIES` | Can edit policy settings |
| `VIEW_ANALYTICS` | Can access dashboards |
| `MANAGE_USERS` | Can manage employees |

### 3.3 Acting "On Behalf Of" Logic

**Current Support:**

| Role | What They Can Do | Who They Can Do It For | Status |
|------|------------------|------------------------|--------|
| Employee | Book flights/hotels | Self only | ✅ |
| Manager | Book, View, Approve | Self + Subordinates | ✅ |
| Travel Admin | Book, View, Override | Anyone in Org | ✅ |
| Executive Assistant | Book | Specific Boss | ⚠️ Needs Delegation Table |

**Gap: Executive Assistant Delegation**
- Current system uses hierarchy (looks DOWN)
- EAs need to book for someone ABOVE them
- **Solution:** Create `Delegation` table for explicit 1-to-1 or 1-to-many assignments

### 3.4 Role Templates

**Current:** Hardcoded in `GROUP_PERMISSION_MAP`

```python
GROUP_PERMISSION_MAP = {
    "travel_admin": {...},
    "executive_assistant": {...},
    "employee": {...},
    "manager": {...}
}
```

**Phase 2:** Move to database table for dynamic configuration

---

## Open Questions for Manager

1. **Executive Assistant Delegation:**
   - Build explicit delegation table (EA → Boss mapping)?
   - Or treat EAs as limited admins for now?

2. **Role Configuration:**
   - Phase 1: Fixed roles in code?
   - Phase 2: Admin UI to create/edit roles?

3. **Travel Class Matrix:**
   - Simple: "Eligible for Business: Yes/No"
   - Complex: Job Title → Specific Cabin mapping?

---

## Final Principle
```
Hierarchy → Permissions → Visibility → Policy Enforcement
```
If hierarchy or permissions are wrong, everything else breaks.
