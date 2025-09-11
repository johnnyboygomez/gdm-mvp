# test_targets.py
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch
import logging

# Import your module (adjust path as needed)
from goals.targets import (
    validate_step_data, 
    calculate_step_increase,
    compute_weekly_target,
    get_step_data_for_week,
    run_weekly_algorithm,
    _parse_increase_value,
    _calculate_first_week_target,
    _calculate_target_met_matrix,
    _calculate_target_missed_matrix
)

class TestValidateStepData:
    """Test step data validation"""
    
    def test_valid_step_counts(self):
        assert validate_step_data(5000) == True
        assert validate_step_data(12000.5) == True
        assert validate_step_data(1000) == True
        assert validate_step_data(49999) == True
    
    def test_invalid_step_counts(self):
        assert validate_step_data(500) == False  # Too low
        assert validate_step_data(60000) == False  # Too high
        assert validate_step_data("5000") == False  # Wrong type
        assert validate_step_data(None) == False
        assert validate_step_data([5000]) == False

class TestParseIncreaseValue:
    """Test parsing of increase values"""
    
    def test_special_cases(self):
        assert _parse_increase_value("maintain") == 0
        assert _parse_increase_value("increase to 10000") == "increase to 10000"
    
    def test_numeric_strings(self):
        assert _parse_increase_value("500") == 500
        assert _parse_increase_value("1000") == 1000
    
    def test_invalid_values(self):
        assert _parse_increase_value("invalid") == 0
        assert _parse_increase_value(None) == 0

class TestFirstWeekTargets:
    """Test first week target calculation"""
    
    def test_low_activity_users(self):
        increase, target = _calculate_first_week_target(3000)
        assert increase == "500"
        assert target == 3500
    
    def test_moderate_activity_users(self):
        increase, target = _calculate_first_week_target(6000)
        assert increase == "1000"
        assert target == 7000
        
        increase, target = _calculate_first_week_target(8500)
        assert increase == "1000"
        assert target == 9500
    
    def test_near_10k_users(self):
        increase, target = _calculate_first_week_target(9500)
        assert increase == "increase to 10000"
        assert target == 10000
    
    def test_high_activity_users(self):
        increase, target = _calculate_first_week_target(12000)
        assert increase == "maintain"
        assert target == 12000

class TestTargetMetMatrix:
    """Test target met scenarios"""
    
    def test_low_current_avg_scenarios(self):
        # Current avg < 5000
        increase, target = _calculate_target_met_matrix(4000, 250)
        assert increase == "500" and target == 4500
        
        increase, target = _calculate_target_met_matrix(4000, 500)
        assert increase == "500" and target == 4500
    
    def test_moderate_current_avg_scenarios(self):
        # 5000 <= current avg < 7500
        increase, target = _calculate_target_met_matrix(6000, 500)
        assert increase == "1000" and target == 7000
        
        increase, target = _calculate_target_met_matrix(6000, 1000)
        assert increase == "1000" and target == 7000
    
    def test_high_current_avg_scenarios(self):
        # current avg >= 10000
        increase, target = _calculate_target_met_matrix(12000, 500)
        assert increase == "maintain" and target == 12000

class TestTargetMissedMatrix:
    """Test target missed scenarios"""
    
    def test_maintain_previous_increase(self):
        # Special case: maintain becomes 1000
        increase, target = _calculate_target_missed_matrix(5000, 0)  # maintain = 0
        assert increase == "1000" and target == 6000
    
    def test_low_current_avg_missed(self):
        # Current avg < 5000, missed target
        increase, target = _calculate_target_missed_matrix(4000, 500)
        assert increase == "250" and target == 4250
        
        increase, target = _calculate_target_missed_matrix(4000, 1000)
        assert increase == "500" and target == 4500
    
    def test_special_increase_to_10k_missed(self):
        increase, target = _calculate_target_missed_matrix(8000, "increase to 10000")
        assert increase == "1000" and target == 9000

class TestComputeWeeklyTarget:
    """Test the main target computation function"""
    
    def setup_method(self):
        self.mock_participant = Mock()
        self.mock_participant.id = 123
        self.week_start = date(2024, 1, 8)  # Monday
        self.week_end = date(2024, 1, 14)   # Sunday
    
    def test_first_week_computation(self):
        result = compute_weekly_target(
            participant=self.mock_participant,
            average_steps=6000,
            week_start=self.week_start,
            week_end=self.week_end,
            last_goal_data=None
        )
        
        assert result["increase"] == "1000"
        assert result["average_steps"] == 6000
        assert result["new_target"] == 7000
        assert result["target_was_met"] is None
    
    def test_subsequent_week_target_met(self):
        last_goal = {"increase": "500", "new_target": 6500}
        
        result = compute_weekly_target(
            participant=self.mock_participant,
            average_steps=7000,  # Met the target of 6500
            week_start=self.week_start,
            week_end=self.week_end,
            last_goal_data=last_goal
        )
        
        assert result["target_was_met"] == True
        assert result["average_steps"] == 7000
    
    def test_subsequent_week_target_missed(self):
        last_goal = {"increase": "500", "new_target": 7000}
        
        result = compute_weekly_target(
            participant=self.mock_participant,
            average_steps=6500,  # Missed the target of 7000
            week_start=self.week_start,
            week_end=self.week_end,
            last_goal_data=last_goal
        )
        
        assert result["target_was_met"] == False
        assert result["average_steps"] == 6500

class TestGetStepDataForWeek:
    """Test step data extraction for specific weeks"""
    
    def setup_method(self):
        self.week_start = date(2024, 1, 8)
        self.week_end = date(2024, 1, 14)
        
        # Sample daily steps data
        self.daily_steps = [
            {"date": "2024-01-08", "value": 5000},
            {"date": "2024-01-09", "value": 6000},
            {"date": "2024-01-10", "value": 7000},
            {"date": "2024-01-11", "value": 5500},
            {"date": "2024-01-12", "value": 8000},
            {"date": "2024-01-13", "value": 6500},
            {"date": "2024-01-14", "value": 7200},
            {"date": "2024-01-15", "value": 5800},  # Outside week
            {"date": "2024-01-07", "value": 4800},  # Outside week
        ]
    
    def test_extract_valid_week_data(self):
        result = get_step_data_for_week(self.daily_steps, self.week_start, self.week_end)
        expected = [5000, 6000, 7000, 5500, 8000, 6500, 7200]
        assert result == expected
    
    def test_handle_invalid_data(self):
        invalid_data = [
            {"date": "2024-01-08", "value": 5000},
            {"date": "invalid-date", "value": 6000},  # Invalid date
            {"date": "2024-01-09", "value": "invalid"},  # Invalid value
            {"date": "2024-01-10", "value": 500},  # Too low (invalid)
            {"date": "2024-01-11", "value": 60000},  # Too high (invalid)
            {"date": "2024-01-12", "value": 7000},
        ]
        
        result = get_step_data_for_week(invalid_data, self.week_start, self.week_end)
        expected = [5000, 7000]  # Only valid entries
        assert result == expected
    
    def test_dateTime_field_support(self):
        data_with_datetime = [
            {"dateTime": "2024-01-08", "value": 5000},
            {"dateTime": "2024-01-09", "value": 6000},
        ]
        
        result = get_step_data_for_week(data_with_datetime, self.week_start, self.week_end)
        assert result == [5000, 6000]

class TestRunWeeklyAlgorithm:
    """Test the main algorithm runner"""
    
    def setup_method(self):
        self.mock_participant = Mock()
        self.mock_participant.id = 123
        self.mock_participant.start_date = date(2024, 1, 1)  # Monday
        self.mock_participant.targets = {}
        
        # Generate sample daily steps for 3 weeks
        self.mock_participant.daily_steps = []
        base_date = date(2024, 1, 1)
        
        # Week 1 data (average ~5000)
        for i in range(7):
            self.mock_participant.daily_steps.append({
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "value": 5000 + (i * 100)  # 5000, 5100, 5200, etc.
            })
        
        # Week 2 data (average ~6000)  
        for i in range(7, 14):
            self.mock_participant.daily_steps.append({
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "value": 6000 + (i * 50)
            })
        
        # Week 3 data (average ~7000)
        for i in range(14, 21):
            self.mock_participant.daily_steps.append({
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "value": 7000 + (i * 25)
            })
    
    @patch('goals.targets.date')
    def test_first_week_no_goal(self, mock_date):
        # Still in first week
        mock_date.today.return_value = date(2024, 1, 5)
        
        result = run_weekly_algorithm(self.mock_participant)
        assert result is None
    
    @patch('goals.targets.date')  
    def test_second_week_first_goal(self, mock_date):
        # Now in second week, analyze first week
        mock_date.today.return_value = date(2024, 1, 10)
        
        result = run_weekly_algorithm(self.mock_participant)
        
        assert result is not None
        assert result["increase"] == "1000"  # First week with ~5300 avg
        assert result["new_target"] == 6300
        
        # Check that goal was saved
        self.mock_participant.save.assert_called_with(update_fields=["targets"])
        assert "2024-01-08" in self.mock_participant.targets
    
    @patch('goals.targets.date')
    def test_third_week_subsequent_goal(self, mock_date):
        # Set up previous goal
        self.mock_participant.targets = {
            "2024-01-08": {"increase": "1000", "new_target": 6300, "average_steps": 5300}
        }
        
        # Now in third week
        mock_date.today.return_value = date(2024, 1, 17)
        
        result = run_weekly_algorithm(self.mock_participant)
        
        assert result is not None
        # Should analyze week 2 data and compare against week 1 goal
        assert result["target_was_met"] == True  # Week 2 avg > 6300
    
    @patch('goals.targets.date')
    def test_insufficient_data_scenario(self, mock_date):
        # Remove most step data to simulate insufficient data
        self.mock_participant.daily_steps = [
            {"date": "2024-01-08", "value": 5000},
            {"date": "2024-01-09", "value": 6000},
            {"date": "2024-01-10", "value": 7000},
            # Only 3 days - insufficient
        ]
        
        # Set up previous goal for fallback
        self.mock_participant.targets = {
            "2024-01-08": {"increase": "1000", "new_target": 6300, "average_steps": 5300}
        }
        
        mock_date.today.return_value = date(2024, 1, 17)
        
        result = run_weekly_algorithm(self.mock_participant)
        
        assert result["increase"] == "insufficient data - target maintained"
        assert result["new_target"] == 6300  # Maintained previous target


# Sample data for manual testing
def create_sample_participant():
    """Create a sample participant object for testing"""
    participant = Mock()
    participant.id = 999
    participant.start_date = date(2024, 1, 1)
    participant.targets = {}
    
    # Generate realistic daily steps for several weeks
    daily_steps = []
    base_date = date(2024, 1, 1)
    
    # 4 weeks of data with increasing trend
    for week in range(4):
        base_steps = 4000 + (week * 1000)  # Start at 4k, increase by 1k each week
        
        for day in range(7):
            day_date = base_date + timedelta(days=week*7 + day)
            # Add some daily variation
            daily_variation = (-500, 200, 800, -200, 400, 600, 300)[day]
            steps = base_steps + daily_variation
            
            daily_steps.append({
                "date": day_date.strftime("%Y-%m-%d"),
                "value": max(1000, steps)  # Ensure minimum 1000 steps
            })
    
    participant.daily_steps = daily_steps
    return participant


# Usage examples and manual testing
if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v"])
    
    # Manual testing examples
    print("\n" + "="*50)
    print("MANUAL TESTING EXAMPLES")
    print("="*50)
    
    # Test first week scenarios
    print("\n1. First week scenarios:")
    test_cases = [3000, 6000, 8500, 9500, 12000]
    for steps in test_cases:
        increase, target = _calculate_first_week_target(steps)
        print(f"  {steps} steps → {increase} (target: {target})")
    
    # Test with sample participant
    print("\n2. Sample participant simulation:")
    sample_participant = create_sample_participant()
    
    # Simulate running algorithm at different dates
    with patch('goals.targets.date') as mock_date:
        for week in [2, 3, 4]:  # Weeks 2-4
            test_date = date(2024, 1, 1) + timedelta(days=week*7 + 3)  # Mid-week
            mock_date.today.return_value = test_date
            
            result = run_weekly_algorithm(sample_participant)
            if result:
                print(f"  Week {week}: {result['increase']} → {result['new_target']} steps")
            else:
                print(f"  Week {week}: No goal generated")
    
    print(f"\nFinal targets: {sample_participant.targets}")