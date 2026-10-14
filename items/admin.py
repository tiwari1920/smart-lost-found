from django.contrib import admin

from matcher.services.verification_service import active_claim_for

from .models import Item


def _set_status(modeladmin, request, queryset, new_status, done_text):
    """Change the status of several reports, skipping reports that belong to an
    active claim (those must be finished on the claim page)."""
    changed = skipped = 0
    for item in queryset:
        if active_claim_for(item):
            skipped += 1
            continue
        item.status = new_status
        item.save(update_fields=['status', 'updated_at'])
        changed += 1
    text = f'{changed} report(s) {done_text}.'
    if skipped:
        text += f' {skipped} skipped because they are part of an active claim.'
    modeladmin.message_user(request, text)


@admin.action(description='Hide selected reports (moderation)')
def hide_reports(modeladmin, request, queryset):
    count = queryset.update(is_hidden=True)
    modeladmin.message_user(request, f'{count} report(s) hidden.')


@admin.action(description='Unhide selected reports')
def unhide_reports(modeladmin, request, queryset):
    count = queryset.update(is_hidden=False, moderation_note='')
    modeladmin.message_user(request, f'{count} report(s) are visible again.')


@admin.action(description='Mark selected reports as recovered')
def mark_recovered(modeladmin, request, queryset):
    _set_status(modeladmin, request, queryset, Item.RECOVERED, 'marked as recovered')


@admin.action(description='Close selected reports')
def close_reports(modeladmin, request, queryset):
    _set_status(modeladmin, request, queryset, Item.CLOSED, 'closed')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type', 'category', 'location', 'status',
                    'is_hidden', 'user', 'created_at')
    list_filter = ('item_type', 'status', 'category', 'is_hidden')
    search_fields = ('title', 'description', 'brand', 'color')
    actions = [hide_reports, unhide_reports, mark_recovered, close_reports]