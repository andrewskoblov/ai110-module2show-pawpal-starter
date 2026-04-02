"""
PawPal+ pytest suite
Run with: pytest test_pawpal.py -v
"""

import pytest
from pawpal_system import Task, Pet, Owner, Scheduler, ScheduledTask, minutes_to_time_str


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

class TestTask:
    def test_valid_task_creation(self):
        t = Task("Walk", 30, "high", "walk")
        assert t.title == "Walk"
        assert t.duration_minutes == 30
        assert t.priority == "high"
        assert t.priority_score == 3

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError):
            Task("Walk", 30, "urgent")

    def test_zero_duration_raises(self):
        with pytest.raises(ValueError):
            Task("Walk", 0)

    def test_negative_duration_raises(self):
        with pytest.raises(ValueError):
            Task("Walk", -5)

    def test_priority_scores(self):
        assert Task("a", 5, "high").priority_score == 3
        assert Task("b", 5, "medium").priority_score == 2
        assert Task("c", 5, "low").priority_score == 1


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

class TestPet:
    def test_add_task(self):
        p = Pet("Mochi", "dog")
        p.add_task(Task("Walk", 30, "high"))
        assert len(p.tasks) == 1

    def test_remove_task_success(self):
        p = Pet("Mochi", "dog")
        p.add_task(Task("Walk", 30, "high"))
        removed = p.remove_task("Walk")
        assert removed is True
        assert len(p.tasks) == 0

    def test_remove_task_not_found(self):
        p = Pet("Mochi", "dog")
        removed = p.remove_task("Nonexistent")
        assert removed is False

    def test_total_task_minutes(self):
        p = Pet("Mochi", "dog")
        p.add_task(Task("Walk", 30, "high"))
        p.add_task(Task("Feed", 10, "medium"))
        assert p.total_task_minutes() == 40

    def test_get_tasks_by_priority(self):
        p = Pet("Mochi", "dog")
        p.add_task(Task("Walk", 30, "high"))
        p.add_task(Task("Feed", 10, "medium"))
        p.add_task(Task("Play", 20, "high"))
        high = p.get_tasks_by_priority("high")
        assert len(high) == 2


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

class TestOwner:
    def test_add_pet(self):
        o = Owner("Jordan", 120)
        o.add_pet(Pet("Mochi", "dog"))
        assert len(o.pets) == 1

    def test_all_tasks_across_pets(self):
        o = Owner("Jordan", 120)
        p1 = Pet("Mochi", "dog")
        p1.add_task(Task("Walk", 30, "high"))
        p2 = Pet("Luna", "cat")
        p2.add_task(Task("Feed", 10, "medium"))
        o.add_pet(p1)
        o.add_pet(p2)
        assert len(o.all_tasks()) == 2

    def test_total_requested_minutes(self):
        o = Owner("Jordan", 120)
        p = Pet("Mochi", "dog")
        p.add_task(Task("Walk", 30, "high"))
        p.add_task(Task("Feed", 10, "medium"))
        o.add_pet(p)
        assert o.total_requested_minutes() == 40


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

class TestScheduler:
    def _make_owner_with_tasks(self, available=120):
        owner = Owner("Jordan", available)
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Walk", 30, "high", "walk", "morning"))
        pet.add_task(Task("Feed", 10, "high", "feeding", "morning"))
        pet.add_task(Task("Play", 20, "medium", "enrichment", "afternoon"))
        pet.add_task(Task("Groom", 15, "low", "grooming"))
        owner.add_pet(pet)
        return owner

    def test_schedule_returns_list(self):
        owner = self._make_owner_with_tasks()
        s = Scheduler(owner)
        result = s.generate_schedule()
        assert isinstance(result, list)

    def test_schedule_respects_available_time(self):
        owner = self._make_owner_with_tasks(available=40)
        s = Scheduler(owner)
        result = s.generate_schedule()
        total = sum(st.task.duration_minutes for st in result)
        assert total <= 40

    def test_schedule_high_priority_first(self):
        owner = self._make_owner_with_tasks(available=60)
        s = Scheduler(owner)
        result = s.generate_schedule()
        titles = [st.task.title for st in result]
        # Walk (high, 30min) and Feed (high, 10min) should be scheduled before Play (medium)
        if "Walk" in titles and "Play" in titles:
            assert titles.index("Walk") < titles.index("Play")

    def test_schedule_no_day_overflow(self):
        """No task should end after 20:00 (1200 min from midnight)."""
        owner = self._make_owner_with_tasks(available=300)
        s = Scheduler(owner)
        result = s.generate_schedule()
        for st in result:
            assert st.end_minutes <= 1200, f"{st.task.title} ends after 20:00"

    def test_no_conflicts_when_enough_time(self):
        owner = self._make_owner_with_tasks(available=120)
        s = Scheduler(owner)
        conflicts = s.detect_conflicts()
        assert conflicts == []

    def test_conflict_detected_when_time_exceeded(self):
        owner = self._make_owner_with_tasks(available=10)  # way too little time
        s = Scheduler(owner)
        conflicts = s.detect_conflicts()
        assert len(conflicts) > 0
        assert any("exceeds" in c for c in conflicts)

    def test_explain_plan_not_empty(self):
        owner = self._make_owner_with_tasks()
        s = Scheduler(owner)
        plan = s.generate_schedule()
        explanation = s.explain_plan(plan)
        assert isinstance(explanation, str)
        assert len(explanation) > 0

    def test_explain_plan_empty_schedule(self):
        owner = Owner("Jordan", 1)  # 1 minute available — nothing fits
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Walk", 30, "high"))
        owner.add_pet(pet)
        s = Scheduler(owner)
        plan = s.generate_schedule()
        explanation = s.explain_plan(plan)
        assert "No tasks" in explanation

    def test_time_of_day_morning_preference(self):
        owner = Owner("Jordan", 120)
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Morning walk", 30, "high", "walk", "morning"))
        owner.add_pet(pet)
        s = Scheduler(owner)
        result = s.generate_schedule()
        assert len(result) == 1
        # Should start at or after 08:00 (480 min)
        assert result[0].start_minutes >= 480
        # Should start before 12:00 (720 min) for morning preference
        assert result[0].start_minutes < 720

    def test_scheduled_task_time_strings(self):
        st = ScheduledTask(Task("Walk", 30), start_minutes=480)
        assert st.start_time_str == "8:00 AM"
        assert st.end_time_str == "8:30 AM"


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------

class TestUtilities:
    def test_minutes_to_time_str_morning(self):
        assert minutes_to_time_str(480) == "8:00 AM"

    def test_minutes_to_time_str_noon(self):
        assert minutes_to_time_str(720) == "12:00 PM"

    def test_minutes_to_time_str_evening(self):
        assert minutes_to_time_str(1020) == "5:00 PM"

    def test_minutes_to_time_str_midnight(self):
        assert minutes_to_time_str(0) == "12:00 AM"
