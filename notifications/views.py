from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    # filter(user=request.user): everyone sees only THEIR OWN notifications
    notifications = Notification.objects.filter(user=request.user)[:50]
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
@require_POST   # changing data is always a POST (CSRF-protected)
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notification_list')