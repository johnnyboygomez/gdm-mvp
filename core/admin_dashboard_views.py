# core/admin_dashboard_views.py
from datetime import date, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import Participant
from collections import defaultdict

def get_next_target_day(start_date):
    today = date.today()
    delta_days = (today - start_date).days
    if delta_days < 7:
        return None
    weeks = delta_days // 7
    next_target = start_date + timedelta(days=7 * (weeks + 1))
    if delta_days % 7 == 0:
        return today
    return next_target

@staff_member_required
def dashboard_view(request):
    is_superuser = request.user.is_superuser
    is_manager = request.user.groups.filter(name="Managers").exists() and not is_superuser
    raw_participants = Participant.objects.select_related('user').all().order_by('start_date')
    today = date.today()
    max_days = 7
    groups = defaultdict(list)
    header_days = {}
    
    for p in raw_participants:
        next_target = get_next_target_day(p.start_date)
        if not next_target:
            continue  # Skip this participant (not enough days yet)
        days_diff = (next_target - today).days
        if 0 <= days_diff < max_days:
            groups[days_diff].append({
                "email": p.user.email,
                "next_target_day": next_target,
            })
    
    for days in groups.keys():
        # Use the first participant's target day as the anchor
        block_date = groups[days][0]['next_target_day'] if groups[days] else today + timedelta(days=days)
        # Create a week of dates centered around or leading up to the block_date
        # This creates dates: [block_date-6, block_date-5, ..., block_date-1, block_date]
        header_days[days] = [block_date - timedelta(days=delta) for delta in range(6, -1, -1)]
    
    # Handle empty groups (days with no participants)
    for days in range(max_days):
        if days not in header_days:
            block_date = today + timedelta(days=days)
            header_days[days] = [block_date - timedelta(days=delta) for delta in range(6, -1, -1)]
    
    # Create a list of tuples that includes both the participants and their header days
    grouped_participants_with_headers = []
    for days in sorted(set(list(groups.keys()) + list(range(max_days)))):
        participants = groups[days] if days in groups else []
        if days not in header_days:
            block_date = today + timedelta(days=days)
            header_days[days] = [block_date - timedelta(days=delta) for delta in range(6, -1, -1)]
        
        grouped_participants_with_headers.append({
            'days': days,
            'participants': participants,
            'header_days': header_days[days]
        })
    
    context = {
        "is_superuser": is_superuser,
        "is_manager": is_manager,
        "grouped_participants_with_headers": grouped_participants_with_headers,
        "today": today,
        "user": request.user,
    }
    return render(request, "admin/dashboard.html", context)