# core/management/commands/check_target_day_sync.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from core.models import Participant
from datetime import date
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check if participants have synced data on their target day (runs daily at noon)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--participant-id',
            type=int,
            help='Check sync for a specific participant ID only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without sending notifications',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for all participants',
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        today = date.today()
        
        self.stdout.write(f"Checking target day sync at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Today is: {today.strftime('%A, %Y-%m-%d')}\n")
        
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No notifications will be sent\n"))
        
        # Get participants to check
        if options['participant_id']:
            try:
                participant = Participant.objects.get(id=options['participant_id'])
                all_participants = [participant]
            except Participant.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Participant {options['participant_id']} not found")
                )
                return
        else:
            # Get only active participants
            all_participants = Participant.objects.select_related('user').filter(
                user__is_active=True
            ).all()
        
        if not all_participants:
            self.stdout.write(self.style.WARNING("No active participants to check"))
            return
        
        self.stdout.write(f"Checking {len(all_participants)} active participant(s)...\n")
        
        # Counters for summary
        not_target_day = 0
        target_day_synced = 0
        target_day_missing = 0
        alerts_sent = 0
        
        for participant in all_participants:
            result = self.check_participant_target_day(participant, today)
            
            if result == 'not_target_day':
                not_target_day += 1
            elif result == 'target_day_synced':
                target_day_synced += 1
            elif result == 'target_day_missing':
                target_day_missing += 1
            elif result == 'alert_sent':
                alerts_sent += 1
        
        # Summary
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(f"Completed in {duration:.1f} seconds")
        self.stdout.write(f"  Not target day: {not_target_day}")
        
        if target_day_synced > 0:
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Target day with data: {target_day_synced}")
            )
        if target_day_missing > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠  Target day missing data: {target_day_missing}")
            )
        if alerts_sent > 0:
            self.stdout.write(
                self.style.ERROR(f"  ✉  Admin alerts sent: {alerts_sent}")
            )
        self.stdout.write("="*70)
    
    def check_participant_target_day(self, participant, today):
        """
        Check if today is participant's target day and if they have data.
        Returns status string for summary reporting.
        """
        # Safety check
        if not participant.user or not participant.user.email:
            if self.verbose:
                self.stdout.write(f"  Participant ID {participant.id}: No user or email - skipping")
            return 'not_target_day'
        
        email = participant.user.email
        
        # Check if participant has a start_date
        if not participant.start_date:
            if self.verbose:
                self.stdout.write(f"  {email}: No start_date set - skipping")
            return 'not_target_day'
        
        # Check if today is their target day (same day of week as start_date)
        if today.weekday() != participant.start_date.weekday():
            if self.verbose:
                self.stdout.write(f"  {email}: Not target day (target is {participant.start_date.strftime('%A')})")
            return 'not_target_day'
        
        # Today IS their target day!
        if self.verbose:
            self.stdout.write(f"  {email}: TODAY IS TARGET DAY - checking for data...")
        
        # Get today's step data
        daily_steps_dict = {}
        if participant.daily_steps is not None:
            for entry in participant.daily_steps:
                date_key = entry.get('date')
                steps_value = entry.get('value')
                if date_key and steps_value is not None:
                    daily_steps_dict[date_key] = int(steps_value)
        
        today_str = today.strftime('%Y-%m-%d')
        today_steps = daily_steps_dict.get(today_str, 0)
        
        # Check if they have data for today
        if today_steps >= 1:
            # They have data! All good.
            if self.verbose:
                self.stdout.write(
                    self.style.SUCCESS(f"    ✓ Has data: {today_steps} steps today")
                )
            return 'target_day_synced'
        
        # No data on target day - send alert!
        self.stdout.write(
            self.style.WARNING(f"  ⚠  {email}: TARGET DAY with NO DATA - sending admin alert")
        )
        
        if not self.dry_run:
            # Check if we already sent an alert today
            if self.already_alerted_today(participant, today):
                self.stdout.write(f"    Already alerted today - skipping duplicate")
                return 'target_day_missing'
            
            # Send admin notification
            self.send_admin_alert(participant, today)
            
            # Mark that we sent alert today
            self.mark_alerted_today(participant, today)
            return 'alert_sent'
        
        return 'target_day_missing'
    
    def already_alerted_today(self, participant, today):
        """Check if we already sent a target day alert today."""
        device_sync_status = participant.device_sync_status or {}
        last_target_day_alert = device_sync_status.get('last_target_day_alert_date')
        
        if last_target_day_alert:
            return last_target_day_alert == today.isoformat()
        return False
    
    def mark_alerted_today(self, participant, today):
        """Mark that we sent a target day alert today."""
        status = participant.device_sync_status.copy() if participant.device_sync_status else {}
        
        status['last_target_day_alert_date'] = today.isoformat()
        
        # Add to history
        if 'target_day_alert_history' not in status:
            status['target_day_alert_history'] = []
        
        status['target_day_alert_history'].append({
            'date': today.isoformat(),
            'alert_time': timezone.now().isoformat(),
            'steps_on_day': 0
        })
        
        participant.device_sync_status = status
        participant.save(update_fields=['device_sync_status'])
    
    def send_admin_alert(self, participant, target_day):
        """Send email alert to admin about missing target day data."""
        subject = f"Target Day Alert: {participant.user.email} - No Data on Target Day"
        
        # Get participant's target day name
        target_day_name = target_day.strftime('%A')
        
        message = f"""Target Day Alert: Missing Data

Participant: {participant.user.email}
Participant ID: {participant.id}
Target Day: {target_day_name} ({target_day.strftime('%Y-%m-%d')})
Start Date: {participant.start_date.strftime('%Y-%m-%d')}

This participant has NOT synced their device today, and today is their weekly target day.
Without at least one step recorded today, we cannot be certain that the past week's data is complete.

Action Required:
1. Contact participant to remind them to sync their device TODAY
2. They need to wear device near phone with Bluetooth enabled
3. Open Fitbit app to trigger sync
4. Verify data appears for today

This is critical because target day data completeness ensures accurate weekly goal calculations.

View participant: {settings.BASE_URL}/admin/participant/{participant.id}/

This is an automated alert from the target day monitoring system.
"""
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'partnersteprimuhc@gmail.com')
        admin_emails = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', [from_email])
        
        # Handle both single email (string) and multiple emails (list)
        recipient_list = admin_emails if isinstance(admin_emails, list) else [admin_emails]
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            logger.info(f"Sent target day alert for {participant.user.email}")
            self.stdout.write(f"    ✉  Alert sent to {', '.join(recipient_list)}")
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(f"Failed to send target day alert for {participant.user.email}: {error_msg}")
            self.stderr.write(
                self.style.ERROR(f"    ✗ Failed to send email: {error_msg}")
            )
