"""Core scheduling logic for ATM and SysAid tasks."""

from datetime import date, timedelta
from typing import List, Optional, Set, Tuple
from .models import TeamMember, Assignment, TaskType, Schedule, FairnessLedger
from .config import SchedulingConfig

ATM_SHIFT_PLAN = {
    0: [  # Monday
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    1: [
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    2: [
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    3: [
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    4: [
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Mid/Night (13:00-22:00)", "rest_next_day": True},
    ],
    5: [  # Saturday
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Midday (06:00)", "rest_next_day": True},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Midday (11:00)", "rest_next_day": True},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Night (16:00)", "rest_next_day": True},
    ],
    6: [  # Sunday
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (07:30)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MORNING, "label": "Morning (09:00)", "rest_next_day": False},
        {"task_type": TaskType.ATM_MIDNIGHT, "label": "Night (16:00)", "rest_next_day": True},
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
    
    def __init__(self, config: SchedulingConfig, ledger: Optional[FairnessLedger] = None):
        self.config = config
        self.ledger = ledger or FairnessLedger(fairness_window_days=config.fairness_window_days)
        self.audit = AuditLog()
    
    def generate_schedule(
        self,
        members: List[TeamMember],
        start_date: date,
        end_date: date
    ) -> Schedule:
        """Generate a complete schedule for the given date range."""
        schedule = Schedule(start_date=start_date, end_date=end_date)
        
        # Generate ATM schedule first (daily)
        atm_assignments = self._schedule_atm(members, start_date, end_date)
        schedule.assignments.extend(atm_assignments)
        
        # Generate SysAid schedule (weekly)
        sysaid_assignments = self._schedule_sysaid(members, start_date, end_date, schedule)
        schedule.assignments.extend(sysaid_assignments)
        
        return schedule
    
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
                    rest_day = current_date + timedelta(days=1)
                    self.audit.log(f"{current_date} - Assigned {assignee.name} to {label}. Rest on {rest_day}")
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
        b_assignments = [a for a in existing_schedule.assignments if a.task_type == TaskType.ATM_MIDNIGHT]
        member_rest_days = {}
        for a in b_assignments:
            rd = a.date + timedelta(days=1)
            member_rest_days.setdefault(a.assignee.id, set()).add(rd)

        # Map ATM assignments by date to avoid double-booking with SysAid
        atm_by_date = {}
        for a in existing_schedule.assignments:
            if a.task_type in {TaskType.ATM_MORNING, TaskType.ATM_MIDNIGHT}:
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
            # Relaxed: allow members who have some ATM assignments but not on all days
            eligible_members = []
            for member in members:
                # Check if member is available for all days in the week
                rest_set = member_rest_days.get(member.id, set())
                atm_days_for_member = {d for d in week_dates if member.id in atm_by_date.get(d, set())}
                
                # Member must be available on all week days (Mon-Sat)
                is_available_all_week = all(
                    member.is_available_on(d) and (d not in rest_set)
                    for d in week_dates
                )
                
                # Allow members even if they have some ATM assignments, as long as they're available
                # The constraint is: they must be available (not resting, not unavailable) on all week days
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

            # If rest rule applies: a member who did ATM_MIDNIGHT on D must rest on D+1 for ALL ATM tasks
            if self.config.atm_rest_rule_enabled and task_type in {TaskType.ATM_MORNING, TaskType.ATM_MIDNIGHT}:
                had_b_previous_day = any(
                    a.task_type == TaskType.ATM_MIDNIGHT and a.assignee.id == member.id and (check_date - a.date).days == 1
                    for a in existing_assignments
                )
                if had_b_previous_day:
                    continue
            
            # For B-shift, check cooldown (avoid consecutive B-shifts)
            if task_type == TaskType.ATM_MIDNIGHT:
                recent_b_assignments = [
                    a for a in existing_assignments
                    if a.task_type == TaskType.ATM_MIDNIGHT
                    and a.assignee.id == member.id
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

