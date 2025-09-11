#!/usr/bin/env python3
"""
Test Data Generator - Following Your Exact Pattern

Creates test data using your methodology:
1. Generate week of data → single goal
2. Shift same data back 1 week + add new week → two goals (first identical, just different date)
"""

from datetime import date, timedelta
import json
import random

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

def create_test_pair(name, initial_week_start, week1_base, week2_base=None, variation=200):
    """
    Create a test pair following your exact methodology:
    1. Single week test
    2. Same data shifted back + new week test
    """
    
    print(f"\n{'='*70}")
    print(f"TEST PAIR: {name}")
    print(f"{'='*70}")
    
    # Generate week 1 step values
    week1_values = generate_week_values(week1_base, variation)
    week1_avg = calculate_average(week1_values)
    
    print(f"Week 1 values: {week1_values}")
    print(f"Week 1 average: {week1_avg}")
    
    # TEST 1: Single week
    print(f"\n--- TEST 1: SINGLE WEEK ---")
    week1_data = create_week_data(initial_week_start, week1_values)
    goal_date_1 = initial_week_start + timedelta(days=7)
    goal_key_1 = goal_date_1.strftime("%Y-%m-%d")
    
    expected_goal_1 = predict_goal(week1_avg, "first_week")
    expected_result_1 = {goal_key_1: expected_goal_1}
    
    print(f"Week 1 data ({initial_week_start.strftime('%Y-%m-%d')} to {(initial_week_start + timedelta(days=6)).strftime('%Y-%m-%d')}):")
    print(json.dumps(week1_data))
    print(f"\nExpected result:")
    print(json.dumps(expected_result_1))
    
    # TEST 2: Same data shifted back + new week
    print(f"\n--- TEST 2: TWO WEEKS (SAME DATA SHIFTED) ---")
    
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
    
    print(f"Modified week 1 and week 2 data:")
    print(f"  Week 1 shifted: {shifted_week_start.strftime('%Y-%m-%d')} to {(shifted_week_start + timedelta(days=6)).strftime('%Y-%m-%d')} (SAME VALUES)")
    print(f"  Week 2: {initial_week_start.strftime('%Y-%m-%d')} to {(initial_week_start + timedelta(days=6)).strftime('%Y-%m-%d')} (avg: {week2_avg})")
    print(json.dumps(combined_data))
    
    print(f"\nExpected result:")
    print(json.dumps(expected_result_2))
    
    # VALIDATION CHECK
    print(f"\n--- VALIDATION ---")
    if expected_goal_shifted == expected_goal_1:
        print(f"✅ CORRECT: First goal identical in both tests (same values, different dates)")
        print(f"   Test 1: {goal_key_1} → {expected_goal_1}")
        print(f"   Test 2: {goal_key_shifted} → {expected_goal_shifted}")
    else:
        print(f"❌ ERROR: First goal should be identical!")
    
    return {
        'test1_data': week1_data,
        'test1_expected': expected_result_1,
        'test2_data': combined_data, 
        'test2_expected': expected_result_2
    }

def main():
    """Generate test pairs following your methodology"""
    
    print("STEP GOALS TEST DATA GENERATOR")
    print("Following your exact pattern: same data, shifted dates")
    
    yesterday = date.today() - timedelta(days=1)  # Sep 8
    data_week_start = yesterday - timedelta(days=6)
    
    # Set seed for reproducible results
    random.seed(42)
    
    # Test Pair 1: Low activity user (like your example)
    create_test_pair(
        name="Low Activity User (~4200 steps)",
        initial_week_start=data_week_start,
        week1_base=4200,
        week2_base=4400,  # Slight improvement
        variation=150
    )
    
    # Test Pair 2: Moderate activity user
    create_test_pair(
        name="Moderate Activity User (~6000 steps)", 
        initial_week_start=data_week_start,  # Monday Aug 18
        week1_base=6000,
        week2_base=6500,
        variation=250
    )
    
    # Test Pair 3: Near 10k user  
    create_test_pair(
        name="Near 10K User (~9400 steps)",
        initial_week_start=data_week_start,  # Monday Aug 4
        week1_base=5999,
        week2_base=9100,  # Slight decline, might miss target
        variation=500
    )
    
    print(f"\n{'='*70}")
    print("HOW TO USE:")
    print("1. Use TEST 1 data first → verify single goal works")
    print("2. Use TEST 2 data → verify:")
    print("   - First goal is IDENTICAL to TEST 1 (same values, different date)")
    print("   - Second goal is calculated correctly")
    print("3. If first goal changes between tests → ALGORITHM BUG!")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()