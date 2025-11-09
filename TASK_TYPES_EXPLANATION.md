# Task Types in the Task Scheduler Project

## Overview

Task Types define the different kinds of work assignments that need to be scheduled in this system. There are **two different concepts** related to task types:

1. **Hardcoded TaskType Enum** - Currently used by the scheduler
2. **Configurable TaskTypeDef** - Database-driven custom task types (infrastructure exists but not fully integrated)

---

## 1. Hardcoded TaskType Enum

### Definition
Located in `task_scheduler/models.py`, the `TaskType` enum defines four fixed task types:

```python
class TaskType(str, Enum):
    ATM_MORNING = "ATM_MORNING"      # Morning reporter (A-shift)
    ATM_MIDNIGHT = "ATM_MIDNIGHT"     # Mid-day+Night reporter (B-shift)
    SYSAID_MAKER = "SYSAID_MAKER"    # SysAid maker role
    SYSAID_CHECKER = "SYSAID_CHECKER" # SysAid checker role
```

### Purpose
These are the **actual task types used by the scheduler** to generate assignments. Each has specific characteristics:

#### ATM_MORNING (A-shift)
- **Time**: Morning shift at 07:30
- **Frequency**: Daily (Monday-Sunday)
- **Rest Rule**: No rest day required after assignment
- **Purpose**: Morning ATM monitoring/reporting

#### ATM_MIDNIGHT (B-shift)
- **Time**: Mid-day/Night shift (13:00-22:00 on weekdays, varies on weekends)
- **Frequency**: Daily (Monday-Sunday)
- **Rest Rule**: **Requires rest day the next day** (if enabled in config)
- **Cooldown**: Minimum 2 days between B-shift assignments (configurable)
- **Purpose**: Extended coverage for ATM monitoring

#### SYSAID_MAKER
- **Frequency**: Weekly (Monday-Saturday, no Sunday)
- **Duration**: Full week assignment
- **Purpose**: Primary SysAid ticket creator for the week

#### SYSAID_CHECKER
- **Frequency**: Weekly (Monday-Saturday, no Sunday)
- **Duration**: Full week assignment
- **Purpose**: Secondary SysAid ticket reviewer for the week

---

## 2. Schedule Generation Logic

The scheduler (`task_scheduler/scheduler.py`) uses a **two-phase approach**:

### Phase 1: ATM Schedule Generation (`_schedule_atm`)

**Process:**
1. Iterates through each day in the date range
2. For each day, looks up the required shifts from `ATM_SHIFT_PLAN` based on weekday
3. For each shift:
   - Gets eligible members (availability checks)
   - Selects the fairest assignee based on historical counts
   - Creates assignment
   - Updates fairness ledger

**Shift Plan by Day:**
- **Monday-Friday**: 2 shifts (Morning + Mid/Night)
- **Saturday**: 4 shifts (Morning + 3 Mid/Night variants)
- **Sunday**: 3 shifts (2 Morning + 1 Night)

**Eligibility Rules for ATM Tasks:**
```python
1. Member must not be in unavailable_dates
2. Member must not be in unavailable_ranges
3. If rest rule enabled: Member cannot have done ATM_MIDNIGHT yesterday
4. For ATM_MIDNIGHT: Member must not have done B-shift within cooldown period (default 2 days)
5. Member cannot be assigned twice on the same day
```

**Fairness Selection:**
- Primary: Lowest count for this specific task type
- Secondary: Lowest total count across all task types
- Tie-breaker: Deterministic hash based on date + task type

### Phase 2: SysAid Schedule Generation (`_schedule_sysaid`)

**Process:**
1. Groups dates into weeks (Monday-Saturday, configurable start day)
2. For each week:
   - Finds eligible members (must be available all week days)
   - Excludes members with rest days from ATM_MIDNIGHT assignments
   - Selects Maker (lowest SYSAID_MAKER count)
   - Selects Checker (lowest SYSAID_CHECKER count, different from Maker)
   - Creates assignments for all 6 days (Mon-Sat)

**Eligibility Rules for SysAid:**
```python
1. Member must be available on ALL week days (Mon-Sat)
2. Member must not have rest days during the week (from ATM_MIDNIGHT)
3. Member can have some ATM assignments, but must still be available
4. Need at least 2 eligible members (one for Maker, one for Checker)
```

**Special Constraints:**
- No Sunday coverage
- Maker and Checker must be different people
- Weekly assignments (counted once per week, not per day)

---

## 3. Fairness System

The scheduler uses a **FairnessLedger** to track assignment counts:

### Tracking
- **Per Task Type**: Counts how many times each member has done each task type
- **Rolling Window**: 90 days (configurable)
- **Total Count**: Sum across all task types

### Selection Algorithm
```python
1. Calculate scores for each eligible member:
   - Primary score: count for this task type
   - Secondary score: total count across all types

2. Sort by (primary_score, secondary_score) ascending

3. Select member with lowest scores

4. If tie: Use deterministic hash for consistent selection
```

### Example
If generating schedule for Monday:
- Member A: ATM_MORNING count = 5, Total = 20
- Member B: ATM_MORNING count = 5, Total = 18
- Member C: ATM_MORNING count = 3, Total = 15

**Result**: Member C is selected (lowest primary score)

---

## 4. Configurable TaskTypeDef (Future/Partial Implementation)

### Database Structure
The system has infrastructure for **custom task types** stored in the database:

**TaskTypeDef Table:**
- `name`: Task type name (e.g., "ATM", "SysAid")
- `recurrence`: "daily", "weekly", or "monthly"
- `required_count`: How many people needed per occurrence
- `role_labels`: List of role identifiers (e.g., ["A", "B"])
- `rules_json`: Advanced rules in JSON format

**ShiftDef Table:**
- `task_type_id`: Links to TaskTypeDef
- `label`: Shift name (e.g., "Morning Shift")
- `start_time`: Start time (HH:MM)
- `end_time`: End time (HH:MM)
- `required_count`: People needed for this shift

### Current Status
- ✅ Database tables exist
- ✅ CRUD API endpoints exist (`/api/task-types`)
- ✅ Frontend UI exists (TaskTypes component)
- ❌ **Not yet integrated into scheduler logic**

The scheduler currently uses the hardcoded `TaskType` enum, not the database `TaskTypeDef` records.

---

## 5. Key Scheduling Rules

### ATM Rest Rule
**If enabled** (`config.atm_rest_rule_enabled = True`):
- Member assigned to `ATM_MIDNIGHT` on day D
- **Cannot** be assigned to ANY ATM task on day D+1
- This ensures rest after heavy B-shift

### ATM B-Shift Cooldown
- Member assigned to `ATM_MIDNIGHT` on day D
- **Cannot** be assigned to `ATM_MIDNIGHT` again until day D + cooldown_days (default: 2)
- Prevents consecutive heavy shifts

### SysAid Weekly Constraint
- Maker and Checker must be different people
- Both must be available for entire week (Mon-Sat)
- No assignments on Sunday

### Availability Checks
- **ATM tasks**: Can work on any day (including Sunday) unless explicitly unavailable
- **SysAid tasks**: Must be in `office_days` (typically Mon-Fri)
- **Unavailable periods**: Override all availability (vacation, training, etc.)

---

## 6. Example Schedule Generation Flow

**Input:**
- Date range: 2025-01-06 (Monday) to 2025-01-12 (Sunday)
- Team: 5 members
- Config: Rest rule enabled, B-shift cooldown = 2 days

**Process:**

1. **ATM Schedule (Daily)**
   - Monday: Assign 2 shifts (Morning + Mid/Night)
   - Tuesday: Assign 2 shifts (consider rest days from Monday's B-shift)
   - ... continues for all 7 days
   - Saturday: Assign 4 shifts (more coverage needed)
   - Sunday: Assign 3 shifts

2. **SysAid Schedule (Weekly)**
   - Identify week: Mon 2025-01-06 to Sat 2025-01-11
   - Find members available all 6 days (excluding rest days)
   - Select Maker (lowest SYSAID_MAKER count)
   - Select Checker (lowest SYSAID_CHECKER count, different person)
   - Create 12 assignments (6 days × 2 roles)

**Output:**
- ~30+ ATM assignments (varies by day)
- 12 SysAid assignments
- Fairness counts updated
- Audit log generated

---

## 7. Integration Points

### Where Task Types Are Used

1. **Scheduler** (`scheduler.py`):
   - Uses `TaskType` enum directly
   - Hardcoded shift plans in `ATM_SHIFT_PLAN`

2. **API** (`api.py`):
   - `generate_schedule()`: Uses scheduler with hardcoded types
   - Task type CRUD: Manages `TaskTypeDef` (not yet used by scheduler)

3. **Database** (`database.py`):
   - `AssignmentDB.task_type`: Stores `TaskType` enum value
   - `FairnessCount.task_type`: Tracks counts per `TaskType`
   - `TaskTypeDef`: Stores custom definitions (future use)

4. **Frontend** (`TaskTypes.jsx`):
   - UI for managing custom task types
   - Currently for configuration only, not active in scheduling

---

## 8. Future Enhancements

To fully integrate configurable task types:

1. **Modify Scheduler**:
   - Load `TaskTypeDef` from database
   - Generate shifts dynamically based on `ShiftDef`
   - Support custom recurrence patterns

2. **Dynamic Shift Planning**:
   - Replace hardcoded `ATM_SHIFT_PLAN` with database-driven shifts
   - Support custom time windows per task type

3. **Rule Engine**:
   - Parse `rules_json` from `TaskTypeDef`
   - Apply custom constraints per task type

---

## Summary

**Current State:**
- ✅ Hardcoded task types work perfectly for ATM and SysAid
- ✅ Fairness system ensures balanced distribution
- ✅ Complex rules (rest days, cooldowns) are implemented
- ⚠️ Configurable task types exist but aren't used by scheduler

**Task Types Purpose:**
- Define what work needs to be assigned
- Determine scheduling frequency (daily vs weekly)
- Enforce business rules (rest days, cooldowns)
- Track fairness across team members

**Scheduling Logic:**
- Two-phase: ATM first, then SysAid
- Fairness-based selection (lowest count wins)
- Constraint checking (availability, rest days, cooldowns)
- Deterministic tie-breaking for consistency

