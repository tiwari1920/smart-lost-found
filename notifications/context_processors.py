from .models import Notification


def unread_notifications(request):
    """Adds {{ unread_notifications }} (a number) to every template."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
    else:
        count = 0
    return {'unread_notifications': count}