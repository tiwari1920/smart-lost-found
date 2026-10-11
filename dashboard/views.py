from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .services import get_statistics


@login_required
def dashboard(request):
    # Authorization: only staff (administrators) may open this page
    if not request.user.is_staff:
        raise PermissionDenied   # shows "403 Forbidden"
    return render(request, 'dashboard/dashboard.html', {'stats': get_statistics()})