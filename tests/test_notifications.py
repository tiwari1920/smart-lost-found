from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification
from notifications.services import notify_new_matches

from .test_match_results import PASSWORD, ExampleDataMixin


class NotificationTests(ExampleDataMixin, TestCase):
    def login(self, name):
        self.client.login(username=name, password=PASSWORD)

    def test_strong_new_match_notifies_the_other_owner(self):
        sent = notify_new_matches(self.found_earbuds)
        self.assertEqual(sent, 1)
        notification = Notification.objects.get()
        self.assertEqual(notification.user, self.alice)      # the owner of the lost report
        self.assertEqual(notification.notification_type, Notification.MATCH)
        self.assertIn('Black Bluetooth earbuds', notification.message)
        self.assertEqual(notification.link, reverse('item_matches', args=[self.lost.pk]))
        self.assertFalse(notification.is_read)

    def test_weak_matches_do_not_notify(self):
        self.assertEqual(notify_new_matches(self.found_backpack), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_reporting_a_found_item_notifies_the_owner_of_the_lost_one(self):
        dave = User.objects.create_user('dave', password=PASSWORD)
        self.login('dave')
        self.client.post(reverse('report_found'), {
            'title': 'Black earbuds', 'category': 'ELECTRONICS', 'brand': 'boAt',
            'color': 'Black', 'location': 'LIBRARY',
            'description': 'Black wireless earbuds with a charging case',
            'date': timezone.localdate().isoformat(), 'time': '15:00',
        })
        self.assertEqual(
            Notification.objects.filter(user=self.alice, notification_type=Notification.MATCH).count(), 1)
        self.assertEqual(Notification.objects.filter(user=dave).count(), 0)

    def test_list_requires_login(self):
        response = self.client.get(reverse('notification_list'))
        self.assertEqual(response.status_code, 302)

    def test_each_user_sees_only_their_own_notifications(self):
        Notification.objects.create(user=self.alice, message='Hello Alice',
                                    notification_type=Notification.MATCH)
        Notification.objects.create(user=self.bob, message='Hello Bob',
                                    notification_type=Notification.MATCH)
        self.login('alice')
        response = self.client.get(reverse('notification_list'))
        self.assertContains(response, 'Hello Alice')
        self.assertNotContains(response, 'Hello Bob')

    def test_unread_count_and_mark_all_read(self):
        for text in ('One', 'Two'):
            Notification.objects.create(user=self.alice, message=text,
                                        notification_type=Notification.MATCH)
        Notification.objects.create(user=self.bob, message='Bobs',
                                    notification_type=Notification.MATCH)
        self.login('alice')
        self.assertEqual(self.client.get(reverse('home')).context['unread_notifications'], 2)

        response = self.client.post(reverse('mark_all_read'))
        self.assertRedirects(response, reverse('notification_list'))
        self.assertEqual(self.client.get(reverse('home')).context['unread_notifications'], 0)
        # Bob's notification is untouched
        self.assertEqual(Notification.objects.filter(user=self.bob, is_read=False).count(), 1)