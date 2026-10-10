from django.conf import settings
from django.db import models

from .services.scoring import get_label


class Match(models.Model):
    """A CLAIM: one lost report and one found report that the system suggested
    as a match. The scores are saved at the moment the claim starts."""

    VERIFICATION_PENDING = 'VERIFICATION_PENDING'
    CONFIRMED = 'CONFIRMED'
    REJECTED = 'REJECTED'
    WITHDRAWN = 'WITHDRAWN'
    COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (VERIFICATION_PENDING, 'Verification pending'),
        (CONFIRMED, 'Confirmed'),
        (REJECTED, 'Rejected'),
        (WITHDRAWN, 'Withdrawn'),
        (COMPLETED, 'Item recovered'),
    ]

    lost_item = models.ForeignKey(
        'items.Item', on_delete=models.CASCADE, related_name='matches_as_lost')
    found_item = models.ForeignKey(
        'items.Item', on_delete=models.CASCADE, related_name='matches_as_found')

    # The six similarity scores (0.0-1.0) and the final score (0-100)
    description_score = models.FloatField()
    category_score = models.FloatField()
    color_score = models.FloatField()
    brand_score = models.FloatField()
    location_score = models.FloatField()
    time_score = models.FloatField()
    final_score = models.FloatField()

    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default=VERIFICATION_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'matches'

    def __str__(self):
        return f'{self.lost_item.title} <-> {self.found_item.title} ({self.final_score}%)'

    @property
    def scores(self):
        """The six sub-scores in the same shape the engine uses."""
        return {
            'description': self.description_score,
            'category': self.category_score,
            'location': self.location_score,
            'color': self.color_score,
            'brand': self.brand_score,
            'time': self.time_score,
        }

    @property
    def label(self):
        return get_label(self.final_score)


class Verification(models.Model):
    """One private question from the finder, and the owner's answer."""

    ASKED = 'ASKED'
    ANSWERED = 'ANSWERED'
    STATUS_CHOICES = [
        (ASKED, 'Waiting for answer'),
        (ANSWERED, 'Answered'),
    ]

    match = models.ForeignKey(
        Match, on_delete=models.CASCADE, related_name='verifications')
    requester = models.ForeignKey(   # the owner who is claiming the item
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='verification_requests')
    question = models.TextField()
    answer = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ASKED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Question {self.pk} on match {self.match_id} ({self.status})'