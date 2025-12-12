# Detailed Sequence Diagrams

## 1. Complete Booking Flow (Happy Path)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as Next.js Frontend
    participant API as FastAPI Gateway
    participant Policy as Policy Engine
    participant Booking as Booking Service
    participant Flight as Flight API (Duffel)
    participant Hotel as Hotel API (Hotelbeds)
    participant Payment as Payment Service
    participant Stripe as Stripe Issuing
    participant DB as PostgreSQL
    participant Queue as Redis Queue
    participant Worker as Celery Worker
    participant Notif as Notification Service
    
    %% SEARCH PHASE
    rect rgb(230, 240, 255)
        Note over U,Notif: PHASE 1: SEARCH & DISCOVERY
        U->>FE: Opens Explore page
        U->>FE: Searches "London, Oct 18-22"
        FE->>API: POST /bookings/search
        
        par Parallel API Calls
            API->>Flight: GET /search (origin=JFK, dest=LHR)
            API->>Hotel: GET /search (city=London, dates)
        end
        
        Flight-->>API: 50 flight options
        Hotel-->>API: 30 hotel options
        
        API->>Policy: POST /policies/bulk-evaluate (100 options)
        Policy->>DB: SELECT policies WHERE org_id=...
        Policy-->>API: Tagged options (green/amber/red)
        
        API-->>FE: Combined results with policy tags
        FE->>U: Display results with compliance badges
    end
    
    %% DRAFT PHASE
    rect rgb(230, 255, 240)
        Note over U,Notif: PHASE 2: SELECTION & DRAFT
        U->>FE: Selects Economy flight ($1850) + Hilton hotel ($980)
        U->>FE: Clicks "Save Draft"
        
        FE->>API: POST /bookings/draft {selections, employee_id}
        API->>DB: BEGIN TRANSACTION
        API->>DB: INSERT INTO bookings (status='draft', total=2830)
        API->>DB: INSERT INTO booking_segments (flight, hotel)
        
        API->>Policy: POST /policies/evaluate {draft_data}
        Policy->>DB: SELECT applicable policies
        Policy->>Policy: Evaluate rules (advance booking, limits, vendors)
        Policy-->>API: Result: OK (no violations)
        
        API->>DB: UPDATE bookings SET policy_status='ok'
        API->>DB: COMMIT TRANSACTION
        
        API-->>FE: {booking_id: "BK-2024-1847", status: "draft"}
        FE->>U: Show draft summary + "Confirm Booking" button
    end
    
    %% CONFIRMATION PHASE
    rect rgb(255, 245, 230)
        Note over U,Notif: PHASE 3: CONFIRMATION & PAYMENT
        U->>FE: Clicks "Confirm Booking"
        FE->>API: POST /bookings/BK-2024-1847/confirm {idempotency_key}
        
        API->>Policy: POST /policies/evaluate (final check)
        Policy-->>API: OK (no approval needed)
        
        %% Payment
        API->>Payment: POST /virtual-cards/create {amount: 2830}
        Payment->>Stripe: POST /issuing/cards
        Stripe-->>Payment: {card_id, card_number, cvv, expiry}
        Payment->>DB: INSERT INTO virtual_cards
        Payment-->>API: {virtual_card_id: "VC-001"}
        
        %% Book Flight
        API->>Booking: book_flight(offer_id, payment_details)
        Booking->>Flight: POST /flights/book {idempotency_key}
        Flight-->>Booking: {booking_ref: "BA178ABC", pnr: "XYZ123"}
        Booking->>DB: UPDATE booking_segments SET supplier_ref='BA178ABC'
        
        %% Book Hotel
        API->>Booking: book_hotel(room_id, payment_details)
        Booking->>Hotel: POST /hotels/book {idempotency_key}
        Hotel-->>Booking: {confirmation: "HLT-456"}
        Booking->>DB: UPDATE booking_segments SET supplier_ref='HLT-456'
        
        %% Finalize
        API->>DB: UPDATE bookings SET status='confirmed'
        API->>Queue: PUBLISH booking.created event
        API->>Notif: send_itinerary(employee_id, booking_id)
        
        par Async Worker Tasks
            Queue->>Worker: Consume booking.created
            Worker->>DB: UPDATE analytics_spend (aggregation)
            Worker->>DB: INSERT check_in_schedule
            Worker->>DB: UPDATE employee compliance_score
        end
        
        Notif->>U: Email: "Your trip to London is confirmed"
        
        API-->>FE: {status: "confirmed", confirmation: "ABC123"}
        FE->>U: Show success + download itinerary
    end
```

---

## 2. Booking with Approval Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as Employee
    participant FE as Frontend
    participant API as API
    participant Policy as Policy Engine
    participant Approval as Approval Service
    participant Notif as Notification
    participant Mgr as Manager
    participant DB as Database
    
    %% User submits booking
    rect rgb(255, 240, 240)
        Note over U,DB: PHASE 1: POLICY VIOLATION DETECTED
        U->>FE: Confirms booking (Business class, 3hr flight)
        FE->>API: POST /bookings/{id}/confirm
        
        API->>Policy: POST /policies/evaluate (final)
        Policy->>DB: SELECT policies WHERE type='soft'
        Policy->>Policy: Check: Business class + duration < 6h
        Policy-->>API: SOFT_WARNING (requires VP approval)
        
        API->>Approval: create_workflow(booking_id, policy_result)
        Approval->>DB: INSERT INTO approval_workflows
        Approval->>DB: Determine approvers (manager → VP)
        
        Approval->>DB: UPDATE bookings SET status='pending_approval'
        Approval-->>API: {workflow_id, approvers, sla}
        
        API-->>FE: 202 Accepted {status: "pending_approval"}
        FE->>U: "Your booking requires manager approval"
    end
    
    %% Notification
    rect rgb(240, 245, 255)
        Note over U,DB: PHASE 2: APPROVAL NOTIFICATION
        Approval->>Notif: notify_approver(manager_id, booking_details)
        Notif->>Mgr: Email: "Approve booking for Employee X"
        Notif->>Mgr: Slack: "New approval request"
    end
    
    %% Manager approves
    rect rgb(240, 255, 240)
        Note over U,DB: PHASE 3: APPROVAL DECISION
        Mgr->>FE: Opens approval link
        Mgr->>FE: Reviews booking details + policy warning
        Mgr->>FE: Clicks "Approve" with justification
        
        FE->>API: POST /approvals/{id}/approve {justification}
        API->>DB: UPDATE approval_workflows SET status='approved'
        API->>DB: UPDATE bookings SET status='confirmed'
        
        %% Trigger booking execution
        API->>API: trigger_booking_execution(booking_id)
        Note over API,DB: (Same flow as happy path booking)
        
        API->>Notif: notify_employee(booking_approved)
        Notif->>U: Email: "Your booking has been approved and confirmed"
        
        API-->>FE: {status: "approved"}
        FE->>Mgr: "Booking approved successfully"
    end
```

---

## 3. Disruption Detection & Auto-Rebook

```mermaid
sequenceDiagram
    autonumber
    participant Flight as Flight Provider
    participant Webhook as Webhook Handler
    participant Disruption as Disruption Service
    participant DB as Database
    participant Queue as Redis Queue
    participant Rebook as Auto-Rebook Worker
    participant Policy as Policy Engine
    participant Notif as Notification
    participant Traveler as Traveler
    participant Admin as Travel Admin
    
    %% Disruption detected
    rect rgb(255, 235, 235)
        Note over Flight,Admin: PHASE 1: DISRUPTION DETECTION
        Flight->>Webhook: POST /webhooks/flight-status
        Note right of Flight: {flight: "BA178", status: "canceled"}
        
        Webhook->>DB: SELECT bookings WHERE supplier_ref='BA178'
        DB-->>Webhook: [booking_1, booking_2, booking_3, booking_4]
        
        loop For each affected booking
            Webhook->>DB: INSERT INTO disruption_events
            Webhook->>DB: UPDATE bookings SET status='requires_attention'
            Webhook->>Queue: PUBLISH disruption.detected event
        end
    end
    
    %% Immediate notification
    rect rgb(255, 245, 230)
        Note over Flight,Admin: PHASE 2: TRAVELER NOTIFICATION
        Webhook->>Notif: notify_critical_disruption(booking_ids)
        
        par Notify all stakeholders
            Notif->>Traveler: SMS: "Flight BA178 canceled. Rebooking options coming..."
            Notif->>Traveler: Email: Full disruption details
            Notif->>Admin: Dashboard alert: "4 travelers affected"
        end
    end
    
    %% Auto-rebook flow
    rect rgb(235, 255, 245)
        Note over Flight,Admin: PHASE 3: AUTO-REBOOK SEARCH
        Queue->>Rebook: Consume disruption.detected event
        
        Rebook->>DB: SELECT booking details (route, dates, class)
        Rebook->>Flight: POST /search (same route, nearby times)
        Flight-->>Rebook: [alternative_1, alternative_2, ...]
        
        Rebook->>Policy: POST /policies/bulk-evaluate (alternatives)
        Policy-->>Rebook: Tagged alternatives (compliant options first)
        
        Rebook->>Rebook: Rank by: 1) policy, 2) timing, 3) price
        Rebook->>DB: INSERT INTO rebook_suggestions
    end
    
    %% Present options
    rect rgb(245, 240, 255)
        Note over Flight,Admin: PHASE 4: TRAVELER DECISION
        Rebook->>Notif: send_rebook_options(traveler)
        Notif->>Traveler: Email with 3 top options
        Notif->>Traveler: SMS with link to select option
        
        Traveler->>Webhook: Clicks option 1 (next flight, +$200)
        Webhook->>DB: SELECT suggested booking
        
        alt Auto-approved (within policy)
            Webhook->>Flight: POST /flights/book (option 1)
            Flight-->>Webhook: {new_booking_ref}
            Webhook->>DB: UPDATE booking_segments
            Webhook->>DB: UPDATE disruption_events SET resolved=true
            Webhook->>Notif: send_confirmation(traveler)
            Notif->>Traveler: "Rebooked on UA1548, departs 8:30 AM"
        else Requires approval (price increase)
            Webhook->>Webhook: create_approval_workflow
            Notif->>Admin: "Approval needed: +$200 rebook"
        end
    end
```

---

## 4. Payment Reconciliation Flow

```mermaid
sequenceDiagram
    autonumber
    participant Merchant as Merchant (Airline)
    participant Stripe as Stripe
    participant Webhook as Stripe Webhook Handler
    participant Reconcile as Reconciliation Worker
    participant DB as Database
    participant Finance as Finance Team
    
    %% Payment occurs
    rect rgb(240, 255, 240)
        Note over Merchant,Finance: PHASE 1: PAYMENT CAPTURE
        Merchant->>Stripe: Charge virtual card (BA flight $1850)
        Stripe->>Stripe: Process payment
        Stripe-->>Merchant: Payment successful
        
        Stripe->>Webhook: POST /webhooks/stripe
        Note right of Stripe: payment_intent.succeeded
        Webhook->>DB: INSERT INTO transactions
        Note right of Webhook: {txn_id, card_id, amount, merchant}
    end
    
    %% Nightly reconciliation
    rect rgb(245, 245, 255)
        Note over Merchant,Finance: PHASE 2: NIGHTLY RECONCILIATION JOB
        activate Reconcile
        Reconcile->>DB: SELECT transactions WHERE reconciled=false
        Reconcile->>DB: SELECT virtual_cards JOIN bookings
        
        loop For each unreconciled transaction
            Reconcile->>Reconcile: Match txn.card_id → booking_id
            Reconcile->>DB: SELECT booking_segments WHERE booking_id=...
            
            alt Perfect match (amount & merchant)
                Reconcile->>DB: UPDATE transactions SET reconciled=true
                Reconcile->>DB: INSERT INTO invoices (finalized)
            else Amount mismatch
                Reconcile->>DB: INSERT INTO reconciliation_exceptions
                Note right of Reconcile: {expected: 1850, actual: 1920}
                Reconcile->>Reconcile: Flag for manual review
            else Unknown merchant
                Reconcile->>DB: INSERT INTO reconciliation_exceptions
                Reconcile->>Reconcile: Flag as potential fraud
            end
        end
        deactivate Reconcile
    end
    
    %% Manual review
    rect rgb(255, 245, 245)
        Note over Merchant,Finance: PHASE 3: EXCEPTION HANDLING
        Reconcile->>Finance: Dashboard alert: "7 flagged transactions"
        
        Finance->>DB: SELECT reconciliation_exceptions
        Finance->>Finance: Review each exception
        
        alt Legitimate (baggage fee, seat upgrade)
            Finance->>DB: UPDATE transactions SET approved=true
            Finance->>DB: UPDATE invoices (adjust amount)
        else Fraudulent
            Finance->>Stripe: Dispute charge
            Finance->>DB: UPDATE transactions SET status='disputed'
        end
    end
```

---

## 5. Multi-Step Approval Workflow

```mermaid
sequenceDiagram
    autonumber
    participant Emp as Employee
    participant API as API
    participant Approval as Approval Engine
    participant DB as Database
    participant Notif as Notification
    participant Mgr as Manager
    participant VP as VP Finance
    participant Exec as Executive
    
    %% Booking requires multi-step approval
    rect rgb(255, 250, 240)
        Note over Emp,Exec: HIGH-VALUE BOOKING ($15,000)
        Emp->>API: POST /bookings/confirm (Tokyo trip, $15K)
        API->>Approval: evaluate_approval_requirements
        
        Approval->>DB: SELECT approval_policies
        Note right of Approval: Thresholds:<br/>$5K → Manager<br/>$10K → VP Finance<br/>$15K → Executive
        
        Approval->>DB: INSERT INTO approval_workflows
        Note right of Approval: {\n  steps: [\n    {step: 1, approver: Manager, threshold: 5K},\n    {step: 2, approver: VP Finance, threshold: 10K},\n    {step: 3, approver: Executive, threshold: 15K}\n  ]\n}
        
        Approval-->>API: Workflow created (3 steps)
        API-->>Emp: "Booking pending 3-level approval"
    end
    
    %% Step 1: Manager
    rect rgb(240, 250, 255)
        Note over Emp,Exec: STEP 1: MANAGER APPROVAL
        Approval->>Notif: notify_approver(Manager)
        Notif->>Mgr: Email + Slack notification
        
        Mgr->>API: POST /approvals/{id}/approve (Step 1)
        API->>DB: UPDATE approval_workflows SET current_step=2
        
        Approval->>Notif: notify_approver(VP Finance)
        Notif->>VP: Email: "Pending your approval (Step 2 of 3)"
    end
    
    %% Step 2: VP Finance
    rect rgb(240, 255, 250)
        Note over Emp,Exec: STEP 2: VP FINANCE APPROVAL
        VP->>API: Reviews budget utilization
        VP->>API: POST /approvals/{id}/approve (Step 2)
        API->>DB: UPDATE approval_workflows SET current_step=3
        
        Approval->>Notif: notify_approver(Executive)
        Notif->>Exec: Email: "Final approval required (Step 3 of 3)"
    end
    
    %% Step 3: Executive (with SLA escalation)
    rect rgb(255, 245, 250)
        Note over Emp,Exec: STEP 3: EXECUTIVE APPROVAL + SLA
        
        loop SLA Check (every 6 hours)
            Approval->>DB: SELECT WHERE sla_deadline < NOW()
            alt SLA breached
                Approval->>Notif: escalate_approval(COO)
                Notif->>Exec: "URGENT: Approval overdue"
            end
        end
        
        Exec->>API: POST /approvals/{id}/approve (Step 3)
        API->>DB: UPDATE approval_workflows SET status='approved'
        API->>DB: UPDATE bookings SET status='confirmed'
        
        %% Trigger booking execution
        API->>API: execute_booking(booking_id)
        
        Approval->>Notif: notify_all_stakeholders
        Notif->>Emp: "Booking approved and confirmed"
        Notif->>Mgr: "Booking completed"
        Notif->>VP: "Booking completed"
    end
```

---

## 6. AI Concierge Conversation Flow

```mermaid
sequenceDiagram
    autonumber
    participant User as User
    participant Chat as Chat UI
    participant API as API
    participant LLM as OpenAI GPT-4
    participant Tools as Function Tools
    participant Booking as Booking Service
    participant Policy as Policy Engine
    participant DB as Database
    
    %% User starts conversation
    rect rgb(245, 250, 255)
        Note over User,DB: PHASE 1: INTENT RECOGNITION
        User->>Chat: "Book a flight to London next week"
        Chat->>API: POST /ai-concierge/chat
        
        API->>LLM: Prompt + user message + context
        Note right of API: System: You are a corporate travel assistant.<br/>Tools: search_flights, check_policy, create_booking
        
        LLM->>LLM: Parse intent: BOOK_FLIGHT
        LLM-->>API: Function call: search_flights(dest="London", dates="next week")
    end
    
    %% Execute tool
    rect rgb(250, 255, 245)
        Note over User,DB: PHASE 2: SEARCH EXECUTION
        API->>Tools: execute_function(search_flights)
        Tools->>Booking: POST /bookings/search (flexible dates)
        Booking-->>Tools: 20 flight options
        
        Tools->>Policy: POST /policies/bulk-evaluate (top 5 options)
        Policy-->>Tools: Tagged options (3 green, 2 amber)
        
        Tools-->>API: Filtered results (policy-compliant first)
    end
    
    %% LLM generates response
    rect rgb(255, 250, 245)
        Note over User,DB: PHASE 3: INTELLIGENT RESPONSE
        API->>LLM: Function response + filtered results
        LLM->>LLM: Generate natural language response
        LLM-->>API: "I found 3 policy-compliant flights to London:<br/><br/>1. BA178 - $1,850 (Economy, direct)<br/>2. UA15 - $1,920 (Economy, 1 stop)<br/>3. AA101 - $3,200 (Business)<br/><br/>Option 1 is recommended (lowest cost + direct).<br/>Would you like to proceed with BA178?"
        
        API-->>Chat: Stream response
        Chat->>User: Display formatted message + action buttons
    end
    
    %% User confirms
    rect rgb(250, 245, 255)
        Note over User,DB: PHASE 4: BOOKING CONFIRMATION
        User->>Chat: "Yes, book BA178"
        Chat->>API: POST /ai-concierge/chat (continue conversation)
        
        API->>LLM: User confirmation message
        LLM-->>API: Function call: create_booking(flight="BA178")
        
        API->>Tools: execute_function(create_booking)
        Tools->>DB: INSERT INTO bookings (status='draft')
        Tools->>Policy: evaluate_booking (final check)
        Policy-->>Tools: OK (no approval needed)
        
        Tools-->>API: {booking_id, status: "draft"}
        
        API->>LLM: Booking created successfully
        LLM-->>API: "Great! I've created your booking:<br/><br/>✅ BA178 - London<br/>📅 Oct 18, 6:00 PM<br/>💵 $1,850<br/><br/>Ready to confirm? I'll also search for hotels."
        
        API-->>Chat: Stream response
        Chat->>User: Display booking summary + confirm button
    end
    
    %% Context-aware follow-up
    rect rgb(255, 250, 250)
        Note over User,DB: PHASE 5: CONTEXTUAL HOTEL SEARCH
        LLM->>LLM: Proactive action: search_hotels
        Note right of LLM: Context: User booked LHR flight Oct 18-22
        
        LLM-->>API: Function call: search_hotels(city="London", checkin="Oct 18", checkout="Oct 22")
        API->>Tools: execute_function
        Tools->>Booking: POST /hotels/search
        Booking-->>Tools: 15 hotel options
        
        Tools-->>API: Filtered results (preferred vendors first)
        API->>LLM: Hotel results
        
        LLM-->>Chat: "I also found 3 preferred hotels:<br/><br/>1. Hilton Metropole - $245/night ⭐ Best value<br/>2. Marriott West India Quay - $280/night<br/>3. Hyatt Regency - $320/night<br/><br/>All are within policy. Which do you prefer?"
    end
```

---

## 7. Analytics Aggregation (Background Job)

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Scheduled Cron
    participant Worker as Analytics Worker
    participant DB as PostgreSQL
    participant Cache as Redis Cache
    participant API as Analytics API
    participant Dashboard as Dashboard UI
    
    %% Nightly aggregation
    rect rgb(240, 245, 255)
        Note over Cron,Dashboard: DAILY AGGREGATION JOB (2:00 AM)
        Cron->>Worker: Trigger: aggregate_daily_spend
        activate Worker
        
        Worker->>DB: BEGIN TRANSACTION
        
        %% Department aggregation
        Worker->>DB: SELECT SUM(total_amount), department<br/>FROM bookings<br/>WHERE created_at::date = YESTERDAY<br/>GROUP BY department
        
        loop For each department
            Worker->>DB: INSERT INTO analytics_spend<br/>(period='daily', department, total_spend)
        end
        
        %% Employee aggregation
        Worker->>DB: SELECT SUM(total_amount), employee_id<br/>FROM bookings<br/>WHERE created_at::date = YESTERDAY<br/>GROUP BY employee_id
        
        loop For each employee
            Worker->>DB: INSERT INTO analytics_spend<br/>(period='daily', employee_id, total_spend)
            Worker->>DB: UPDATE employees<br/>SET compliance_score = calculate_compliance()
        end
        
        Worker->>DB: COMMIT TRANSACTION
        deactivate Worker
    end
    
    %% CO2 calculation
    rect rgb(245, 255, 245)
        Note over Cron,Dashboard: CO2 EMISSIONS CALCULATION
        Worker->>DB: SELECT booking_segments<br/>WHERE segment_type='flight'<br/>AND created_at::date = YESTERDAY
        
        loop For each flight
            Worker->>Worker: Calculate CO2 (distance × cabin_multiplier)
            Note right of Worker: Economy: 0.115 kg/km<br/>Business: 0.230 kg/km
            Worker->>DB: UPDATE booking_segments SET co2_kg = calculated
        end
        
        Worker->>DB: INSERT INTO analytics_spend (co2_emissions = SUM)
    end
    
    %% Cache warming
    rect rgb(255, 250, 240)
        Note over Cron,Dashboard: CACHE WARMING FOR DASHBOARD
        Worker->>DB: SELECT * FROM analytics_spend<br/>WHERE period_end >= (NOW() - interval '30 days')
        
        Worker->>Cache: SET dashboard:spend:30d (JSON, TTL=1h)
        Worker->>Cache: SET dashboard:compliance (metrics, TTL=1h)
        Worker->>Cache: SET dashboard:top_destinations (list, TTL=1h)
    end
    
    %% Dashboard load
    rect rgb(250, 245, 255)
        Note over Cron,Dashboard: USER LOADS DASHBOARD
        Dashboard->>API: GET /analytics/summary
        
        API->>Cache: GET dashboard:spend:30d
        alt Cache hit
            Cache-->>API: Return cached data (fast)
        else Cache miss
            API->>DB: Query analytics tables
            DB-->>API: Raw data
            API->>Cache: SET cache (for next request)
        end
        
        API-->>Dashboard: {spend, compliance, destinations}
        Dashboard->>Dashboard: Render charts
    end
```

---

## Key Takeaways from Sequence Diagrams:

### 1. **Idempotency is Critical**
- Every booking operation uses `idempotency_key`
- Prevents duplicate bookings on retries

### 2. **Async Operations**
- Heavy tasks (analytics, notifications) happen asynchronously
- Main booking flow stays fast (<2s response time)

### 3. **Policy Engine is Central**
- Called at multiple stages: search, draft, confirm, rebook
- Ensures compliance throughout lifecycle

### 4. **Multi-Layer Communication**
- Frontend → API Gateway → Services → External APIs
- Clear separation of concerns

### 5. **Event-Driven Architecture**
- BookingCreated event triggers: analytics, check-in, reconciliation
- Decouples services

### 6. **Resilience Patterns**
- Retries with exponential backoff
- Circuit breakers for external APIs
- Fallback to manual workflows

---

## Error Handling Patterns

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Flight as Flight API
    participant DB
    
    User->>API: POST /bookings/confirm
    API->>Flight: POST /flights/book
    
    alt 5xx Server Error
        Flight-->>API: 500 Internal Server Error
        API->>API: Retry 1 (wait 1s)
        API->>Flight: POST /flights/book (same idempotency_key)
        Flight-->>API: 500 Internal Server Error
        API->>API: Retry 2 (wait 2s)
        API->>Flight: POST /flights/book
        Flight-->>API: 200 OK (booking confirmed)
        API-->>User: Success
    else 4xx Client Error
        Flight-->>API: 400 Bad Request (invalid payment)
        API->>DB: UPDATE bookings SET status='failed'
        API-->>User: Error: Payment declined
    else Timeout
        API->>Flight: POST /flights/book
        Note over Flight: No response (timeout 30s)
        API->>DB: UPDATE bookings SET status='pending_confirmation'
        API->>DB: INSERT INTO manual_review_queue
        API-->>User: Booking is being processed. We'll email you confirmation.
    else Circuit Breaker Open
        API->>API: Check circuit breaker (too many failures)
        API-->>User: Service temporarily unavailable. Try again in 5 minutes.
    end
```

This comprehensive set of diagrams shows **exactly how data flows** through your system for every major user journey!
