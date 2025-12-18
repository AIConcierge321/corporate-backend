# Corporate Travel App — Core Logic Clarification
(Applies to: https://bugle-glaze-62467952.figma.site/)

## 1. Employees (Data, Hierarchy & Visibility)

### 1.1 Employee Data (from ERP)
The system should ingest all employee attributes available from the ERP, including but not limited to:
*   Full name
*   Job title / position
*   Email address
*   Department / team
*   Employee ID

👉 Please check and let me know which types of information we can extract and if we can get more information.

### 1.2 Hierarchy as the Core Structure
*   The organizational hierarchy defines approvals.
*   Every employee must have a clearly defined direct supervisor (except top-level roles like CEO).
*   All approval flows (travel, policy exceptions, etc.) route upward in the hierarchy.

Example:
*   Analyst → Manager → Director → CEO

### 1.3 Employee Visibility (Permission-Based)
*   The Employees list is not global.
*   Visibility is strictly controlled by the Permissions tab.

Rules:
*   A user can only see and book for employees they are permitted to act for.
*   If a manager is allowed to book only for their own team, they should:
    *   See only their direct and indirect reports
    *   NOT see other managers, the CEO, or unrelated departments
*   Visibility = Who you are allowed to act on behalf of

## 2. Policies (Approval Logic & Controls)

### 2.1 Approval Mode Configuration
The admin can choose between two policy modes:

**A. “Always Ask”**
*   Every booking always requires manager approval, regardless of:
    *   price
    *   timing
    *   class of travel

**B. “Only When Necessary”**
*   Manager approval is required only when a policy rule is violated

### 2.2 Cost Controls (Example)
Example rule: Max airfare = $800

| Ticket Price | Always Ask | Only When Necessary |
| :--- | :--- | :--- |
| $700 | Approval required | No approval |
| $1,000 | Approval required | Approval required |

👉 Any hard limit breach triggers approval in both modes.

### 2.3 Travel Class Eligibility
*   Travel class access (e.g., Business Class) is hierarchy-based
*   Example configurations:
    *   Business Class → CEO only
    *   Business Class → C-suite + Directors
*   This requires the company structure to be accurately defined first

### 2.4 Advance Booking Rules
Example rule: Flights must be booked ≥ 7 days in advance

| Booking Timing | Always Ask | Only When Necessary |
| :--- | :--- | :--- |
| 10 days ahead | Approval required | No approval |
| 3 days ahead | Approval required | Approval required |

👉 As long as the booking is within allowed thresholds, no approval is required under “Only When Necessary”.

### 2.5 Policy Summary Rule
*   Always Ask → approval for every booking
*   Only When Necessary → approval only when:
    *   cost limits are exceeded
    *   class eligibility rules are violated
    *   advance booking rules are broken

## 3. Permissions (The Most Critical Layer)

### 3.1 Hierarchy First
*   Permissions must be applied after extracting:
    *   reporting lines
    *   departments
    *   teams
*   Without hierarchy, permissions cannot function correctly.

### 3.2 Role-Based Capabilities
Each role should define:
*   What actions the user can perform
*   For whom they can perform them

Examples of permissions:
*   Book flights
*   Book hotels
*   Book ground transport
*   View analytics
*   Approve travel / expenses
*   Set or edit budgets

### 3.3 Acting “On Behalf Of” Logic
Permissions must distinguish between:
*   What you can do
*   Who you can do it for

Examples:
*   **Executive Assistant:**
    *   Can book travel
    *   Only for one specific person (their boss)
*   **Department Manager:**
    *   Can book for their entire team
    *   Can approve team bookings
*   **Travel Coordinator:**
    *   Can book for multiple teams or departments
*   **CEO:**
    *   Can book for anyone
    *   Can override policies

### 3.4 Role Templates (Configurable)
Role templates should be customizable, for example:
*   Travel Coordinator → book for department / company
*   Department Head → set budgets + approve team
*   Executive Assistant → book for named individual only

👉 Permissions define:
*   Visibility
*   Booking rights
*   Approval authority

## Final Principle (Important)
Hierarchy → Permissions → Visibility → Policy Enforcement
If hierarchy or permissions are wrong, everything else breaks.
