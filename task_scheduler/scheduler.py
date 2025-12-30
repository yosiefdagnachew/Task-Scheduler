"""Core scheduling logic for ATM and SysAid tasks."""

from datetime import date, timedelta
import calendar
from typing import List, Optional, Set, Tuple, Dict, Any
from .models import TeamMember, Assignment, TaskType, Schedule, FairnessLedger
from .config import SchedulingConfig
from .rest_day_helper import calculate_rest_day, is_rest_day
from .task_type_model import DynamicTaskType, TaskTypeShift

ATM_SHIFT_PLAN = {
    0: [  # Monday
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    1: [  # Tuesday
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    2: [  # Wednesday
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    3: [  # Thursday
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    4: [  # Friday - rest day is Monday (not Saturday)
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    5: [  # Saturday - no rest day
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Midday (06:00)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Midday (11:00)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Night (16:00)", "rest_next_day": False},
    ],
    6: [  # Sunday - no rest day
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (09:00)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Night (16:00)", "rest_next_day": False},
    ],
}


class AuditLog:
    """Simple audit log for scheduling decisions."""
    
    def __init__(self):
        self.entries: List[str] = []
    
    def log(self, message: str):
        """Add an entry to the audit log."""
        self.entries.append(message)
    
    def get_log(self) -> str:
        """Get the full audit log as a string."""
        return "\n".join(self.entries)


class Scheduler:
    """Main scheduler that generates fair assignments."""
    
    def __init__(
        self,
        config: SchedulingConfig,
        ledger: Optional[FairnessLedger] = None,
        dynamic_counts: Optional[Dict[str, Dict[str, int]]] = None
    ):
        self.config = config
        self.ledger = ledger or FairnessLedger(fairness_window_days=config.fairness_window_days)
        self.audit = AuditLog()
        # Track fairness for dynamic task types (custom task types from database)
        if dynamic_counts:
            self.dynamic_task_counts = {task: dict(counts) for task, counts in dynamic_counts.items()}
        else:
            self.dynamic_task_counts = {}
    
    def generate_schedule(
        self,
        members: List[TeamMember],
        start_date: date,
        end_date: date,
        task_types: Optional[List[DynamicTaskType]] = None,
        task_members: Optional[Dict[str, List[str]]] = None
    ) -> Schedule:
        """
        Generate a complete schedule for the given date range.
        
        Args:
            members: List of team members
            start_date: Start date for schedule
            end_date: End date for schedule
            task_types: Optional list of DynamicTaskType records from database.
                       If None, uses hardcoded ATM/SysAid logic (backward compatibility)
        """
        schedule = Schedule(start_date=start_date, end_date=end_date)
        
        if task_types:
            # Use database-driven task types
            for task_type in task_types:
                # Filter members for this task type if task_members mapping is provided
                task_specific_members = members
                if task_members and task_type.name in task_members:
                    selected_member_ids = set(task_members[task_type.name])
                    task_specific_members = [m for m in members if m.id in selected_member_ids]
                    if not task_specific_members:
                        self.audit.log(f"WARNING: No members selected for task type '{task_type.name}', skipping")
                        continue
                    self.audit.log(f"Using {len(task_specific_members)} selected members for task type '{task_type.name}'")
                
                if task_type.recurrence == "daily":
                    assignments = self._schedule_daily_task_type(task_specific_members, task_type, start_date, end_date, schedule)
                elif task_type.recurrence == "weekly":
                    assignments = self._schedule_weekly_task_type(task_specific_members, task_type, start_date, end_date, schedule)
                elif task_type.recurrence == "monthly":
                    assignments = self._schedule_monthly_task_type(task_specific_members, task_type, start_date, end_date, schedule)
                else:
                    self.audit.log(f"WARNING: Unknown recurrence '{task_type.recurrence}' for task type '{task_type.name}', skipping")
                    continue
                schedule.assignments.extend(assignments)
        else:
            # Backward compatibility: use hardcoded ATM/SysAid logic
            # Filter members if task_members mapping is provided with "default" key
            atm_sysaid_members = members
            if task_members and "default" in task_members:
                selected_member_ids = set(task_members["default"])
                atm_sysaid_members = [m for m in members if m.id in selected_member_ids]
                if not atm_sysaid_members:
                    self.audit.log("WARNING: No members selected for default ATM/SysAid schedule, skipping")
                    return schedule
                self.audit.log(f"Using {len(atm_sysaid_members)} selected members for default ATM/SysAid schedule")
            
            # Schedule SysAid FIRST to ensure we have enough members
            # Then schedule ATM while avoiding conflicts with SysAid weeks
            sysaid_assignments = self._schedule_sysaid(atm_sysaid_members, start_date, end_date, schedule)
            schedule.assignments.extend(sysaid_assignments)
            
            # Now schedule ATM, but exclude members who have SysAid assignments during their weeks
            atm_assignments = self._schedule_atm_with_sysaid_conflict_check(atm_sysaid_members, start_date, end_date, schedule)
            schedule.assignments.extend(atm_assignments)
        
        return schedule
    
    def _schedule_atm_with_sysaid_conflict_check(
        self,
        members: List[TeamMember],
        start_date: date,
        end_date: date,
        existing_schedule: Schedule
    ) -> List[Assignment]:
        """Schedule ATM monitoring tasks while avoiding conflicts with SysAid assignments."""
        assignments = []
        
        # Build map of SysAid assignments by week
        sysaid_by_week = {}  # {week_start: set(member_ids)}
        for a in existing_schedule.assignments:
            if a.task_type in {TaskType.SYSAID_MAKER, TaskType.SYSAID_CHECKER} and a.week_start:
                if a.week_start not in sysaid_by_week:
                    sysaid_by_week[a.week_start] = set()
                sysaid_by_week[a.week_start].add(a.assignee.id)
        
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.weekday()
            shifts = ATM_SHIFT_PLAN.get(weekday, ATM_SHIFT_PLAN[0])
            assigned_today = {a.assignee.id for a in assignments if a.date == current_date}

            # Check which week this date belongs to (for SysAid conflict check)
            days_since_monday = current_date.weekday() - self.config.sysaid_week_start_day
            if days_since_monday < 0:
                days_since_monday += 7
            week_start = current_date - timedelta(days=days_since_monday)
            sysaid_members_this_week = sysaid_by_week.get(week_start, set())

            for shift in shifts:
                task_type = shift["task_type"]
                label = shift["label"]
                rest_next_day = shift.get("rest_next_day", False)

                eligible = self._get_eligible_members(members, current_date, task_type, assignments)

                # If this shift creates a rest day (B-shift), avoid assigning members
                # whose rest day would overlap with a SysAid assignment. Previously
                # we excluded all SysAid members for the whole week which caused
                # shortages; instead only block those with an actual conflict on
                # the computed rest day.
                if rest_next_day:
                    rest_day = calculate_rest_day(current_date)
                    if rest_day:
                        # collect members who have SysAid assignment on the rest day
                        sysaid_on_rest = set()
                        for a in existing_schedule.assignments:
                            a_task = a.task_type
                            a_task_is_sys = False
                            if isinstance(a_task, TaskType):
                                a_task_is_sys = a_task in {TaskType.SYSAID_MAKER, TaskType.SYSAID_CHECKER}
                            else:
                                a_task_is_sys = str(a_task) in {TaskType.SYSAID_MAKER.value, TaskType.SYSAID_CHECKER.value}
                            if a_task_is_sys and a.date == rest_day:
                                sysaid_on_rest.add(a.assignee.id)

                        eligible = [m for m in eligible if m.id not in sysaid_on_rest]

                # Do not assign members already assigned today
                eligible = [m for m in eligible if m.id not in assigned_today]

                if not eligible:
                    self.audit.log(f"WARNING: {current_date} - No eligible members for {label} ({task_type.value})")
                    continue

                assignee = self._select_assignee(eligible, task_type, current_date)
                assignments.append(Assignment(
                    task_type=task_type,
                    assignee=assignee,
                    date=current_date,
                    shift_label=label
                ))
                assigned_today.add(assignee.id)

                if self.config.atm_rest_rule_enabled and rest_next_day:
                    rest_day = calculate_rest_day(current_date)
                    if rest_day:
                        self.audit.log(f"{current_date} - Assigned {assignee.name} to {label}. Rest on {rest_day}")
                    else:
                        self.audit.log(f"{current_date} - Assigned {assignee.name} to {label} (no rest day)")
                else:
                    self.audit.log(f"{current_date} - Assigned {assignee.name} to {label}")

                self.ledger.increment(assignee.id, task_type)

            current_date += timedelta(days=1)

        return assignments
    
    def _schedule_atm(
        self,
        members: List[TeamMember],
        start_date: date,
        end_date: date
    ) -> List[Assignment]:
        """Schedule ATM monitoring tasks (daily)."""
        assignments = []
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.weekday()
            shifts = ATM_SHIFT_PLAN.get(weekday, ATM_SHIFT_PLAN[0])
            assigned_today = {a.assignee.id for a in assignments if a.date == current_date}

            for shift in shifts:
                task_type = shift["task_type"]
                label = shift["label"]
                rest_next_day = shift.get("rest_next_day", False)

                eligible = self._get_eligible_members(members, current_date, task_type, assignments)
                eligible = [m for m in eligible if m.id not in assigned_today]

                if not eligible:
                    self.audit.log(f"WARNING: {current_date} - No eligible members for {label} ({task_type.value})")
                    continue

                assignee = self._select_assignee(eligible, task_type, current_date)
                assignments.append(Assignment(
                    task_type=task_type,
                    assignee=assignee,
                    date=current_date,
                    shift_label=label
                ))
                assigned_today.add(assignee.id)

                if self.config.atm_rest_rule_enabled and rest_next_day:
                    rest_day = calculate_rest_day(current_date)
                    if rest_day:
                        self.audit.log(f"{current_date} - Assigned {assignee.name} to {label}. Rest on {rest_day}")
                    else:
                        self.audit.log(f"{current_date} - Assigned {assignee.name} to {label} (no rest day)")
                else:
                    self.audit.log(f"{current_date} - Assigned {assignee.name} to {label}")

                self.ledger.increment(assignee.id, task_type)

            current_date += timedelta(days=1)

        return assignments
    
    def _schedule_sysaid(
        self,
        members: List[TeamMember],
        start_date: date,
        end_date: date,
        existing_schedule: Schedule
    ) -> List[Assignment]:
        """Schedule SysAid tasks (weekly)."""
        assignments = []
        # Build per-member rest-day map from existing ATM assignments
        # Accept either enum TaskType or string identifier for dynamic tasks
        b_assignments = [
            a for a in existing_schedule.assignments
            if (a.task_type == TaskType.ATM_MIDNIGHT) or (isinstance(a.task_type, str) and a.task_type == TaskType.ATM_MIDNIGHT.value)
        ]
        member_rest_days = {}
        for a in b_assignments:
            rd = calculate_rest_day(a.date)
            if rd:
                member_rest_days.setdefault(a.assignee.id, set()).add(rd)

        # Map ATM assignments by date to avoid double-booking with SysAid
        atm_by_date = {}
        for a in existing_schedule.assignments:
            if (a.task_type == TaskType.ATM_MORNING) or (isinstance(a.task_type, str) and a.task_type == TaskType.ATM_MORNING.value) or \
               (a.task_type == TaskType.ATM_MIDNIGHT) or (isinstance(a.task_type, str) and a.task_type == TaskType.ATM_MIDNIGHT.value):
                atm_by_date.setdefault(a.date, set()).add(a.assignee.id)
        
        # Find week boundaries
        current_date = start_date
        while current_date <= end_date:
            # Find the start of the week (Monday by default)
            days_since_monday = current_date.weekday() - self.config.sysaid_week_start_day
            if days_since_monday < 0:
                days_since_monday += 7
            week_start = current_date - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            # Skip if we've already processed this week
            if any(a.week_start == week_start for a in assignments):
                current_date = week_end + timedelta(days=1)
                continue
            
            # Check Monday-Saturday for SysAid (no Sunday coverage)
            week_dates = [week_start + timedelta(days=i) for i in range(6)]
            
            # Find eligible members (must be in office for all days of the week)
            # Since SysAid is scheduled FIRST, we don't need to check for ATM conflicts here
            # ATM will be scheduled later and will avoid SysAid conflicts
            eligible_members = []
            for member in members:
                # Check if member is available for all days in the week
                rest_set = member_rest_days.get(member.id, set())
                
                # Member must be available on all week days (Mon-Sat)
                is_available_all_week = all(
                    member.is_available_on(d) and (d not in rest_set)
                    for d in week_dates
                )
                
                if is_available_all_week:
                    eligible_members.append(member)
            
            if len(eligible_members) < 2:
                self.audit.log(f"WARNING: Week {week_start} - Insufficient eligible members for SysAid (need 2, found {len(eligible_members)})")
                current_date = week_end + timedelta(days=1)
                continue
            
            # Select maker and checker based on fairness
            maker = self._select_assignee(eligible_members, TaskType.SYSAID_MAKER, week_start)
            eligible_no_maker = [m for m in eligible_members if m.id != maker.id]
            checker = self._select_assignee(eligible_no_maker, TaskType.SYSAID_CHECKER, week_start)
            
            # Create assignments for the week
            for week_date in week_dates:
                if week_date <= end_date:
                    assignments.append(Assignment(
                        task_type=TaskType.SYSAID_MAKER,
                        assignee=maker,
                        date=week_date,
                        week_start=week_start,
                        shift_label=f"Maker duty (week of {week_start.isoformat()})"
                    ))
                    assignments.append(Assignment(
                        task_type=TaskType.SYSAID_CHECKER,
                        assignee=checker,
                        date=week_date,
                        week_start=week_start,
                        shift_label=f"Checker duty (week of {week_start.isoformat()})"
                    ))
            
            self.audit.log(f"Week {week_start} - Assigned {maker.name} (Maker) and {checker.name} (Checker)")
            
            # Update ledger (count once per week, not per day)
            self.ledger.increment(maker.id, TaskType.SYSAID_MAKER)
            self.ledger.increment(checker.id, TaskType.SYSAID_CHECKER)
            
            current_date = week_end + timedelta(days=1)
        
        return assignments
    
    def _schedule_daily_task_type(
        self,
        members: List[TeamMember],
        task_type: DynamicTaskType,
        start_date: date,
        end_date: date,
        existing_schedule: Schedule
    ) -> List[Assignment]:
        """Schedule a daily task type from database."""
        assignments = []
        current_date = start_date
        
        while current_date <= end_date:
            weekday = current_date.weekday()
            shifts = task_type.get_shifts_for_weekday(weekday)
            assigned_today = {a.assignee.id for a in assignments if a.date == current_date}
            
            # Also check existing schedule for conflicts
            existing_today = {a.assignee.id for a in existing_schedule.assignments if a.date == current_date}
            assigned_today.update(existing_today)
            
            for shift in shifts:
                # Get eligible members for this shift
                eligible = self._get_eligible_members_for_dynamic_task(
                    members, current_date, task_type, shift, existing_schedule, assignments
                )
                eligible = [m for m in eligible if m.id not in assigned_today]
                
                if not eligible:
                    self.audit.log(f"WARNING: {current_date} - No eligible members for {task_type.name} - {shift.label}")
                    continue
                
                # Select assignee based on improved fairness algorithm
                assignee = self._select_assignee_for_dynamic_task_improved(eligible, task_type, current_date, [])
                
                # Create assignment for dynamic task
                # Use the task type name (string) as the stored task identifier for dynamic tasks
                assignments.append(Assignment(
                    task_type=task_type.name,
                    assignee=assignee,
                    date=current_date,
                    shift_label=f"{task_type.name} - {shift.label}",
                    custom_task_name=task_type.name,
                    custom_task_shift=shift.label,
                    recurrence=task_type.recurrence
                ))
                assigned_today.add(assignee.id)
                
                # Handle rest day if required
                if shift.requires_rest:
                    rest_day = calculate_rest_day(current_date)
                    if rest_day:
                        self.audit.log(f"{current_date} - Assigned {assignee.name} to {task_type.name} - {shift.label}. Rest on {rest_day}")
                    else:
                        self.audit.log(f"{current_date} - Assigned {assignee.name} to {task_type.name} - {shift.label} (no rest day)")
                else:
                    self.audit.log(f"{current_date} - Assigned {assignee.name} to {task_type.name} - {shift.label}")
                
                # Update fairness ledger (using task type name as key)
                self._increment_fairness_for_dynamic_task(assignee.id, task_type)
            
            current_date += timedelta(days=1)
        
        return assignments
    
    def _schedule_weekly_task_type(
        self,
        members: List[TeamMember],
        task_type: DynamicTaskType,
        start_date: date,
        end_date: date,
        existing_schedule: Schedule
    ) -> List[Assignment]:
        """Schedule a weekly task type from database."""
        assignments = []
        
        # Get week start day from rules or default to Monday
        week_start_day = task_type.rules_json.get("week_start_day", 0) if task_type.rules_json else 0
        
        # Build rest days map from existing assignments
        member_rest_days = {}
        for a in existing_schedule.assignments:
            if a.shift_label and task_type.name in a.shift_label:
                # Check if this assignment requires rest
                # We'll need to track this in the assignment or check shift definition
                rd = calculate_rest_day(a.date)
                if rd:
                    member_rest_days.setdefault(a.assignee.id, set()).add(rd)
        
        current_date = start_date
        while current_date <= end_date:
            # Find week start
            days_since_week_start = current_date.weekday() - week_start_day
            if days_since_week_start < 0:
                days_since_week_start += 7
            week_start = current_date - timedelta(days=days_since_week_start)
            week_end = week_start + timedelta(days=6)
            
            # Skip if already processed
            if any(a.week_start == week_start for a in assignments if hasattr(a, 'week_start')):
                current_date = week_end + timedelta(days=1)
                continue
            
            # Get week dates (exclude Sunday if configured)
            exclude_sunday = task_type.rules_json.get("exclude_sunday", True) if task_type.rules_json else True
            week_dates = [week_start + timedelta(days=i) for i in range(6 if exclude_sunday else 7)]
            
            # Find eligible members
            eligible_members = []
            for member in members:
                rest_set = member_rest_days.get(member.id, set())
                is_available_all_week = all(
                    member.is_available_on(d) and (d not in rest_set)
                    for d in week_dates
                )
                if is_available_all_week:
                    eligible_members.append(member)
            
            if len(eligible_members) < task_type.required_count:
                self.audit.log(f"WARNING: Week {week_start} - Insufficient eligible members for {task_type.name} (need {task_type.required_count}, found {len(eligible_members)})")
                current_date = week_end + timedelta(days=1)
                continue
            
            # Select assignees based on role labels or required count with improved fairness
            # For weekly tasks, we want to ensure equal distribution across all weeks
            selected_members = []
            for i in range(task_type.required_count):
                if i < len(eligible_members):
                    # Select based on improved fairness algorithm
                    remaining = [m for m in eligible_members if m.id not in [s.id for s in selected_members]]
                    if remaining:
                        # Use improved selection that ensures fairness
                        selected = self._select_assignee_for_dynamic_task_improved(
                            remaining, task_type, week_start, selected_members
                        )
                        selected_members.append(selected)
            
            # Create assignments for the week
            for week_date in week_dates:
                if week_date <= end_date:
                    for idx, member in enumerate(selected_members):
                        role_label = task_type.role_labels[idx] if idx < len(task_type.role_labels) else f"Role {idx+1}"
                        assignments.append(Assignment(
                            task_type=task_type.name,
                            assignee=member,
                            date=week_date,
                            week_start=week_start,
                            shift_label=f"{task_type.name} - {role_label} (week of {week_start.isoformat()})",
                            custom_task_name=task_type.name,
                            custom_task_shift=role_label,
                            recurrence=task_type.recurrence
                        ))
                        self._increment_fairness_for_dynamic_task(member.id, task_type)
            
            self.audit.log(f"Week {week_start} - Assigned {len(selected_members)} members to {task_type.name}")
            current_date = week_end + timedelta(days=1)
        
        return assignments
    
    def _schedule_monthly_task_type(
        self,
        members: List[TeamMember],
        task_type: DynamicTaskType,
        start_date: date,
        end_date: date,
        existing_schedule: Schedule
    ) -> List[Assignment]:
        """Schedule a monthly task type from database with equal distribution."""
        assignments = []
        
        # Determine scheduling day: can be an integer day (1..31), negative (e.g. -1 means last day),
        # or the string 'EOM' / 'eom' to indicate end-of-month. Default to 1st.
        raw_dom = None
        if task_type.rules_json:
            raw_dom = task_type.rules_json.get("day_of_month", None)
            # Some task definitions may use a boolean flag for end-of-month
            if raw_dom is None and task_type.rules_json.get("eom"):
                raw_dom = "EOM"
        if raw_dom is None:
            day_of_month = 1
            eom = False
        else:
            if isinstance(raw_dom, str) and raw_dom.strip().upper() == "EOM":
                eom = True
                day_of_month = None
            elif isinstance(raw_dom, int) and raw_dom < 0:
                # negative indexing like -1 means last day
                eom = True
                day_of_month = None
            else:
                try:
                    day_of_month = int(raw_dom)
                    eom = False
                except Exception:
                    # fallback to 1st
                    day_of_month = 1
                    eom = False

        # First, collect all dates that need assignments by iterating months
        dates_to_schedule = []
        year = start_date.year
        month = start_date.month
        # iterate months until we pass end_date
        cur = date(year, month, 1)
        while cur <= end_date:
            if eom:
                last_day = calendar.monthrange(cur.year, cur.month)[1]
                candidate = date(cur.year, cur.month, last_day)
            else:
                # ensure day exists in this month; if not, skip (e.g., 31st on short months)
                try:
                    candidate = date(cur.year, cur.month, day_of_month)
                except ValueError:
                    # invalid day for month
                    cur = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
                    continue

            # If candidate falls on weekend, adjust to previous Friday or next Monday
            adjusted = candidate
            # Saturday == 5, Sunday == 6
            if candidate.weekday() == 5:
                # Saturday: prefer previous Friday, else next Monday
                prev_friday = candidate - timedelta(days=1)
                next_monday = candidate + timedelta(days=2)
                if prev_friday >= start_date:
                    adjusted = prev_friday
                elif next_monday <= end_date:
                    adjusted = next_monday
                else:
                    # no valid fallback within range
                    self.audit.log(f"{candidate} falls on Saturday and no fallback within range; skipping")
                    adjusted = None
            elif candidate.weekday() == 6:
                # Sunday: prefer next Monday, else previous Friday
                next_monday = candidate + timedelta(days=1)
                prev_friday = candidate - timedelta(days=2)
                if next_monday <= end_date:
                    adjusted = next_monday
                elif prev_friday >= start_date:
                    adjusted = prev_friday
                else:
                    self.audit.log(f"{candidate} falls on Sunday and no fallback within range; skipping")
                    adjusted = None

            if adjusted and adjusted >= start_date and adjusted <= end_date:
                # avoid duplicates if adjustment causes same date twice
                if adjusted not in dates_to_schedule:
                    if adjusted != candidate:
                        self.audit.log(f"Adjusted monthly candidate {candidate} -> {adjusted}")
                    dates_to_schedule.append(adjusted)

            # advance to first of next month
            next_month = cur.month + 1
            next_year = cur.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            cur = date(next_year, next_month, 1)
        
        if not dates_to_schedule:
            return assignments
        
        # Calculate total slots needed (dates * shifts per date)
        total_slots = 0
        for schedule_date in dates_to_schedule:
            shifts = task_type.get_shifts_for_weekday(schedule_date.weekday())
            total_slots += len(shifts)
        
        # For equal distribution: calculate how many assignments each member should get
        # This ensures fairness when members > slots or slots > members
        num_members = len(members)
        if num_members == 0:
            return assignments
        
        # Calculate target assignments per member for equal distribution
        base_assignments = total_slots // num_members
        extra_assignments = total_slots % num_members
        
        # Track how many assignments each member has received
        member_assignment_counts = {m.id: 0 for m in members}
        
        # Sort members by current fairness count (ascending) for initial ordering
        members_sorted = sorted(members, key=lambda m: self._get_fairness_count_for_dynamic_task(m.id, task_type))
        
        # Process each date
        for schedule_date in dates_to_schedule:
            shifts = task_type.get_shifts_for_weekday(schedule_date.weekday())
            assigned_today = {a.assignee.id for a in assignments if a.date == schedule_date}
            existing_today = {a.assignee.id for a in existing_schedule.assignments if a.date == schedule_date}
            assigned_today.update(existing_today)
            
            for shift in shifts:
                # Get eligible members
                eligible = self._get_eligible_members_for_dynamic_task(
                    members, schedule_date, task_type, shift, existing_schedule, assignments
                )
                eligible = [m for m in eligible if m.id not in assigned_today]
                
                if not eligible:
                    self.audit.log(f"WARNING: {schedule_date} - No eligible members for {task_type.name} - {shift.label}")
                    continue
                
                # Select assignee with improved fairness algorithm
                # Prioritize members who haven't reached their target assignment count
                target_scores = []
                for member in eligible:
                    current_count = member_assignment_counts[member.id]
                    fairness_count = self._get_fairness_count_for_dynamic_task(member.id, task_type)
                    
                    # Calculate target for this member
                    member_index = next(i for i, m in enumerate(members_sorted) if m.id == member.id)
                    target = base_assignments + (1 if member_index < extra_assignments else 0)
                    
                    # Score: lower is better
                    # Primary: how far below target (negative means below target, positive means above)
                    # Secondary: fairness count
                    # Tertiary: total count
                    score = (current_count - target, fairness_count, self.ledger.get_total_count(member.id))
                    target_scores.append((score, member))
                
                # Sort by score (lower is better)
                target_scores.sort(key=lambda x: x[0])
                assignee = target_scores[0][1]
                
                assignments.append(Assignment(
                    task_type=task_type.name,
                    assignee=assignee,
                    date=schedule_date,
                    shift_label=f"{task_type.name} - {shift.label}",
                    custom_task_name=task_type.name,
                    custom_task_shift=shift.label,
                    recurrence=task_type.recurrence
                ))
                assigned_today.add(assignee.id)
                member_assignment_counts[assignee.id] += 1
                self._increment_fairness_for_dynamic_task(assignee.id, task_type)
        
        return assignments
    
    def _get_eligible_members_for_dynamic_task(
        self,
        members: List[TeamMember],
        check_date: date,
        task_type: DynamicTaskType,
        shift: TaskTypeShift,
        existing_schedule: Schedule,
        new_assignments: List[Assignment]
    ) -> List[TeamMember]:
        """Get eligible members for a dynamic task type."""
        eligible = []
        
        # Get rules from task type
        requires_office_days = task_type.rules_json.get("requires_office_days", True) if task_type.rules_json else True
        
        for member in members:
            # Check availability
            if requires_office_days:
                if not member.is_available_on(check_date):
                    continue
            else:
                # Allow any day unless explicitly unavailable
                if check_date in member.unavailable_dates:
                    continue
                if any(start <= check_date <= end for start, end in member.unavailable_ranges):
                    continue
            
            # Check rest days if shift requires rest
            if shift.requires_rest:
                # Check if member has rest day on check_date from previous assignments
                has_rest = any(
                    is_rest_day(check_date, a.date)
                    for a in existing_schedule.assignments + new_assignments
                    if a.assignee.id == member.id and a.shift_label and task_type.name in a.shift_label
                )
                if has_rest:
                    continue
            
            eligible.append(member)
        
        return eligible
    
    def _select_assignee_for_dynamic_task(
        self,
        eligible_members: List[TeamMember],
        task_type: DynamicTaskType,
        assignment_date: date
    ) -> TeamMember:
        """Select assignee for dynamic task type based on fairness."""
        if not eligible_members:
            raise ValueError("No eligible members available")
        
        if len(eligible_members) == 1:
            return eligible_members[0]
        
        # Calculate fairness scores using task type name as identifier
        scores = []
        for member in eligible_members:
            count = self._get_fairness_count_for_dynamic_task(member.id, task_type)
            total_count = self.ledger.get_total_count(member.id)
            scores.append((count, total_count, member))
        
        scores.sort(key=lambda x: (x[0], x[1]))
        best_score = scores[0][0]
        best_members = [s[2] for s in scores if s[0] == best_score]
        
        if len(best_members) > 1:
            tie_breaker = hash((assignment_date.isoformat(), task_type.name)) % len(best_members)
            selected = best_members[tie_breaker]
        else:
            selected = best_members[0]
        
        return selected

    def _select_assignee_for_dynamic_task_improved(
        self,
        eligible_members: List[TeamMember],
        task_type: DynamicTaskType,
        assignment_date: date,
        already_selected: List[TeamMember]
    ) -> TeamMember:
        """Improved selection for dynamic tasks.

        Prioritizes members with lower dynamic fairness count for the task type,
        then by total ledger count. Avoids members already in `already_selected`.
        Uses deterministic tie-breaker based on date and task name.
        """
        if not eligible_members:
            raise ValueError("No eligible members available")

        # Filter out any already_selected members first if possible
        remaining = [m for m in eligible_members if m.id not in {s.id for s in already_selected}]
        candidates = remaining if remaining else eligible_members

        if len(candidates) == 1:
            return candidates[0]

        scores = []
        for member in candidates:
            dyn_count = self._get_fairness_count_for_dynamic_task(member.id, task_type)
            total = self.ledger.get_total_count(member.id)
            # lower is better
            scores.append((dyn_count, total, member))

        scores.sort(key=lambda x: (x[0], x[1]))
        best_score = scores[0][0]
        best_members = [s[2] for s in scores if s[0] == best_score]

        if len(best_members) > 1:
            tie_breaker = hash((assignment_date.isoformat(), task_type.name)) % len(best_members)
            selected = best_members[tie_breaker]
            self.audit.log(f"Tie-break for {task_type.name} on {assignment_date}: selected {selected.name} from {len(best_members)} candidates")
        else:
            selected = best_members[0]

        self.audit.log(f"Selected {selected.name} for {task_type.name} on {assignment_date} (dyn_count={self._get_fairness_count_for_dynamic_task(selected.id, task_type)})")
        return selected
    
    def _get_fairness_count_for_dynamic_task(self, member_id: str, task_type: DynamicTaskType) -> int:
        """Get fairness count for a dynamic task type."""
        if task_type.name not in self.dynamic_task_counts:
            return 0
        return self.dynamic_task_counts[task_type.name].get(member_id, 0)
    
    def _increment_fairness_for_dynamic_task(self, member_id: str, task_type: DynamicTaskType):
        """Increment fairness count for a dynamic task type."""
        if task_type.name not in self.dynamic_task_counts:
            self.dynamic_task_counts[task_type.name] = {}
        if member_id not in self.dynamic_task_counts[task_type.name]:
            self.dynamic_task_counts[task_type.name][member_id] = 0
        self.dynamic_task_counts[task_type.name][member_id] += 1
    
    def _get_eligible_members(
        self,
        members: List[TeamMember],
        check_date: date,
        task_type: TaskType,
        existing_assignments: List[Assignment]
    ) -> List[TeamMember]:
        """Get members eligible for a task on a specific date."""
        eligible = []
        
        for member in members:
            # For ATM tasks, check availability but allow Sunday even if not in office_days
            # (ATM monitoring is 24/7, so we bypass office_days check for ATM)
            if task_type in {TaskType.ATM_MORNING, TaskType.ATM_MIDNIGHT}:
                # Check unavailable dates/ranges, but allow Sunday even if not in office_days
                if check_date in member.unavailable_dates:
                    continue
                # Check if date falls in any unavailable range
                is_in_unavailable_range = any(
                    start <= check_date <= end
                    for start, end in member.unavailable_ranges
                )
                if is_in_unavailable_range:
                    continue
                # For ATM, we allow any day (including Sunday) unless explicitly unavailable
            else:
                # For SysAid, use normal availability check (must be in office_days)
                if not member.is_available_on(check_date):
                    continue

            # If rest rule applies: a member who did ATM_MIDNIGHT on D must rest on the calculated rest day for ALL ATM tasks
            if self.config.atm_rest_rule_enabled and task_type in {TaskType.ATM_MORNING, TaskType.ATM_MIDNIGHT}:
                # Check if member has a rest day on check_date from any previous ATM_MIDNIGHT assignment
                has_rest_day = any(
                    a.task_type == TaskType.ATM_MIDNIGHT 
                    and a.assignee.id == member.id 
                    and is_rest_day(check_date, a.date)
                    for a in existing_assignments
                )
                if has_rest_day:
                    continue
            
            # For B-shift, check cooldown (avoid consecutive B-shifts)
            if task_type == TaskType.ATM_MIDNIGHT:
                recent_b_assignments = [
                    a for a in existing_assignments
                    if (
                        (a.task_type == TaskType.ATM_MIDNIGHT) or 
                        (isinstance(a.task_type, str) and a.task_type == TaskType.ATM_MIDNIGHT.value)
                    ) and a.assignee.id == member.id
                    and (check_date - a.date).days <= self.config.atm_b_cooldown_days
                ]
                if recent_b_assignments:
                    continue
            
            eligible.append(member)
        
        return eligible
    
    def _select_assignee(
        self,
        eligible_members: List[TeamMember],
        task_type: TaskType,
        assignment_date: date
    ) -> TeamMember:
        """Select the most fair assignee from eligible members."""
        if not eligible_members:
            raise ValueError("No eligible members available")
        
        if len(eligible_members) == 1:
            return eligible_members[0]
        
        # Calculate fairness scores (lower is better)
        scores = []
        for member in eligible_members:
            count = self.ledger.get_count(member.id, task_type)
            total_count = self.ledger.get_total_count(member.id)
            # Primary: task-specific count, secondary: total count
            scores.append((count, total_count, member))
        
        # Sort by count (ascending), then by total count
        scores.sort(key=lambda x: (x[0], x[1]))
        
        # Get the best score
        best_score = scores[0][0]
        best_members = [s[2] for s in scores if s[0] == best_score]
        
        # If tie, use deterministic selection based on date and member IDs
        if len(best_members) > 1:
            # Use date as seed for consistent tie-breaking
            tie_breaker = hash((assignment_date.isoformat(), task_type.value)) % len(best_members)
            selected = best_members[tie_breaker]
            self.audit.log(f"Tie-break for {task_type.value} on {assignment_date}: selected {selected.name} from {len(best_members)} candidates")
        else:
            selected = best_members[0]
        
        self.audit.log(f"Selected {selected.name} for {task_type.value} on {assignment_date} (count: {self.ledger.get_count(selected.id, task_type)})")
        return selected

