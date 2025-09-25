# core/management/commands/calculate_weekly_targets.py
from django.core.management.base import BaseCommand
from datetime import date
from core.models import Participant
from goals.targets import run_weekly_algorithm, is_target_day
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Calculate weekly step targets for participants on their target day'

    def add_arguments(self, parser):
        parser.add_argument(
            '--participant_id',
            type=int,
            help='Calculate target for specific participant ID only',
        )

    def handle(self, *args, **options):
        today = date.today()
        self.stdout.write(f"Calculating weekly targets for {today.strftime('%Y-%m-%d')}...\n")
        
        # If specific participant requested
        participant_id = options.get('participant_id')
        if participant_id:
            try:
                participant = Participant.objects.get(id=participant_id)
                self.calculate_for_participant(participant)
            except Participant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Participant {participant_id} not found"))
            return

        # Get all participants
        all_participants = Participant.objects.select_related('user').all()
        
        # Filter to those on target day AND active
        target_day_participants = [
            p for p in all_participants 
            if is_target_day(p.start_date) and p.user.is_active
        ]
        
        if not target_day_participants:
            self.stdout.write(self.style.WARNING("No active participants on target day today"))
            return
        
        self.stdout.write(f"Found {len(target_day_participants)} active participants on target day:\n")
        
        success_count = 0
        no_target_count = 0
        no_data_today_count = 0
        error_count = 0
        
        for participant in target_day_participants:
            result = self.calculate_for_participant(participant)
            
            if result == 'success':
                success_count += 1
            elif result == 'no_target':
                no_target_count += 1
            elif result == 'no_data_today':
                no_data_today_count += 1
            else:
                error_count += 1
        
        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write("Calculation Summary:")
        self.stdout.write(self.style.SUCCESS(f"  ✓ Targets Calculated: {success_count}"))
        if no_data_today_count > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠  No Target Day Data Yet: {no_data_today_count}"))
        if no_target_count > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠  No Target (insufficient data): {no_target_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  ✗ Errors: {error_count}"))
        self.stdout.write("="*60)

    def calculate_for_participant(self, participant):
        """Calculate target for a single participant"""
        try:
        	today = date.today()
        	today_str = today.strftime('%Y-%m-%d')
        
        	# Check if target already exists for today
        	targets = participant.targets or {}
        	if today_str in targets and targets[today_str].get('new_target'):
            	self.stdout.write(
                	f"  {participant.user.email}: Target already exists for today - skipping"
            	)
            	return 'already_exists'
            
            # CRITICAL: Check for target day data before calculating
            # This ensures all 7 days of data are reliably synced
            today = date.today()
            today_str = today.strftime('%Y-%m-%d')
            
            daily_steps = participant.daily_steps or []
            has_today_data = any(
                entry.get('date') == today_str and entry.get('value', 0) > 0
                for entry in daily_steps
            )
            
            if not has_today_data:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠  {participant.user.email}: No step data from today yet - skipping calculation"
                    )
                )
                return 'no_data_today'
            
            # Now safe to calculate - we know all 7 days are synced
            goal_data = run_weekly_algorithm(participant)
            
            if goal_data:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {participant.user.email}: Target calculated - {goal_data['new_target']} steps/day"
                    )
                )
                return 'success'
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠  {participant.user.email}: No target calculated (insufficient data or first week)"
                    )
                )
                return 'no_target'
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ {participant.user.email}: {str(e)}")
            )
            logger.exception(f"Error calculating target for participant {participant.id}")
            return 'error'