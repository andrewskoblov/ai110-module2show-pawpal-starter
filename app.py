import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — powered by priority-based planning")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "tasks" not in st.session_state:
    st.session_state.tasks = []   # list of dicts
if "schedule" not in st.session_state:
    st.session_state.schedule = []
if "explanation" not in st.session_state:
    st.session_state.explanation = ""
if "conflicts" not in st.session_state:
    st.session_state.conflicts = []

# ---------------------------------------------------------------------------
# Section 1: Owner + Pet info
# ---------------------------------------------------------------------------

st.header("1. Owner & Pet Info")

col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
    available_minutes = st.number_input(
        "Available time today (minutes)", min_value=10, max_value=480, value=120, step=5
    )
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    pet_age = st.number_input("Pet age (years)", min_value=0, max_value=30, value=3)

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Task Management
# ---------------------------------------------------------------------------

st.header("2. Add Tasks")

with st.form("add_task_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        task_title = st.text_input("Task title", value="Morning walk")
        category = st.selectbox(
            "Category",
            ["walk", "feeding", "medication", "grooming", "enrichment", "general"],
        )
    with c2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        time_of_day = st.selectbox(
            "Preferred time of day",
            ["any", "morning", "afternoon", "evening"],
        )
    with c3:
        priority = st.selectbox("Priority", ["high", "medium", "low"], index=1)
        notes = st.text_input("Notes (optional)", value="")

    submitted = st.form_submit_button("Add task")
    if submitted:
        if task_title.strip() == "":
            st.error("Task title cannot be empty.")
        else:
            st.session_state.tasks.append(
                {
                    "title": task_title.strip(),
                    "duration_minutes": int(duration),
                    "priority": priority,
                    "category": category,
                    "time_of_day": None if time_of_day == "any" else time_of_day,
                    "notes": notes.strip(),
                }
            )
            st.success(f"Added: {task_title.strip()}")

# Show current task list with delete buttons
if st.session_state.tasks:
    st.subheader("Current tasks")
    for i, t in enumerate(st.session_state.tasks):
        cols = st.columns([4, 1])
        with cols[0]:
            tod = t["time_of_day"] or "any time"
            st.markdown(
                f"**{t['title']}** — {t['duration_minutes']}min | "
                f"Priority: `{t['priority']}` | Category: `{t['category']}` | "
                f"Time: `{tod}`"
            )
        with cols[1]:
            if st.button("Remove", key=f"del_{i}"):
                st.session_state.tasks.pop(i)
                st.rerun()
else:
    st.info("No tasks yet. Add one above.")

# Quick-load default tasks
if st.button("Load sample tasks"):
    st.session_state.tasks = [
        {"title": "Morning walk",      "duration_minutes": 30,  "priority": "high",   "category": "walk",        "time_of_day": "morning",   "notes": ""},
        {"title": "Breakfast feeding", "duration_minutes": 10,  "priority": "high",   "category": "feeding",     "time_of_day": "morning",   "notes": ""},
        {"title": "Medication",        "duration_minutes": 5,   "priority": "high",   "category": "medication",  "time_of_day": "morning",   "notes": ""},
        {"title": "Afternoon play",    "duration_minutes": 20,  "priority": "medium", "category": "enrichment",  "time_of_day": "afternoon", "notes": ""},
        {"title": "Evening walk",      "duration_minutes": 25,  "priority": "medium", "category": "walk",        "time_of_day": "evening",   "notes": ""},
        {"title": "Grooming session",  "duration_minutes": 15,  "priority": "low",    "category": "grooming",    "time_of_day": None,        "notes": ""},
        {"title": "Training tricks",   "duration_minutes": 10,  "priority": "low",    "category": "enrichment",  "time_of_day": None,        "notes": ""},
    ]
    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Generate Schedule
# ---------------------------------------------------------------------------

st.header("3. Generate Daily Schedule")

if st.button("Generate schedule", type="primary", disabled=len(st.session_state.tasks) == 0):
    # Build domain objects
    owner = Owner(name=owner_name, available_minutes=int(available_minutes))
    pet = Pet(name=pet_name, species=species, age=int(pet_age))

    for t in st.session_state.tasks:
        pet.add_task(
            Task(
                title=t["title"],
                duration_minutes=t["duration_minutes"],
                priority=t["priority"],
                category=t["category"],
                time_of_day=t["time_of_day"],
                notes=t["notes"],
            )
        )
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    st.session_state.conflicts = scheduler.detect_conflicts()
    st.session_state.schedule = scheduler.generate_schedule()
    st.session_state.explanation = scheduler.explain_plan(st.session_state.schedule)

# Display conflicts
if st.session_state.conflicts:
    st.warning("**Scheduling conflicts detected:**")
    for c in st.session_state.conflicts:
        st.markdown(f"- {c}")

# Display the schedule
if st.session_state.schedule:
    st.success(f"Schedule generated: {len(st.session_state.schedule)} tasks planned")

    schedule_data = [
        {
            "Time": f"{s.start_time_str} - {s.end_time_str}",
            "Task": s.task.title,
            "Duration (min)": s.task.duration_minutes,
            "Priority": s.task.priority,
            "Category": s.task.category,
        }
        for s in st.session_state.schedule
    ]
    st.table(schedule_data)

    with st.expander("Why this schedule? (Full explanation)"):
        st.text(st.session_state.explanation)

    # Stats
    total_scheduled = sum(s.task.duration_minutes for s in st.session_state.schedule)
    total_requested = sum(t["duration_minutes"] for t in st.session_state.tasks)
    skipped = total_requested - total_scheduled

    c1, c2, c3 = st.columns(3)
    c1.metric("Time scheduled", f"{total_scheduled} min")
    c2.metric("Time available", f"{available_minutes} min")
    c3.metric("Time dropped", f"{skipped} min")

elif st.session_state.explanation and not st.session_state.schedule:
    st.error("No tasks could be scheduled. Try increasing available time or reducing task durations.")
