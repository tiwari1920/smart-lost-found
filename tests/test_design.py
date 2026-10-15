from django.test import TestCase
from django.urls import reverse


class DesignTests(TestCase):
    def test_home_page_loads_the_theme_file(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'css/campusfind.css')
        self.assertContains(response, 'data-bs-theme="dark"')

    def test_developer_details_are_on_every_page(self):
        for name in ('home', 'login', 'register'):
            response = self.client.get(reverse(name))
            self.assertContains(response, 'Satyam Tiwari')
            self.assertContains(response, 'iamsatyampandit@gmail.com')
            self.assertContains(response, 'CampusFind by Tiwari')

    def test_home_page_has_the_new_hero(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Matched in seconds')
        self.assertContains(response, reverse('register'))