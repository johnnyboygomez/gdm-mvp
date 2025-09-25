# core/management/commands/fetch_all_fitbit_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Participant
from device_integration.fitbit import fetch_fitbit_data_for_participant
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch Fitbit data for all active participants with connected devices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--participant_id',
            type=int,
            help='Fetch data for specific participant ID only',
        )

    def handle(self, *args, **options):
        participant_id = options.get('participant_id')
        if participant_id:
            try:
                participant = Participant.objects.get(id=participant_id)
                self.fetch_for_participant(participant)
            except Participant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Participant {participant_id} not found"))
            return

        # Get ALL participants
        all_participants = Participant.objects.select_related('user').all()
        
        # Separate into valid and invalid token groups
        valid_token_participants = []
        invalid_token_participants = []
        
        for participant in all_participants:
            token = participant.fitbit_access_token
            # Check if token is None, empty, or just whitespace
            if not token or not token.strip():
                invalid_token_participants.append(participant)
                # Log error to status_flags
                error_msg = "No Fitbit access token - device not connected"
                participant.status_flags["fetch_fitbit_data_fail"] = True
                participant.status_flags["fetch_fitbit_data_last_error"] = error_msg
                participant.status_flags["fetch_fitbit_data_last_error_time"] = timezone.now().isoformat()
                participant.save(update_fields=["status_flags"])
            else:
                valid_token_participants.append(participant)
        
        # Report on invalid tokens
        if invalid_token_participants:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {len(invalid_token_participants)} participants without valid Fitbit tokens:"))
            for p in invalid_token_participants:
                self.stdout.write(f"   - {p.user.email}: Error logged to status_flags")
        
        # Fetch for valid tokens
        if valid_token_participants:
            self.stdout.write(f"\nStarting Fitbit data fetch for {len(valid_token_participants)} participants with valid tokens...")
            
            success_count = 0
            error_count = 0
            
            for participant in valid_token_participants:
                if self.fetch_for_participant(participant):
                    success_count += 1
                else:
                    error_count += 1
            
            # Summary
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"Fetch completed:")
            self.stdout.write(self.style.SUCCESS(f"  ✓ Successful: {success_count}"))
            if error_count > 0:
                self.stdout.write(self.style.ERROR(f"  ✗ API Errors: {error_count}"))
            if invalid_token_participants:
                self.stdout.write(self.style.WARNING(f"  ⚠  No Token: {len(invalid_token_participants)}"))
            self.stdout.write("="*50)

    def fetch_for_participant(self, participant):
        """Fetch data for a single participant and return success status"""
        try:
            result, status = fetch_fitbit_data_for_participant(participant.id)
            
            if status == 200:
                steps_count = len(result.get('steps', []))
                self.stdout.write(
                    self.style.SUCCESS(f"✓ {participant.user.email}: {steps_count} days fetched")
                )
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                self.stdout.write(
                    self.style.ERROR(f"✗ {participant.user.email}: {error_msg}")
                )
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ {participant.user.email}: {str(e)}")
            )
            logger.exception(f"Error fetching Fitbit data for participant {participant.id}")
            return False