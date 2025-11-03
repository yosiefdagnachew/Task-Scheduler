"""Core scheduling logic for ATM and SysAid tasks."""

from datetime import date, timedelta
from typing import List, Optional, Set, Tuple
from .models import TeamMember, Assignment, TaskType, Schedule, FairnessLedger
from .config import SchedulingConfig


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
        rest_days: Set[date] = set()  # Track rest days from previous B-shifts
        
        current_date = start_date
        while current_date <= end_date:
            # Get existing rest days from previous assignments
            for assignment in assignments:
                if assignment.task_type == TaskType.ATM_MIDNIGHT:
                    rest_day = assignment.date + timedelta(days=1)
                    if rest_day <= end_date:
                        rest_days.add(rest_day)
            
            # Skip if this is a rest day
            if current_date in rest_days:
                current_date += timedelta(days=1)
                continue
            
            # Find eligible members for this date
            eligible_for_a = self._get_eligible_members(
                members, current_date, TaskType.ATM_MORNING, rest_days, assignments
            )
            eligible_for_b = self._get_eligible_members(
                members, current_date, TaskType.ATM_MIDNIGHT, rest_days, assignments
            )
            
            # Remove members already assigned today
            assigned_today = {a.assignee.id for a in assignments if a.date == current_date}
            eligible_for_a = [m for m in eligible_for_a if m.id not in assigned_today]
            eligible_for_b = [m for m in eligible_for_b if m.id not in assigned_today]
            
            # Select assignees based on fairness
            if eligible_for_a and eligible_for_b:
                assignee_a = self._select_assignee(eligible_for_a, TaskType.ATM_MORNING, current_date)
                assignee_b = self._select_assignee(eligible_for_b, TaskType.ATM_MIDNIGHT, current_date)
                
                # Ensure A and B are different
                if assignee_a.id == assignee_b.id:
                    # If only one eligible member, skip this day
                    if len(eligible_for_a) == 1 and len(eligible_for_b) == 1:
                        self.audit.log(f"WARNING: {current_date} - Only one eligible member, skipping ATM assignment")
                        current_date += timedelta(days=1)
                        continue
                    # Swap B if needed
                    eligible_for_b_no_a = [m for m in eligible_for_b if m.id != assignee_a.id]
                    if eligible_for_b_no_a:
                        assignee_b = self._select_assignee(eligible_for_b_no_a, TaskType.ATM_MIDNIGHT, current_date)
                    else:
                        self.audit.log(f"WARNING: {current_date} - Cannot assign distinct A and B, skipping")
                        current_date += timedelta(days=1)
                        continue
                
                assignments.append(Assignment(
                    task_type=TaskType.ATM_MORNING,
                    assignee=assignee_a,
                    date=current_date
                ))
                assignments.append(Assignment(
                    task_type=TaskType.ATM_MIDNIGHT,
                    assignee=assignee_b,
                    date=current_date
                ))
                
                # Mark next day as rest day for B
                if self.config.atm_rest_rule_enabled:
                    rest_day = current_date + timedelta(days=1)
                    rest_days.add(rest_day)
                    self.audit.log(f"{current_date} - Assigned {assignee_a.name} (A) and {assignee_b.name} (B). {assignee_b.name} rests on {rest_day}")
                else:
                    self.audit.log(f"{current_date} - Assigned {assignee_a.name} (A) and {assignee_b.name} (B)")
                
                # Update ledger
                self.ledger.increment(assignee_a.id, TaskType.ATM_MORNING)
                self.ledger.increment(assignee_b.id, TaskType.ATM_MIDNIGHT)
            else:
                self.audit.log(f"WARNING: {current_date} - Insufficient eligible members for ATM assignment")
            
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
        # Get rest days from existing ATM assignments
        rest_days = existing_schedule.get_rest_days()
        
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
            
            # Check all days in the week for office presence
            week_dates = [week_start + timedelta(days=i) for i in range(7)]
            
            # Find eligible members (must be in office for all days of the week)
            eligible_members = []
            for member in members:
                # Check if member is available for all days in the week
                is_available_all_week = all(
                    member.is_available_on(d) and d not in rest_days
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
                        week_start=week_start
                    ))
                    assignments.append(Assignment(
                        task_type=TaskType.SYSAID_CHECKER,
                        assignee=checker,
                        date=week_date,
                        week_start=week_start
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
        rest_days: Set[date],
        existing_assignments: List[Assignment]
    ) -> List[TeamMember]:
        """Get members eligible for a task on a specific date."""
        eligible = []
        
        for member in members:
            # Must be available on the date
            if not member.is_available_on(check_date):
                continue
            
            # Must not be on rest day
            if check_date in rest_days:
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

