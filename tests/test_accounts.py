from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .helpers import PASSWORD


class RegisterTests(TestCase):
    def data(self, **overrides):
        data = {'username': 'newuser', 'email': 'new@example.com',
                'password1': PASSWORD, 'password2': PASSWORD}
        data.update(overrides)
        return data

    def test_register_creates_a_user_and_logs_them_in(self):
        response = self.client.post(reverse('register'), self.data())
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))

    def test_password_is_stored_hashed(self):
        self.client.post(reverse('register'), self.data())
        user = User.objects.get(username='newuser')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse('register'), self.data(password2='Different#2026'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse('register'), self.data(password1='password', password2='password'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_email_is_required(self):
        response = self.client.post(reverse('register'), self.data(email=''))
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)

    def test_email_must_be_unique_ignoring_case(self):
        User.objects.create_user('taken', email='taken@example.com', password=PASSWORD)
        response = self.client.post(
            reverse('register'), self.data(email='TAKEN@Example.com'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_username_must_be_unique(self):
        User.objects.create_user('newuser', email='other@example.com', password=PASSWORD)
        response = self.client.post(reverse('register'), self.data())
        self.assertEqual(response.status_code, 200)
        self.assertIn('username', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_logged_in_users_are_sent_home(self):
        user = User.objects.create_user('someone', password=PASSWORD)
        self.client.force_login(user)
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('home'))


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'alice', email='alice@example.com', password=PASSWORD)

    def login_data(self, **overrides):
        data = {'username': 'alice', 'password': PASSWORD}
        data.update(overrides)
        return data

    def test_login_with_the_right_password(self):
        response = self.client.post(reverse('login'), self.login_data())
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))

    def test_wrong_password_is_refused(self):
        response = self.client.post(reverse('login'), self.login_data(password='wrong'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username and password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_blocked_users_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(reverse('login'), self.login_data())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_returns_to_the_page_you_asked_for(self):
        url = reverse('login') + '?next=' + reverse('profile')
        response = self.client.post(url, self.login_data())
        self.assertRedirects(response, reverse('profile'))

    def test_protected_pages_send_visitors_to_the_login_page(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, '/accounts/login/?next=/accounts/profile/')

    def test_logout_ends_the_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            'alice', email='alice@example.com', password=PASSWORD)
        self.bob = User.objects.create_user(
            'bob', email='bob@example.com', password=PASSWORD)
        self.client.force_login(self.alice)

    def test_profile_is_updated(self):
        response = self.client.post(reverse('profile'), {
            'first_name': 'Alice', 'last_name': 'Rao', 'email': 'alice.rao@example.com'})
        self.assertRedirects(response, reverse('profile'))
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.first_name, 'Alice')
        self.assertEqual(self.alice.last_name, 'Rao')
        self.assertEqual(self.alice.email, 'alice.rao@example.com')

    def test_keeping_your_own_email_is_allowed(self):
        response = self.client.post(reverse('profile'), {
            'first_name': 'Alice', 'last_name': '', 'email': 'alice@example.com'})
        self.assertRedirects(response, reverse('profile'))

    def test_the_email_of_another_account_is_refused(self):
        response = self.client.post(reverse('profile'), {
            'first_name': '', 'last_name': '', 'email': 'bob@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, 'alice@example.com')

    def test_the_username_cannot_be_changed_through_the_form(self):
        self.client.post(reverse('profile'), {
            'first_name': '', 'last_name': '', 'email': 'alice@example.com',
            'username': 'hacker'})
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.username, 'alice')