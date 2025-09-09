# goals/models.py
from django.db import models
from core.models import Participant

class WeeklyGoal(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="weekly_goals")
    week_start = models.DateField()
    week_end = models.DateField()
    average_steps = models.IntegerField()
    increase = models.CharField(max_length=50)   # could be numeric or "maintain"/"increase to 10000"
    new_target = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("participant", "week_start")  # avoid duplicate goals per week
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.participant.user.username} – {self.week_start} target {self.new_target}"

