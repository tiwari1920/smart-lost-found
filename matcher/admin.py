from django.contrib import admin
from django.urls import reverse

from notifications.models import Notification
from notifications.services import notify

from .models import Match, Verification
from .services.verification_service import ClaimError, admin_cancel_claim


class VerificationInline(admin.TabularInline):
    model = Verification
    extra = 0


@admin.action(description='Cancel selected claims (reopens both reports)')
def cancel_claims(modeladmin, request, queryset):
    cancelled = 0
    for match in queryset:
        try:
            admin_cancel_claim(match)
        except ClaimError:
            continue   # already finished: nothing to cancel
        message = (f'An administrator cancelled the claim for "{match.lost_item.title}". '
                   'Both reports are open again.')
        link = reverse('claim_detail', args=[match.pk])
        for user in (match.lost_item.user, match.found_item.user):
            notify(user, message, Notification.CLAIM, link)
        cancelled += 1
    modeladmin.message_user(request, f'{cancelled} claim(s) cancelled.')


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('lost_item', 'found_item', 'final_score', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [VerificationInline]
    actions = [cancel_claims]