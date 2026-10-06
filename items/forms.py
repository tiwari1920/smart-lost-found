from django import forms
from django.utils import timezone

from accounts.forms import BootstrapFormMixin

from .models import Item

MAX_IMAGE_MB = 2


class ItemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Item
        # user, item_type and status are NOT listed on purpose:
        # the view sets them, so a visitor can't fake them.
        fields = [
            'title', 'category', 'brand', 'color', 'description',
            'location', 'date', 'time', 'image',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }
        help_texts = {
            'title': 'Short name, e.g. "Black boAt earbuds".',
            'brand': 'Optional, e.g. boAt, Nike, Casio.',
            'color': 'Main colour, e.g. Black.',
            'description': 'Size, marks, stickers, case, etc. Do not write phone numbers or other private details.',
            'time': 'Approximate time is fine. Leave empty if unsure.',
            'image': 'Optional. JPG, PNG or WEBP, up to 2 MB.',
        }

    def clean_date(self):
        date = self.cleaned_data['date']
        if date > timezone.localdate():
            raise forms.ValidationError('The date cannot be in the future.')
        return date

    def clean_image(self):
        image = self.cleaned_data.get('image')
        # Only NEW uploads have 'content_type'; a photo already saved does not
        if image and hasattr(image, 'content_type'):
            if image.size > MAX_IMAGE_MB * 1024 * 1024:
                raise forms.ValidationError(f'Image is too large. Maximum size is {MAX_IMAGE_MB} MB.')
        return image