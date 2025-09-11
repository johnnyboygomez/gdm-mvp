#!/usr/bin/env python3
"""
Test Data Generator for Step Goals Algorithm

Creates copy-paste ready JSON data for database testing, following your pattern:
1. Generate week(s) of daily steps data
2. Calculate expected results
3. Output in your exact format for easy database insertion
"""

from datetime import date, timedelta
import json
import random

def generate_daily_steps(start_date, num_weeks, base_steps, variation=500):
    """
    Generate realistic daily step data
    
    Args:
        start_date: Starting Monday date
        num_weeks: Number of weeks to generate
        base_steps: Average steps per day
        variation: Random variation (+/- this amount)
    
    Returns:
        List of daily step entries in your format
    """
    daily_steps = []
    
    for week in range(num_weeks):
        for day in range(7):  # Monday to Sunday
            current_date = start_date + timedelta(days=week*7 + day)
            
            # Add some realistic daily variation
            steps = base_steps + random.randint(-variation, variation)
            steps = max(1000, steps)  # Minimum 1000 steps
            
            daily_steps.append({
                "value": str(steps),
                "dateTime": current_date.strftime("%Y-%m-%d")
            })
    
    return daily_steps

def calculate_expected_targets(daily_steps, participant_start_date):
    """
    Calculate what the algorithm should produce
    
    Args:
        daily_steps: List of step data
        participant_start_date: When participant started (Monday)
    
    Returns:
        Dict of expected targets in your format
    """
    from goals.targets import (
        _calculate_first_week_target,
        _calculate_target_met_matrix,
        _calculate_target_missed_matrix,
        _parse_increase_value
    )
    
    # Group steps by week
    weeks = {}
    for step_entry in daily_steps:
        step_date = date.fromisoformat(step_entry["dateTime"])
        days_since_start = (step_date - participant_start_date).days
        week_num = days_since_start // 7
        
        if week_num not in weeks:
            weeks[week_num] = []
        weeks[week_num].append(int(step_entry["value"]))
    
    expected_targets = {}
    last_goal_data = None
    
    # Process each completed week (skip current incomplete week)
    for week_num in sorted(weeks.keys())[:-1]:  # Skip last week (current)
        if len(weeks[week_num]) >= 4:  # Need at least 4 days
            week_avg = sum(weeks[week_num]) // len(weeks[week_num])
            
            # Calculate target week start (next week)
            target_week_start = participant_start_date + timedelta(days=(week_num + 1) * 7)
            target_week_key = target_week_start.strftime("%Y-%m-%d")
            
            # Determine target was met
            target_was_met = True
            if last_goal_data:
                target_was_met = week_avg >= last_goal_data.get("new_target", 0)
            
            # Calculate increase
            if not last_goal_data:
                # First week
                increase, new_target = _calculate_first_week_target(week_avg)
            elif target_was_met:
                # Target met
                prev_increase = _parse_increase_value(last_goal_data["increase"])
                increase, new_target = _calculate_target_met_matrix(week_avg, prev_increase)
            else:
                # Target missed
                prev_increase = _parse_increase_value(last_goal_data["increase"])
                increase, new_target = _calculate_target_missed_matrix(week_avg, prev_increase)
            
            # Store result
            expected_targets[target_week_key] = {
                "increase": increase,
                "new_target": new_target,
                "average_steps": week_avg
            }
            
            last_goal_data = expected_targets[target_week_key]
    
    return expected_targets

def create_test_scenario(name, start_date, weeks_data, description=""):
    """
    Create a complete test scenario
    
    Args:
        name: Test scenario name
        start_date: Participant start date (Monday)
        weeks_data: List of (base_steps, variation) tuples
        description: What this scenario tests
    """
    print(f"\n{'='*60}")
    print(f"TEST SCENARIO: {name}")
    print(f"Description: {description}")
    print(f"Participant starts: {start_date.strftime('%Y-%m-%d')} (Monday)")
    print(f"{'='*60}")
    
    # Generate daily steps
    daily_steps = []
    for week_idx, (base_steps, variation) in enumerate(weeks_data):
        week_start = start_date + timedelta(days=week_idx * 7)
        week_steps = generate_daily_steps(week_start, 1, base_steps, variation)
        daily_steps.extend(week_steps)
        
        # Show week summary
        week_values = [int(step["value"]) for step in week_steps]
        week_avg = sum(week_values) // len(week_values)
        print(f"Week {week_idx + 1}: {week_start.strftime('%m-%d')} to {(week_start + timedelta(days=6)).strftime('%m-%d')}, avg: {week_avg}")
    
    # Calculate expected targets
    expected_targets = calculate_expected_targets(daily_steps, start_date)
    
    # Output in your format
    print(f"\nDAILY STEPS DATA (copy to database):")
    print(json.dumps(daily_steps, separators=(',', ': ')))
    
    print(f"\nEXPECTED TARGETS (for verification):")
    print(json.dumps(expected_targets, separators=(',', ': ')))
    
    return daily_steps, expected_targets

def main():
    """Generate various test scenarios"""
    
    print("STEP GOALS ALGORITHM - TEST DATA GENERATOR")
    print("Copy-paste ready data for database testing")
    
    # Scenario 1: Single week (first goal)
    create_test_scenario(
        name="First Goal - Low Activity User",
        start_date=date(2025, 9, 1),  # Sept 1 (Monday)
        weeks_data=[(4200, 200)],  # One week, ~4200 steps +/- 200
        description="Tests first week logic for user averaging ~4200 steps"
    )
    
    # Scenario 2: Target missed scenario (your exact case)
    create_test_scenario(
        name="Target Missed - Sedentary User",
        start_date=date(2025, 8, 25),  # Aug 25 (Monday) 
        weeks_data=[(4200, 150), (4400, 150)],  # Two weeks, slight improvement
        description="User misses target, should get smaller increase"
    )
    
    # Scenario 3: Target met scenario
    create_test_scenario(
        name="Target Met - Improving User",
        start_date=date(2025, 8, 18),
        weeks_data=[(4200, 150), (5000, 200)],  # Significant improvement
        description="User meets target, should get normal increase"
    )
    
    # Scenario 4: Near 10k user (special logic)
    create_test_scenario(
        name="Near 10K User",
        start_date=date(2025, 8, 11),
        weeks_data=[(9400, 200)],  # Close to 10k
        description="Tests 'increase to 10000' logic"
    )
    
    # Scenario 5: High activity user
    create_test_scenario(
        name="High Activity User", 
        start_date=date(2025, 8, 4),
        weeks_data=[(12000, 500)],  # Already high
        description="Tests maintain logic for high activity users"
    )
    
    # Scenario 6: Multi-week progression
    create_test_scenario(
        name="Multi-Week Progression",
        start_date=date(2025, 7, 28),
        weeks_data=[
            (3500, 200),  # Week 1: Low
            (4000, 200),  # Week 2: Improvement  
            (4300, 200),  # Week 3: Continued improvement
            (3900, 300),  # Week 4: Setback (missed target)
        ],
        description="Tests realistic multi-week user journey with setback"
    )

def create_custom_scenario():
    """Interactive mode to create custom scenarios"""
    print(f"\n{'='*60}")
    print("CUSTOM SCENARIO BUILDER")
    print(f"{'='*60}")
    
    name = input("Scenario name: ")
    start_date_str = input("Start date (YYYY-MM-DD, must be Monday): ")
    start_date = date.fromisoformat(start_date_str)
    
    weeks_data = []
    week_num = 1
    
    while True:
        print(f"\nWeek {week_num}:")
        base_steps = input(f"  Average steps (or 'done' to finish): ")
        
        if base_steps.lower() == 'done':
            break
            
        base_steps = int(base_steps)
        variation = int(input(f"  Daily variation (+/-): ") or "200")
        weeks_data.append((base_steps, variation))
        week_num += 1
    
    description = input("Description: ")
    
    create_test_scenario(name, start_date, weeks_data, description)

if __name__ == "__main__":
    # Set random seed for reproducible results
    random.seed(42)
    
    # Generate standard scenarios
    main()
    
    # Offer custom scenario creation
    print(f"\n{'='*60}")
    custom = input("Create custom scenario? (y/n): ")
    if custom.lower() == 'y':
        create_custom_scenario()
    
    print(f"\n{'='*60}")
    print("USAGE INSTRUCTIONS:")
    print("1. Copy the DAILY STEPS DATA → paste into participant.daily_steps")
    print("2. Run your algorithm")  
    print("3. Compare result with EXPECTED TARGETS")
    print("4. Should match exactly!")
    print(f"{'='*60}")