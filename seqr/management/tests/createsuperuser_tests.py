from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class CreateSuperuserTest(TestCase):
    fixtures = ['users']

    def test_command(self):
        call_command(
            'createsuperuser', interactive=False, username='new_superuser',
            email='new_superuser@test.com', verbosity=0,
        )
        user = User.objects.get(email='new_superuser@test.com')
        self.assertEqual(user.username, 'new_superuser')
        self.assertTrue(user.is_superuser)

        with self.assertRaises(CommandError) as err:
            call_command(
                'createsuperuser', interactive=False, username='dup_superuser',
                email='Test_Superuser@test.com', verbosity=0,
            )
        self.assertEqual(str(err.exception), 'That email is already taken.')
        self.assertFalse(User.objects.filter(username='dup_superuser').exists())
