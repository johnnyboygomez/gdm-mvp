#!/usr/bin/env python3
"""
Test Data Generator - Following Your Exact Pattern

Creates 20 test datasets using your methodology:
1. Generate week of data → single goal
2. Shift same data back 1 week + add new week → two goals (first identical, just different date)
"""

from datetime import date, timedelta
import json
import random
import csv
import os

def generate_week_values(base_steps, variation=200):
    """Generate 7 step values for a week"""
    values = []
    for day in range(7):
        steps = base_steps + random.randint(-variation, variation)
        steps = max(1000, steps)
        values.append(steps)
    return values

def create_week_data(start_monday, step_values):
    """Convert step values to your JSON format for specific week"""
    week_data = []
    for day in range(7):
        current_date = start_monday + timedelta(days=day)
        week_data.append({
            "value": str(step_values[day]),
            "dateTime": current_date.strftime("%Y-%m-%d")
        })
    return week_data

def calculate_average(step_values):
    """Calculate integer average like your algorithm"""
    return sum(step_values) // len(step_values)

def predict_goal(average_steps, scenario="first_week"):
    """Predict goal based on average - simplified for demo"""
    if scenario == "first_week":
        if average_steps < 5000:
            return {"increase": "500", "new_target": average_steps + 500, "average_steps": average_steps}
        elif average_steps < 7500:
            return {"increase": "1000", "new_target": average_steps + 1000, "average_steps": average_steps}
        elif average_steps < 9000:
            return {"increase": "1000", "new_target": average_steps + 1000, "average_steps": average_steps}
        elif average_steps < 10000:
            return {"increase": "increase to 10000", "new_target": 10000, "average_steps": average_steps}
        else:
            return {"increase": "maintain", "new_target": average_steps, "average_steps": average_steps}
    
    # For second week, just a simple example - you'd use your actual algorithm
    return {"increase": "250", "new_target": average_steps + 250, "average_steps": average_steps}

def create_test_pair_silent(name, initial_week_start, week1_base, week2_base=None, variation=200):
    """
    Create a test pair following your exact methodology (without printing):
    1. Single week test
    2. Same data shifted back + new week test
    """
    
    # Generate week 1 step values
    week1_values = generate_week_values(week1_base, variation)
    week1_avg = calculate_average(week1_values)
    
    # TEST 1: Single week
    week1_data = create_week_data(initial_week_start, week1_values)
    goal_date_1 = initial_week_start + timedelta(days=7)
    goal_key_1 = goal_date_1.strftime("%Y-%m-%d")
    
    expected_goal_1 = predict_goal(week1_avg, "first_week")
    expected_result_1 = {goal_key_1: expected_goal_1}
    
    # TEST 2: Same data shifted back + new week
    # Shift week 1 back by 7 days
    shifted_week_start = initial_week_start - timedelta(days=7)
    shifted_week1_data = create_week_data(shifted_week_start, week1_values)  # SAME VALUES!
    
    # Generate week 2 data
    if week2_base:
        week2_values = generate_week_values(week2_base, variation)
    else:
        # Generate week 2 with slight variation from week 1
        week2_values = generate_week_values(week1_base + random.randint(-300, 400), variation)
    
    week2_avg = calculate_average(week2_values)
    week2_data = create_week_data(initial_week_start, week2_values)  # Week 2 uses original start date
    
    # Combine data
    combined_data = shifted_week1_data + week2_data
    
    # Expected results
    shifted_goal_date = shifted_week_start + timedelta(days=7)  # This should be initial_week_start
    goal_key_shifted = shifted_goal_date.strftime("%Y-%m-%d")
    goal_key_2 = goal_date_1.strftime("%Y-%m-%d")  # Second goal same as before
    
    # CRITICAL: First goal should be IDENTICAL to test 1, just different date
    expected_goal_shifted = predict_goal(week1_avg, "first_week")  # SAME as test 1
    expected_goal_2 = predict_goal(week2_avg, "second_week")
    
    expected_result_2 = {
        goal_key_shifted: expected_goal_shifted,
        goal_key_2: expected_goal_2,
    }
    
    return {
        'test1_data': week1_data,
        'test1_expected': expected_result_1,
        'test2_data': combined_data, 
        'test2_expected': expected_result_2
    }

def generate_random_test_datasets(num_datasets=20, seed=42):
    """Generate multiple random test datasets with varied scenarios"""
    
    random.seed(seed)
    
    # Define activity level profiles with realistic ranges
    activity_profiles = [
        {"name": "Sedentary", "base_range": (2000, 4000), "variation": (100, 300)},
        {"name": "Lightly_Active", "base_range": (4000, 6000), "variation": (150, 400)},
        {"name": "Moderately_Active", "base_range": (6000, 8000), "variation": (200, 500)},
        {"name": "Active", "base_range": (8000, 10000), "variation": (300, 600)},
        {"name": "Highly_Active", "base_range": (10000, 15000), "variation": (500, 1000)},
    ]
    
    # Week 2 change patterns
    change_patterns = [
        {"name": "Improving", "multiplier": (1.05, 1.25)},  # 5-25% increase
        {"name": "Declining", "multiplier": (0.75, 0.95)},  # 5-25% decrease  
        {"name": "Stable", "multiplier": (0.95, 1.05)},     # ±5% change
        {"name": "Major_Jump", "multiplier": (1.25, 1.5)},  # 25-50% increase
        {"name": "Big_Drop", "multiplier": (0.5, 0.75)},    # 25-50% decrease
    ]
    
    all_test_results = {}
    yesterday = date.today() - timedelta(days=1)
    data_week_start = yesterday - timedelta(days=6)
    
    for i in range(num_datasets):
        # Randomly select profile and pattern
        profile = random.choice(activity_profiles)
        pattern = random.choice(change_patterns)
        
        # Generate week 1 base steps
        week1_base = random.randint(profile["base_range"][0], profile["base_range"][1])
        variation = random.randint(profile["variation"][0], profile["variation"][1])
        
        # Generate week 2 base steps using pattern
        multiplier = random.uniform(pattern["multiplier"][0], pattern["multiplier"][1])
        week2_base = int(week1_base * multiplier)
        week2_base = max(1500, week2_base)  # Minimum realistic steps
        
        # Create unique test name
        test_name = f"Dataset_{i+1:02d}_{profile['name']}_{pattern['name']}"
        
        # Generate the test pair (silently)
        all_test_results[test_name] = create_test_pair_silent(
            name=test_name,
            initial_week_start=data_week_start,
            week1_base=week1_base,
            week2_base=week2_base,
            variation=variation
        )
    
    return all_test_results

def save_to_csv(all_test_results, filename="step_goals_test_data_20datasets.csv"):
    """Save test results to CSV file"""
    
    # Prepare CSV data
    csv_data = []
    
    for test_name, results in all_test_results.items():
        # Test 1 (Single week)
        test1_data = results['test1_data']
        test1_expected = results['test1_expected']
        
        # Extract goal info from test 1
        goal_date_1 = list(test1_expected.keys())[0]
        goal_info_1 = test1_expected[goal_date_1]
        
        csv_data.append({
            'test_pair': test_name,
            'test_type': 'single_week',
            'data_json': json.dumps(test1_data),
            'expected_goals_json': json.dumps(test1_expected),
            'num_goals': 1,
            'goal_date_1': goal_date_1,
            'goal_1_average_steps': goal_info_1['average_steps'],
            'goal_1_increase': goal_info_1['increase'],
            'goal_1_target': goal_info_1['new_target'],
            'goal_date_2': '',
            'goal_2_average_steps': '',
            'goal_2_increase': '',
            'goal_2_target': '',
            'validation_notes': 'Single week baseline test'
        })
        
        # Test 2 (Two weeks)
        test2_data = results['test2_data']
        test2_expected = results['test2_expected']
        
        # Extract goal info from test 2
        goal_dates = list(test2_expected.keys())
        goal_info_1_t2 = test2_expected[goal_dates[0]]
        goal_info_2_t2 = test2_expected[goal_dates[1]]
        
        # Validation check
        validation_status = "PASS" if goal_info_1 == goal_info_1_t2 else "FAIL"
        validation_notes = f"First goal identical check: {validation_status}"
        
        csv_data.append({
            'test_pair': test_name,
            'test_type': 'two_weeks_shifted',
            'data_json': json.dumps(test2_data),
            'expected_goals_json': json.dumps(test2_expected),
            'num_goals': 2,
            'goal_date_1': goal_dates[0],
            'goal_1_average_steps': goal_info_1_t2['average_steps'],
            'goal_1_increase': goal_info_1_t2['increase'],
            'goal_1_target': goal_info_1_t2['new_target'],
            'goal_date_2': goal_dates[1],
            'goal_2_average_steps': goal_info_2_t2['average_steps'],
            'goal_2_increase': goal_info_2_t2['increase'],
            'goal_2_target': goal_info_2_t2['new_target'],
            'validation_notes': validation_notes
        })
    
    # Write to CSV
    fieldnames = [
        'test_pair', 'test_type', 'data_json', 'expected_goals_json', 'num_goals',
        'goal_date_1', 'goal_1_average_steps', 'goal_1_increase', 'goal_1_target',
        'goal_date_2', 'goal_2_average_steps', 'goal_2_increase', 'goal_2_target',
        'validation_notes'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    return filename

def get_user_input():
    """Get seed and number of datasets from user prompts"""
    
    # Get seed
    while True:
        try:
            seed = int(input("Please enter seed (1 to 99): "))
            if 1 <= seed <= 99:
                break
            else:
                print("Please enter a number between 1 and 99")
        except ValueError:
            print("Please enter a valid number")
    
    # Get number of datasets
    while True:
        try:
            datasets = int(input("Please enter number of datasets required (1 to 99): "))
            if 1 <= datasets <= 99:
                break
            else:
                print("Please enter a number between 1 and 99")
        except ValueError:
            print("Please enter a valid number")
    
    return seed, datasets

def main():
    """Generate test datasets and save to CSV with user prompts"""
    
    print("Step Goals Test Data Generator")
    print("=" * 40)
    
    # Get user input
    seed, num_datasets = get_user_input()
    
    # Generate filename
    output_filename = f"step_goals_test_data_{num_datasets}datasets.csv"
    
    print(f"\nGenerating {num_datasets} datasets with seed {seed}...")
    
    # Generate test datasets with specified parameters
    all_test_results = generate_random_test_datasets(
        num_datasets=num_datasets, 
        seed=seed
    )
    
    # Save to CSV
    filename = save_to_csv(all_test_results, output_filename)
    
    # Confirmation output
    print(f"\n✅ Complete!")
    print(f"Generated {len(all_test_results)} datasets with {len(all_test_results) * 2} total test cases")
    print(f"Random seed: {seed}")
    print(f"Saved to: {filename}")

if __name__ == "__main__":
    main()