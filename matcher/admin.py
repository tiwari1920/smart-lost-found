from django.contrib import admin

from .models import Match, Verification


class VerificationInline(admin.TabularInline):
    model = Verification
    extra = 0


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('lost_item', 'found_item', 'final_score', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [VerificationInline]