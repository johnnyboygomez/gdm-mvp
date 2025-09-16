from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import CustomUser, Participant
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Bulk create test users and participants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of users to create (default: 20)'
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='testuser',
            help='Email prefix (default: testuser). Creates testuser1@test.com, testuser2@test.com, etc.'
        )
        parser.add_argument(
            '--domain',
            type=str,
            default='test.com',
            help='Email domain (default: test.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='testpass123',
            help='Password for all test users (default: testpass123)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for participants (YYYY-MM-DD). If not provided, uses random dates within last 30 days.'
        )
        parser.add_argument(
            '--id-start',
            type=int,
            default=1,
            help='User number to start with for suffix (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        count = options['count']
        prefix = options['prefix']
        domain = options['domain']
        password = options['password']
        dry_run = options['dry_run']
        id_start = options['id_start']
        
        # Handle start date
        if options['start_date']:
            from datetime import datetime
            base_start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
        else:
            base_start_date = None

        if dry_run:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE - No users will be created"))

        self.stdout.write(f"Creating {count} test users:")
        self.stdout.write(f"  📧 Email pattern: {prefix}N@{domain} (N starts at {id_start})")
        self.stdout.write(f"  🔐 Password: {password}")
        
        created_users = []
        created_participants = []

        created = 0
        i = id_start
        with transaction.atomic():
            while created < count:
                email = f"{prefix}{i}@{domain}"

                # Generate start date
                if base_start_date:
                    start_date = base_start_date
                else:
                    # Random date within last 30 days
                    days_ago = random.randint(1, 30)
                    start_date = date.today() - timedelta(days=days_ago)

                if CustomUser.objects.filter(email=email).exists():
                    self.stdout.write(self.style.WARNING(f"  ⚠️ Skipping: {email} (already exists)"))
                else:
                    if not dry_run:
                        try:
                            # Create user
                            user = CustomUser.objects.create_user(
                                email=email,
                                password=password
                            )
                            created_users.append(user)
                            
                            # Create participant
                            participant = Participant.objects.create(
                                user=user,
                                start_date=start_date
                            )
                            created_participants.append(participant)
                            
                            self.stdout.write(f"  ✅ Created: {email} (Participant ID: {participant.id})")
                            created += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"  ❌ Error creating {email}: {e}")
                            )
                    else:
                        self.stdout.write(f"  📋 Would create: {email} (start date: {start_date})")
                        created += 1  # Still increment in dry run mode
                i += 1

        if not dry_run:
            self.stdout.write(f"\n🎉 SUCCESS!")
            self.stdout.write(f"Created {len(created_users)} users and {len(created_participants)} participants")
            
            if created_participants:
                participant_ids = [p.id for p in created_participants]
                self.stdout.write(f"\n📋 Participant IDs: {','.join(map(str, participant_ids))}")
                self.stdout.write(f"\n💡 To upload test data to these users:")
                self.stdout.write(f"python manage.py upload_test_data --csv-file your_data.csv --participant-ids {','.join(map(str, participant_ids))}")
        else:
            self.stdout.write(f"\n🧪 DRY RUN COMPLETE - Would have created {count} users")