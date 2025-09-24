# management/commands/test_targets.py
from django.core.management.base import BaseCommand
from goals.targets import run_weekly_algorithm
from core.models import Participant

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('participant_id', type=int)
    
    def handle(self, *args, **options):
        participant = Participant.objects.get(id=options['participant_id'])
        result = run_weekly_algorithm(participant)
        self.stdout.write(f"Result: {result}")