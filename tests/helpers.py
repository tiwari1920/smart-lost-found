"""Small helpers shared by the test files."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

PASSWORD = 'CampusTest#2026'


def report_data(**overrides):
    """Valid data for the report form (today's date, so it is never in the future)."""
    data = {
        'title': 'Black earbuds', 'category': 'ELECTRONICS', 'brand': 'boAt',
        'color': 'Black', 'location': 'LIBRARY',
        'description': 'Black wireless earbuds with a charging case',
        'date': timezone.localdate().isoformat(), 'time': '15:00',
    }
    data.update(overrides)
    return data


def make_image(name='photo.png', size=(10, 10)):
    """A tiny real PNG image, ready to upload in a test."""
    buffer = io.BytesIO()
    Image.new('RGB', size, 'red').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')