# core/management/commands/calculate_weekly_targets.py
from django.core.management.base import BaseCommand
from datetime import date
from core.models import Participant
from goals.targets import run_weekly_algorithm, is_target_day
from goals.notifications import send_goal_notification
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Calculate weekly step targets and send notifications for participants on their target day'

    def add_arguments(self, parser):
        parser.add_argument(
            '--participant_id',
            type=int,
            help='Calculate target for specific participant ID only',
        )
        parser.add_argument(
            '--skip-notifications',
            action='store_true',
            help='Calculate targets but skip sending notifications',
        )

    def handle(self, *args, **options):
        today = date.today()
        skip_notifications = options.get('skip_notifications', False)

        self.stdout.write(f"Calculating weekly targets for {today.strftime('%Y-%m-%d')}...\n")

        # If specific participant requested
        participant_id = options.get('participant_id')
        if participant_id:
            try:
                participant = Participant.objects.get(id=participant_id)
                self.calculate_for_participant(participant, skip_notifications)
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
        notification_sent_count = 0
        notification_failed_count = 0
        no_target_count = 0
        no_data_today_count = 0
        already_exists_count = 0
        error_count = 0

        for participant in target_day_participants:
            result = self.calculate_for_participant(participant, skip_notifications)

            if result['status'] == 'success':
                success_count += 1
                if result.get('notification_sent'):
                    notification_sent_count += 1
                elif result.get('notification_attempted'):
                    notification_failed_count += 1
            elif result['status'] == 'no_target':
                no_target_count += 1
            elif result['status'] == 'no_data_today':
                no_data_today_count += 1
            elif result['status'] == 'already_exists':
                already_exists_count += 1
            else:
                error_count += 1

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write("Calculation Summary:")
        self.stdout.write(self.style.SUCCESS(f"  ✓ Targets Calculated: {success_count}"))
        if notification_sent_count > 0:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Notifications Sent: {notification_sent_count}"))
        if notification_failed_count > 0:
            self.stdout.write(self.style.ERROR(f"  ✗ Notifications Failed: {notification_failed_count}"))
        if already_exists_count > 0:
            self.stdout.write(f"  ℹ  Already Calculated: {already_exists_count}")
        if no_data_today_count > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠  No Target Day Data Yet: {no_data_today_count}"))
        if no_target_count > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠  No Target (insufficient data): {no_target_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  ✗ Errors: {error_count}"))
        self.stdout.write("="*60)

    def calculate_for_participant(self, participant, skip_notifications=False):
        """Calculate target for a single participant and optionally send notification"""
        result = {
            'status': None,
            'notification_sent': False,
            'notification_attempted': False
        }

        try:
            today = date.today()
            today_str = today.strftime('%Y-%m-%d')

            # Check if target already exists for today
            targets = participant.targets or {}
            if today_str in targets and targets[today_str].get('new_target'):
                self.stdout.write(
                    f"  {participant.user.email}: Target already exists for today - skipping"
                )
                result['status'] = 'already_exists'
                return result

            # CRITICAL: Check for target day data before calculating
            daily_steps = participant.daily_steps or []

            def safe_int(value, default=0):
                """Safely convert value to int"""
                try:
                    return int(value) if value else default
                except (ValueError, TypeError):
                    return default

            has_today_data = any(
                entry.get('date') == today_str and safe_int(entry.get('value')) > 0
                for entry in participant.daily_steps
            )

            if not has_today_data:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠  {participant.user.email}: No step data from today yet - skipping calculation"
                    )
                )
                result['status'] = 'no_data_today'
                return result

            # Now safe to calculate - we know all 7 days are synced
            goal_data = run_weekly_algorithm(participant)

            if goal_data:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {participant.user.email}: Target calculated - {goal_data['new_target']} steps/day"
                    )
                )
                result['status'] = 'success'

                # Send notification unless skipped
                if not skip_notifications:
                    result['notification_attempted'] = True
                    notification_sent = send_goal_notification(participant, goal_data)

                    if notification_sent:
                        result['notification_sent'] = True
                        self.stdout.write(f"  → Notification sent")
                    else:
                        self.stdout.write(self.style.WARNING(f"  → Notification failed (logged to status_flags)"))
                else:
                    self.stdout.write(f"  → Notification skipped")

                return result
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠  {participant.user.email}: No target calculated (insufficient data or first week)"
                    )
                )
                result['status'] = 'no_target'
                return result

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ {participant.user.email}: {str(e)}")
            )
            logger.exception(f"Error calculating target for participant {participant.id}")
            result['status'] = 'error'
            return result
