import io
import os
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from items.models import Item

from .helpers import PASSWORD, make_image, report_data
from .test_matching_service import make_item

TEMP_MEDIA = tempfile.mkdtemp()   # test photos go here, never into your real media/ folder


class UsersMixin:
    def setUp(self):
        self.alice = User.objects.create_user(
            'alice', email='alice@example.com', password=PASSWORD)
        self.bob = User.objects.create_user(
            'bob', email='bob@example.com', password=PASSWORD)

    def login(self, name):
        self.client.login(username=name, password=PASSWORD)


class ReportTests(UsersMixin, TestCase):
    def test_login_is_required(self):
        for name in ('report_lost', 'report_found'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)

    def test_a_lost_report_is_saved_for_the_logged_in_user(self):
        self.login('alice')
        response = self.client.post(reverse('report_lost'), report_data())
        item = Item.objects.get()
        self.assertRedirects(response, reverse('item_detail', args=[item.pk]))
        self.assertEqual(item.user, self.alice)
        self.assertEqual(item.item_type, Item.LOST)
        self.assertEqual(item.status, Item.LOST)

    def test_a_found_report_uses_found_wording_and_status(self):
        self.login('bob')
        response = self.client.get(reverse('report_found'))
        self.assertContains(response, 'Where was it found?')
        self.assertContains(response, 'Date found')
        self.client.post(reverse('report_found'), report_data())
        item = Item.objects.get()
        self.assertEqual(item.item_type, Item.FOUND)
        self.assertEqual(item.status, Item.FOUND)

    def test_owner_type_and_status_cannot_be_faked(self):
        self.login('alice')
        data = report_data(user=self.bob.pk, item_type='FOUND', status='RECOVERED')
        self.client.post(reverse('report_lost'), data)
        item = Item.objects.get()
        self.assertEqual(item.user, self.alice)
        self.assertEqual(item.item_type, Item.LOST)
        self.assertEqual(item.status, Item.LOST)

    def test_a_future_date_is_rejected(self):
        self.login('alice')
        tomorrow = timezone.localdate() + timedelta(days=1)
        response = self.client.post(
            reverse('report_lost'), report_data(date=tomorrow.isoformat()))
        self.assertEqual(response.status_code, 200)
        self.assertIn('date', response.context['form'].errors)
        self.assertEqual(Item.objects.count(), 0)

    def test_missing_required_fields_are_rejected(self):
        self.login('alice')
        response = self.client.post(reverse('report_lost'), {'title': ''})
        self.assertEqual(response.status_code, 200)
        for field in ('title', 'category', 'color', 'description', 'location', 'date'):
            self.assertIn(field, response.context['form'].errors)
        self.assertEqual(Item.objects.count(), 0)

    def test_a_category_that_is_not_in_the_list_is_rejected(self):
        self.login('alice')
        response = self.client.post(reverse('report_lost'), report_data(category='HACKED'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('category', response.context['form'].errors)
        self.assertEqual(Item.objects.count(), 0)


class DetailTests(UsersMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.item = make_item(self.alice, Item.LOST, title='Black earbuds')
        self.url = reverse('item_detail', args=[self.item.pk])

    def test_login_is_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_an_unknown_report_gives_404(self):
        self.login('alice')
        response = self.client.get(reverse('item_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_the_owner_sees_edit_and_delete_links_but_strangers_do_not(self):
        edit_url = reverse('item_edit', args=[self.item.pk])
        delete_url = reverse('item_delete', args=[self.item.pk])
        self.login('alice')
        response = self.client.get(self.url)
        self.assertContains(response, edit_url)
        self.assertContains(response, delete_url)
        self.login('bob')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, edit_url)
        self.assertNotContains(response, delete_url)

    def test_the_reporters_email_is_never_shown(self):
        self.login('bob')
        response = self.client.get(self.url)
        self.assertContains(response, 'alice')
        self.assertNotContains(response, 'alice@example.com')


class EditTests(UsersMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.item = make_item(self.alice, Item.LOST, title='Black earbuds', color='Black')
        self.url = reverse('item_edit', args=[self.item.pk])

    def test_the_owner_can_edit(self):
        self.login('alice')
        response = self.client.post(self.url, report_data(color='Blue'))
        self.assertRedirects(response, reverse('item_detail', args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.color, 'Blue')
        self.assertEqual(self.item.item_type, Item.LOST)
        self.assertEqual(self.item.status, Item.LOST)

    def test_the_edit_page_keeps_the_found_wording_for_found_reports(self):
        found = make_item(self.bob, Item.FOUND, title='Black earbuds')
        self.login('bob')
        response = self.client.get(reverse('item_edit', args=[found.pk]))
        self.assertContains(response, 'Where was it found?')

    def test_strangers_get_404_and_cannot_change_anything(self):
        self.login('bob')
        self.assertEqual(self.client.get(self.url).status_code, 404)
        response = self.client.post(self.url, report_data(color='Hacked'))
        self.assertEqual(response.status_code, 404)
        self.item.refresh_from_db()
        self.assertEqual(self.item.color, 'Black')


class DeleteTests(UsersMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.item = make_item(self.alice, Item.LOST, title='Black earbuds')
        self.url = reverse('item_delete', args=[self.item.pk])

    def test_the_owner_deletes_after_confirming(self):
        self.login('alice')
        self.assertContains(self.client.get(self.url), 'Delete this report?')
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())   # GET deletes nothing
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('my_reports'))
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_strangers_get_404_and_nothing_is_deleted(self):
        self.login('bob')
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())


class StatusTests(UsersMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.item = make_item(self.alice, Item.LOST, title='Black earbuds')
        self.url = reverse('item_change_status', args=[self.item.pk])

    def test_the_owner_can_mark_recovered_or_closed(self):
        self.login('alice')
        for status in (Item.RECOVERED, Item.CLOSED):
            item = make_item(self.alice, Item.LOST, title='Another')
            response = self.client.post(
                reverse('item_change_status', args=[item.pk]), {'status': status})
            self.assertRedirects(response, reverse('item_detail', args=[item.pk]))
            item.refresh_from_db()
            self.assertEqual(item.status, status)

    def test_other_statuses_are_refused(self):
        self.login('alice')
        response = self.client.post(
            self.url, {'status': Item.VERIFICATION_PENDING}, follow=True)
        self.assertContains(response, 'not allowed')
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.LOST)

    def test_a_plain_link_cannot_change_the_status(self):
        self.login('alice')
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_strangers_get_404(self):
        self.login('bob')
        response = self.client.post(self.url, {'status': Item.CLOSED})
        self.assertEqual(response.status_code, 404)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.LOST)


class MyReportsTests(UsersMixin, TestCase):
    def test_only_your_own_reports_are_listed(self):
        make_item(self.alice, Item.LOST, title='Alice lost thing')
        make_item(self.bob, Item.LOST, title='Bob lost thing')
        self.login('alice')
        response = self.client.get(reverse('my_reports'))
        self.assertContains(response, 'Alice lost thing')
        self.assertNotContains(response, 'Bob lost thing')

    def test_an_empty_list_explains_itself(self):
        self.login('alice')
        response = self.client.get(reverse('my_reports'))
        self.assertContains(response, 'reported anything yet')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ImageUploadTests(UsersMixin, TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def test_a_real_photo_is_saved_under_a_random_name(self):
        self.login('alice')
        self.client.post(reverse('report_lost'), report_data(image=make_image('photo.png')))
        item = Item.objects.get()
        self.assertTrue(item.image.name.startswith('items/'))
        self.assertTrue(item.image.name.endswith('.png'))
        self.assertNotIn('photo', item.image.name)    # the original file name is thrown away
        self.assertTrue(os.path.exists(item.image.path))

    def test_a_text_file_is_rejected(self):
        self.login('alice')
        notes = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        response = self.client.post(reverse('report_lost'), report_data(image=notes))
        self.assertEqual(response.status_code, 200)
        self.assertIn('image', response.context['form'].errors)
        self.assertEqual(Item.objects.count(), 0)

    def test_a_fake_image_is_rejected(self):
        self.login('alice')
        fake = SimpleUploadedFile('evil.png', b'this is not an image', content_type='image/png')
        response = self.client.post(reverse('report_lost'), report_data(image=fake))
        self.assertEqual(response.status_code, 200)
        self.assertIn('image', response.context['form'].errors)
        self.assertEqual(Item.objects.count(), 0)

    def test_a_photo_over_2_mb_is_rejected(self):
        self.login('alice')
        noise = Image.frombytes('RGB', (1000, 1000), os.urandom(3 * 1000 * 1000))
        buffer = io.BytesIO()
        noise.save(buffer, format='PNG')
        big = SimpleUploadedFile('big.png', buffer.getvalue(), content_type='image/png')
        response = self.client.post(reverse('report_lost'), report_data(image=big))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'too large')
        self.assertEqual(Item.objects.count(), 0)

    def test_deleting_a_report_deletes_its_photo_file(self):
        self.login('alice')
        self.client.post(reverse('report_lost'), report_data(image=make_image()))
        item = Item.objects.get()
        path = item.image.path
        self.assertTrue(os.path.exists(path))
        self.client.post(reverse('item_delete', args=[item.pk]))
        self.assertFalse(os.path.exists(path))