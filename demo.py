"""
PawPal+ CLI Demo
Run with: python demo.py
"""

from pawpal_system import Task, Pet, Owner, Scheduler


def main():
    print("=" * 55)
    print("  PawPal+ CLI Demo")
    print("=" * 55)

    # --- Build the owner ---
    owner = Owner(name="Jordan", available_minutes=120)

    # --- Build a pet with tasks ---
    mochi = Pet(name="Mochi", species="dog", age=3)

    mochi.add_task(Task("Morning walk",      30,  "high",   "walk",       "morning"))
    mochi.add_task(Task("Breakfast feeding", 10,  "high",   "feeding",    "morning"))
    mochi.add_task(Task("Medication",        5,   "high",   "medication", "morning"))
    mochi.add_task(Task("Afternoon play",    20,  "medium", "enrichment", "afternoon"))
    mochi.add_task(Task("Evening walk",      25,  "medium", "walk",       "evening"))
    mochi.add_task(Task("Grooming session",  15,  "low",    "grooming"))
    mochi.add_task(Task("Training tricks",   10,  "low",    "enrichment"))

    owner.add_pet(mochi)

    print(f"\nOwner : {owner}")
    print(f"Pet   : {mochi}")
    print(f"Total task time requested : {owner.total_requested_minutes()}min")
    print(f"Available time            : {owner.available_minutes}min")

    # --- Conflict detection ---
    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        print("\n[!] Conflicts detected:")
        for c in conflicts:
            print(f"   - {c}")
    else:
        print("\n[OK] No conflicts detected.")

    # --- Generate schedule ---
    schedule = scheduler.generate_schedule()

    print("\n" + "-" * 55)
    print(scheduler.explain_plan(schedule))
    print("-" * 55)


if __name__ == "__main__":
    main()
