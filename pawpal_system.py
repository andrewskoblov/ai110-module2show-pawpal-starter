"""
PawPal+ Backend Logic
Classes: Task, Pet, Owner, Scheduler
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}

# Day starts at 8:00 AM (480 minutes from midnight)
DAY_START_MINUTES = 480  # 8:00 AM


def minutes_to_time_str(minutes_from_midnight: int) -> str:
    """Convert minutes from midnight to HH:MM AM/PM string."""
    h = (minutes_from_midnight // 60) % 24
    m = minutes_from_midnight % 60
    period = "AM" if h < 12 else "PM"
    display_h = h if h <= 12 else h - 12
    if display_h == 0:
        display_h = 12
    return f"{display_h}:{m:02d} {period}"


@dataclass
class Task:
    """Represents a single pet care task."""
    title: str
    duration_minutes: int
    priority: str = "medium"          # "low" | "medium" | "high"
    category: str = "general"         # walk, feeding, medication, grooming, enrichment, general
    time_of_day: Optional[str] = None  # "morning" | "afternoon" | "evening" | None (any)
    recurring: bool = True
    notes: str = ""

    def __post_init__(self):
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"Invalid priority '{self.priority}'. Use: low, medium, high.")
        if self.duration_minutes <= 0:
            raise ValueError("Duration must be a positive integer.")

    @property
    def priority_score(self) -> int:
        return PRIORITY_RANK[self.priority]

    def __repr__(self) -> str:
        return f"Task('{self.title}', {self.duration_minutes}min, {self.priority})"


@dataclass
class Pet:
    """Represents a pet with its care tasks."""
    name: str
    species: str
    age: int = 1
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.title != title]
        return len(self.tasks) < before

    def get_tasks_by_priority(self, priority: str) -> list[Task]:
        return [t for t in self.tasks if t.priority == priority]

    def total_task_minutes(self) -> int:
        return sum(t.duration_minutes for t in self.tasks)

    def __repr__(self) -> str:
        return f"Pet('{self.name}', {self.species}, {len(self.tasks)} tasks)"


@dataclass
class Owner:
    """Represents the pet owner with their schedule constraints."""
    name: str
    available_minutes: int = 120   # default: 2 hours per day
    pets: list[Pet] = field(default_factory=list)
    preferred_start_time: str = "8:00 AM"  # display only

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def all_tasks(self) -> list[Task]:
        """Return all tasks across all pets."""
        tasks = []
        for pet in self.pets:
            tasks.extend(pet.tasks)
        return tasks

    def total_requested_minutes(self) -> int:
        return sum(t.duration_minutes for t in self.all_tasks())

    def __repr__(self) -> str:
        return f"Owner('{self.name}', {self.available_minutes}min available, {len(self.pets)} pets)"


@dataclass
class ScheduledTask:
    """A task that has been placed in the daily plan."""
    task: Task
    start_minutes: int   # minutes from midnight
    reason: str = ""

    @property
    def end_minutes(self) -> int:
        return self.start_minutes + self.task.duration_minutes

    @property
    def start_time_str(self) -> str:
        return minutes_to_time_str(self.start_minutes)

    @property
    def end_time_str(self) -> str:
        return minutes_to_time_str(self.end_minutes)

    def __repr__(self) -> str:
        return f"{self.start_time_str} - {self.end_time_str}: {self.task.title}"


class Scheduler:
    """
    Schedules pet care tasks for a day.

    Algorithm:
    1. Sort tasks by priority (high >> medium >> low), then by duration (shortest first
       within same priority) to maximise the number of tasks that fit.
    2. Respect time-of-day preferences when assigning start times:
       morning  = 08:00 - 11:59
       afternoon = 12:00 - 16:59
       evening   = 17:00 - 20:00
    3. Greedily pack tasks back-to-back within the owner's available window.
    4. Detect conflicts: tasks that overflow the day window or exceed available time.
    """

    MORNING_START = 480    # 08:00
    AFTERNOON_START = 720  # 12:00
    EVENING_START = 1020   # 17:00
    DAY_END = 1200         # 20:00

    def __init__(self, owner: Owner):
        self.owner = owner

    # ------------------------------------------------------------------
    # Core scheduling
    # ------------------------------------------------------------------

    def _sorted_tasks(self) -> list[Task]:
        """Return all tasks sorted: priority desc, then duration asc (shorter first)."""
        return sorted(
            self.owner.all_tasks(),
            key=lambda t: (-t.priority_score, t.duration_minutes),
        )

    def _preferred_start(self, task: Task, current_cursor: int) -> int:
        """Return the earliest sensible start minute for a task given its time_of_day preference."""
        if task.time_of_day == "morning":
            return max(current_cursor, self.MORNING_START)
        if task.time_of_day == "afternoon":
            return max(current_cursor, self.AFTERNOON_START)
        if task.time_of_day == "evening":
            return max(current_cursor, self.EVENING_START)
        return current_cursor  # no preference >> pack immediately

    def generate_schedule(self) -> list[ScheduledTask]:
        """
        Build an ordered list of ScheduledTask objects fitting within the owner's
        available minutes and the day window (08:00-20:00).
        """
        schedule: list[ScheduledTask] = []
        minutes_used = 0
        cursor = self.MORNING_START

        for task in self._sorted_tasks():
            # Respect time-of-day preference
            start = self._preferred_start(task, cursor)

            # Check we still fit in the day and within owner's available budget
            fits_in_day = (start + task.duration_minutes) <= self.DAY_END
            fits_in_budget = (minutes_used + task.duration_minutes) <= self.owner.available_minutes

            if fits_in_day and fits_in_budget:
                reason = self._build_reason(task, minutes_used)
                schedule.append(ScheduledTask(task=task, start_minutes=start, reason=reason))
                cursor = start + task.duration_minutes
                minutes_used += task.duration_minutes

        return schedule

    def _build_reason(self, task: Task, minutes_used_so_far: int) -> str:
        remaining = self.owner.available_minutes - minutes_used_so_far
        parts = [f"Priority: {task.priority}."]
        if task.category != "general":
            parts.append(f"Category: {task.category}.")
        if task.time_of_day:
            parts.append(f"Preferred time: {task.time_of_day}.")
        parts.append(f"{remaining}min of budget remaining when scheduled.")
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self) -> list[str]:
        """Return a list of human-readable conflict messages."""
        conflicts: list[str] = []
        all_tasks = self.owner.all_tasks()

        total_requested = sum(t.duration_minutes for t in all_tasks)
        if total_requested > self.owner.available_minutes:
            overflow = total_requested - self.owner.available_minutes
            conflicts.append(
                f"Total task time ({total_requested}min) exceeds available time "
                f"({self.owner.available_minutes}min) by {overflow}min. "
                f"Some tasks will be dropped."
            )

        # Flag duplicate categories in high-priority tasks
        high_cats: list[str] = [t.category for t in all_tasks if t.priority == "high" and t.category != "general"]
        seen: set[str] = set()
        for cat in high_cats:
            if cat in seen:
                conflicts.append(f"Multiple high-priority tasks in category '{cat}'.")
            seen.add(cat)

        return conflicts

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    def explain_plan(self, schedule: list[ScheduledTask]) -> str:
        if not schedule:
            return "No tasks could be scheduled within the given constraints."

        lines = [
            f"Daily plan for {self.owner.name}'s pet(s) — "
            f"{sum(s.task.duration_minutes for s in schedule)}min of "
            f"{self.owner.available_minutes}min used:\n"
        ]
        for idx, s in enumerate(schedule, 1):
            lines.append(
                f"  {idx}. [{s.start_time_str} - {s.end_time_str}] "
                f"{s.task.title} ({s.task.duration_minutes}min)"
            )
            lines.append(f"     >> {s.reason}")

        skipped = [
            t for t in self.owner.all_tasks()
            if t.title not in {s.task.title for s in schedule}
        ]
        if skipped:
            lines.append("\nTasks NOT scheduled (time/budget exceeded):")
            for t in skipped:
                lines.append(f"  - {t.title} ({t.duration_minutes}min, {t.priority} priority)")

        return "\n".join(lines)
