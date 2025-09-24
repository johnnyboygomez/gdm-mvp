"""
Simulates real-world syncing delays: 
- Each user/dataset has a random (but contiguous) number of days with step data.
- The possible number of days is [days_ago-2, days_ago-1, days_ago], always contiguous from the earliest day.
- Goals: week 1 if at least 7 days; week 2 only for 14 days.
- UPDATED: Creates data in Fitbit format: [{"date": "2025-09-03", "value": 2941}, {"date": "2025-09-04", "value": 3008}]
- NEW: Adds realistic fluctuation with occasional "off days" and "great days"
- UPDATED: Now includes previous_target field in expected goals
"""

from datetime import date, timedelta
import json
import random
import csv
import os

def generate_step_values(base_steps, variation=200, num_days=7):
    """Generate num_days of step values with realistic daily fluctuation."""
    values = []
    for day in range(num_days):
        # Start with normal variation
        steps = base_steps + random.randint(-variation, variation)
        
        # Add realistic fluctuation - some days are just different
        fluctuation_chance = random.random()
        
        if fluctuation_chance < 0.15:  # 15% chance of "off day"
            # Really low day (sick, busy, tired, etc.)
            off_day_reduction = random.randint(int(steps * 0.3), int(steps * 0.6))
            steps = max(steps - off_day_reduction, 500)  # Never below 500 steps
            
        elif fluctuation_chance < 0.25:  # 10% chance of "great day" 
            # Exceptionally active day (weekend hike, extra motivation, etc.)
            great_day_boost = random.randint(int(steps * 0.2), int(steps * 0.5))
            steps += great_day_boost
            
        elif fluctuation_chance < 0.35:  # 10% chance of "lazy day"
            # Moderately low day (rainy day, work from home, etc.)
            lazy_reduction = random.randint(int(steps * 0.1), int(steps * 0.25))
            steps = max(steps - lazy_reduction, 1000)
            
        elif fluctuation_chance < 0.45:  # 10% chance of "active day"
            # Moderately high day (nice weather, meeting friends, etc.)
            active_boost = random.randint(int(steps * 0.1), int(steps * 0.3))
            steps += active_boost
        
        # Weekend effect - people often have different patterns on weekends
        # Assuming start_date is known, we can simulate this
        if day % 7 in [5, 6]:  # Approximate weekend days (Sat, Sun)
            weekend_factor = random.choice([-0.15, -0.1, 0.1, 0.2, 0.3])  # Can go either way
            weekend_change = int(steps * weekend_factor)
            steps += weekend_change
        
        # Ensure minimum steps
        steps = max(1000, steps)
        values.append(steps)
    
    return values

def create_step_data(start_date, step_values):
    """Create step data in Fitbit format: [{"date": "2025-09-03", "value": 2941}]"""
    return [
        {
        #
            "date": (start_date + timedelta(days=day)).strftime("%Y-%m-%d"),
            "value": steps
        }
        for day, steps in enumerate(step_values)
    ]

def calculate_average(step_values):
    return sum(step_values) // len(step_values)

def predict_goal(average_steps, scenario="first_week", previous_target=None):
    """
    Predict goal with previous_target field included.
    
    Args:
        average_steps: Average steps for the week
        scenario: "first_week" or "second_week" 
        previous_target: The target from previous week (None for first week)
    
    Returns:
        dict: Goal data including previous_target field
    """
    if average_steps < 5000:
        goal_data = {"increase": "500", "new_target": average_steps + 500, "average_steps": average_steps}
    elif average_steps < 7500:
        goal_data = {"increase": "1000", "new_target": average_steps + 1000, "average_steps": average_steps}
    elif average_steps < 9000:
        goal_data = {"increase": "1000", "new_target": average_steps + 1000, "average_steps": average_steps}
    elif average_steps < 10000:
        goal_data = {"increase": "increase to 10000", "new_target": 10000, "average_steps": average_steps}
    else:
        goal_data = {"increase": "maintain", "new_target": average_steps, "average_steps": average_steps}
    
    # Add previous_target field (None for first week, actual value for subsequent weeks)
    goal_data["previous_target"] = previous_target
    
    return goal_data

def generate_test_data(num_datasets=20, seed=42, days_ago=14):
    random.seed(seed)
    activity_profiles = [
        {"name": "Sedentary", "base_range": (2000, 4000), "variation": (100, 300)},
        {"name": "Lightly_Active", "base_range": (4000, 6000), "variation": (150, 400)},
        {"name": "Moderately_Active", "base_range": (6000, 8000), "variation": (200, 500)},
        {"name": "Active", "base_range": (8000, 10000), "variation": (300, 600)},
        {"name": "Highly_Active", "base_range": (10000, 15000), "variation": (500, 1000)},
    ]
    all_test_results = {}
    yesterday = date.today() - timedelta(days=1)
    start_date = yesterday - timedelta(days=days_ago - 1)

    for i in range(num_datasets):
        profile = random.choice(activity_profiles)
        week1_base = random.randint(*profile["base_range"])
        variation = random.randint(*profile["variation"])
        # For each user, pick a random number of days in [days_ago-2, days_ago-1, days_ago]
        min_days = max(7, days_ago - 2)  # never less than 7
        max_days = days_ago
        actual_days = random.randint(min_days, max_days)
        step_values = generate_step_values(week1_base, variation, num_days=actual_days)
        step_data = create_step_data(start_date, step_values)
        test_name = f"Dataset_{i+1:02d}_{profile['name']}_{actual_days}days"

        expected_goals = {}
        previous_week_target = None  # Track previous target for chaining
        
        # Always calculate week 1 target if at least 7 days of data
        if actual_days >= 7:
            week1 = step_values[:7]
            week1_avg = calculate_average(week1)
            goal_date_1 = (start_date + timedelta(days=7)).strftime("%Y-%m-%d")
            week1_goal = predict_goal(week1_avg, "first_week", previous_target=None)
            expected_goals[goal_date_1] = week1_goal
            previous_week_target = week1_goal["new_target"]  # Store for next week
            
        # Only calculate week 2 target if there are 14 days
        if actual_days == 14:
            week2 = step_values[7:14]
            week2_avg = calculate_average(week2)
            goal_date_2 = (start_date + timedelta(days=14)).strftime("%Y-%m-%d")
            week2_goal = predict_goal(week2_avg, "second_week", previous_target=previous_week_target)
            expected_goals[goal_date_2] = week2_goal

        all_test_results[test_name] = {
            "step_data": step_data,
            "expected_goals": expected_goals,
            "actual_days": actual_days
        }
    return all_test_results

def save_to_csv(all_test_results, filename="step_goals_test_data.csv"):
    csv_data = []
    for test_name, results in all_test_results.items():
        row = {
            "test_pair": test_name,
            "actual_days": results["actual_days"],
            "data_json": json.dumps(results["step_data"]),
            "expected_goals_json": json.dumps(results["expected_goals"])
        }
        csv_data.append(row)
    fieldnames = ["test_pair", "actual_days", "data_json", "expected_goals_json"]
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()   # Only write header if new file
        writer.writerows(csv_data)
    return filename

def get_user_input():
    while True:
        try:
            seed = int(input("Please enter seed (1 to 99): "))
            if 1 <= seed <= 99:
                break
            else:
                print("Please enter a number between 1 and 99")
        except ValueError:
            print("Please enter a valid number")
    while True:
        try:
            datasets = int(input("Please enter number of datasets required (1 to 99): "))
            if 1 <= datasets <= 99:
                break
            else:
                print("Please enter a number between 1 and 99")
        except ValueError:
            print("Please enter a valid number")
    while True:
        try:
            days_ago = int(input("How many days ago should the data start? (12, 13, or 14 days): "))
            if 12 <= days_ago <= 14:
                break
            else:
                print("Please enter number of days: 12, 13 or 14")
        except ValueError:
            print("Please enter a valid number")
    return seed, datasets, days_ago

def main():
    print("Step Data Generator (with realistic daily fluctuation)")
    print("====================================================")
    seed, num_datasets, days_ago = get_user_input()
    output_filename = f"step_goals_datasets.csv"
    print(f"\nGenerating {num_datasets} datasets with seed {seed} and up to {days_ago} days of data each...")
    print("Features: Off days, great days, weekend effects, natural variation, and previous_target tracking")
    all_test_results = generate_test_data(num_datasets, seed, days_ago)
    filename = save_to_csv(all_test_results, output_filename)
    print(f"\n✅ Complete!")
    print(f"Generated {len(all_test_results)} datasets with {days_ago} possible days (each has 7 to {days_ago})")
    print(f"Each expected goal now includes previous_target field")
    print(f"Saved to: {filename}")

if __name__ == "__main__":
    main()