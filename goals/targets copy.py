# goals/targets.py
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

def validate_step_data(average_steps):
    """Validate that step data is reasonable"""
    if not isinstance(average_steps, (int, float)):
        logger.warning(f"Invalid step data type: {type(average_steps)}")
        return False
    
    if average_steps < 1000:
        logger.warning(f"Step count too low (< 1000): {average_steps}")
        return False
        
    if average_steps > 50000:  # Unreasonably high
        logger.warning(f"Unusually high step count: {average_steps}")
        return False
        
    return True

def calculate_step_increase(current_avg, last_goal_data=None, target_was_met=True):
    """
    Calculate the appropriate step increase based on current average and performance.
    
    Args:
        current_avg: Current week's average steps
        last_goal_data: Previous goal dictionary or None
        target_was_met: Whether previous target was achieved
    
    Returns:
        tuple: (increase_description, new_target_value)
    """
    
    # Validate input
    if not validate_step_data(current_avg):
        current_avg = max(1000, min(current_avg, 50000))  # Clamp to reasonable range
    
    current_avg = int(current_avg)  # Ensure integer
    
    # First week logic (no previous goal)
    if not last_goal_data:
        return _calculate_first_week_target(current_avg)
    
    # Subsequent weeks - consider performance
    if target_was_met:
        return _calculate_target_met(current_avg)
    else:
        return _calculate_target_missed(current_avg)

def _calculate_first_week_target(current_avg):
    """Calculate target for first week"""
    if current_avg < 5000:
        return "500", current_avg + 500
    elif current_avg < 7500:
        return "1000", current_avg + 1000
    elif current_avg < 9000:
        return "1000", current_avg + 1000
    elif current_avg < 10000:
        return "increase to 10000", 10000
    else:
        return "maintain", current_avg

def _calculate_target_met(current_avg):
    """Calculate target when previous goal was met"""
    if current_avg >= 10000:
        return "maintain", current_avg
    elif current_avg < 5000:
        return "500", current_avg + 500
    elif current_avg < 7500:
        return "1000", current_avg + 1000
    elif current_avg < 9000:
        return "1000", current_avg + 1000
    else:  # 9000–9999
        return "500", current_avg + 500

def _calculate_target_missed(current_avg):
    """Calculate target when previous goal was missed (more conservative)"""
    if current_avg >= 10000:
        return "maintain", current_avg
    elif current_avg < 5000:
        return "250", current_avg + 250
    elif current_avg < 7500:
        return "500", current_avg + 500
    elif current_avg < 9000:
        return "500", current_avg + 500
    else:  # 9000–9999
        return "increase to 10000", 10000

def compute_weekly_target(participant, average_steps, week_start, week_end, last_goal_data=None):
    """
    Calculate this week's step target for a participant.

    Args:
        participant: Participant instance
        average_steps: int, last week's average steps
        week_start: Start date of the week (based on participant start date)
        week_end: End date of the week
        last_goal_data: Previous goal dictionary or None
    
    Returns:
        dict: Goal data with increase, average_steps, new_target
    """
    
    logger.info(f"Computing weekly target for participant {participant.id}, "
               f"average_steps: {average_steps}, week: {week_start} to {week_end}, "
               f"has_last_goal: {last_goal_data is not None}")
    
    # Determine if previous target was met
    target_was_met = True
    if last_goal_data:
        target_was_met = average_steps >= last_goal_data.get("new_target", 0)
    
    # Calculate new target
    increase_description, new_target = calculate_step_increase(
        current_avg=average_steps,
        last_goal_data=last_goal_data,
        target_was_met=target_was_met
    )
    
    # Return goal data as dictionary
    goal_data = {
        "increase": increase_description,
        "average_steps": average_steps,
        "new_target": new_target,
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "target_was_met": target_was_met if last_goal_data else None
    }
    
    logger.info(f"Computed goal: {goal_data}")
    return goal_data

def get_step_data_for_week(daily_steps, week_start, week_end):
    """
    Extract and validate step data for a specific week.
    
    Args:
        daily_steps: List of step data from participant
        week_start: Start date of week
        week_end: End date of week
    
    Returns:
        list: Valid step values for the week
    """
    week_steps = []
    
def get_step_data_for_week(daily_steps, week_start, week_end):
    week_steps = []
    
    for step_entry in daily_steps:
        try:
            # Handle both "date" and "dateTime" field names
            date_str = step_entry.get("date") or step_entry.get("dateTime")
            step_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            step_value = int(step_entry["value"])
            
            if week_start <= step_date <= week_end and validate_step_data(step_value):
                week_steps.append(step_value)
                
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Invalid step entry: {step_entry}, error: {e}")
            continue
    
    return week_steps

def run_weekly_algorithm(participant):
    """
    Compute and save a weekly step goal for a participant.

    Rules:
    - Analyzes the most recently completed week of data
    - Sets goals for the current/upcoming week
    - Allows re-running on same day (for updated data scenarios)
    
    Returns:
        dict: Goal data or None
    """
    
    logger.info(f"Running weekly algorithm for participant {participant.id}")
    
    today = date.today()
    targets = participant.targets or {}
    daily_steps = participant.daily_steps or []
    
    # Calculate which week we're in since participant start
    days_since_start = (today - participant.start_date).days
    weeks_since_start = days_since_start // 7
    
    # Still in first week - no complete week to analyze yet
    if weeks_since_start == 0:
        logger.info(f"Still in first week (day {days_since_start}), no complete week to analyze")
        return None
    
    # Calculate the most recently completed week to analyze
    completed_week_number = weeks_since_start - 1
    analysis_week_start = participant.start_date + timedelta(days=completed_week_number * 7)
    analysis_week_end = analysis_week_start + timedelta(days=6)
    
    # Calculate the current week (where we set the goal)
    target_week_start = participant.start_date + timedelta(days=weeks_since_start * 7)
    target_week_end = target_week_start + timedelta(days=6)
    
    logger.info(f"Analyzing week {analysis_week_start} to {analysis_week_end}")
    logger.info(f"Setting goal for week {target_week_start} to {target_week_end}")
    
    # Get last goal data for comparison
    last_goal_data = None
    target_week_key = target_week_start.strftime("%Y-%m-%d")

    if targets:
        goal_dates = sorted(targets.keys())
        if goal_dates:
            # If we're updating the current week, don't use it for comparison
            if goal_dates[-1] == target_week_key and len(goal_dates) > 1:
                # Use the previous week's goal
                last_goal_data = targets[goal_dates[-2]]
            elif goal_dates[-1] != target_week_key:
                # Use the most recent goal (different week)
                last_goal_data = targets[goal_dates[-1]]
            # If only one goal exists and it's this week, use first-week logic (last_goal_data remains None)
    
    # Get step data for the completed week
    week_steps = get_step_data_for_week(daily_steps, analysis_week_start, analysis_week_end)
    logger.info(f"Found {len(week_steps)} days of step data for analysis week")

    if len(week_steps) >= 4:
        week_avg = sum(week_steps) // len(week_steps)
        logger.info(f"Calculated average: {week_avg} steps from {len(week_steps)} days")
        
        goal_data = compute_weekly_target(
            participant=participant, 
            average_steps=week_avg,
            week_start=target_week_start,
            week_end=target_week_end,
            last_goal_data=last_goal_data
        )
    else:
        if last_goal_data:
            goal_data = {
                "increase": "insufficient data - target maintained",
                "average_steps": "insufficient data",
                "new_target": last_goal_data["new_target"],
                "week_start": target_week_start.strftime("%Y-%m-%d"),
                "week_end": target_week_end.strftime("%Y-%m-%d"),
                "target_was_met": None
            }
        else:
            logger.error(f"First week with insufficient data for participant {participant.id}")
            return None

    # Save to participant.targets JSON
    target_week_key = target_week_start.strftime("%Y-%m-%d")
    targets[target_week_key] = {
        "increase": goal_data["increase"],
        "average_steps": goal_data["average_steps"],
        "new_target": goal_data["new_target"]
    }
    participant.targets = targets
    participant.save(update_fields=["targets"])
    
    logger.info(f"Successfully created and saved weekly goal: {goal_data}")
    return goal_data