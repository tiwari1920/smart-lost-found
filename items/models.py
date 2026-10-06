import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def item_image_path(instance, filename):
    """Save uploads as media/items/<random-name>.<ext>.
    The user's original filename is thrown away, so unsafe or
    duplicate names can never cause problems."""
    extension = Path(filename).suffix.lower()
    return f'items/{uuid.uuid4().hex}{extension}'


class Item(models.Model):
    # ----- Choices: (value stored in database, label shown to users) -----
    LOST = 'LOST'
    FOUND = 'FOUND'
    TYPE_CHOICES = [
        (LOST, 'Lost'),
        (FOUND, 'Found'),
    ]

    POTENTIAL_MATCH = 'POTENTIAL_MATCH'
    VERIFICATION_PENDING = 'VERIFICATION_PENDING'
    RECOVERED = 'RECOVERED'
    CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (LOST, 'Lost'),
        (FOUND, 'Found'),
        (POTENTIAL_MATCH, 'Potential Match'),
        (VERIFICATION_PENDING, 'Verification Pending'),
        (RECOVERED, 'Recovered'),
        (CLOSED, 'Closed'),
    ]

    CATEGORY_CHOICES = [
        ('ELECTRONICS', 'Electronics'),
        ('BAGS', 'Bags'),
        ('BOOKS', 'Books & Stationery'),
        ('CLOTHING', 'Clothing'),
        ('WALLETS', 'Wallets, Cards & IDs'),
        ('KEYS', 'Keys'),
        ('ACCESSORIES', 'Accessories & Jewellery'),
        ('SPORTS', 'Sports Items'),
        ('OTHER', 'Other'),
    ]

    # Edit this list to match your real campus. On Day 6 the matcher
    # will use it to decide which places are "near" each other.
    LOCATION_CHOICES = [
        ('LIBRARY', 'Library'),
        ('MAIN_BUILDING', 'Main Building'),
        ('CLASSROOM_BLOCK', 'Classroom Block'),
        ('COMPUTER_LAB', 'Computer Lab'),
        ('CANTEEN', 'Canteen'),
        ('SPORTS_GROUND', 'Sports Ground'),
        ('PARKING', 'Parking Area'),
        ('AUDITORIUM', 'Auditorium'),
        ('MAIN_GATE', 'Main Gate'),
        ('OTHER', 'Other'),
    ]

    # ----- Fields (each one becomes a column in the table) -----
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,   # if a user is deleted, their reports go too
        related_name='items',       # lets us write user.items.all()
    )
    item_type = models.CharField(max_length=5, choices=TYPE_CHOICES)
    title = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    brand = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=30)
    description = models.TextField()
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)   # approximate time is optional
    image = models.ImageField(
        upload_to=item_image_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    status = models.CharField(max_length=25, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)  # set once, when created
    updated_at = models.DateTimeField(auto_now=True)      # refreshed on every save

    class Meta:
        ordering = ['-created_at']   # newest first, everywhere

    def __str__(self):
        return f'{self.get_item_type_display()}: {self.title}'

    @property
    def status_badge_class(self):
        """Bootstrap colour for the status badge (used in 3B)."""
        return {
            self.LOST: 'bg-danger',
            self.FOUND: 'bg-success',
            self.POTENTIAL_MATCH: 'bg-warning text-dark',
            self.VERIFICATION_PENDING: 'bg-info text-dark',
            self.RECOVERED: 'bg-primary',
            self.CLOSED: 'bg-secondary',
        }.get(self.status, 'bg-secondary')