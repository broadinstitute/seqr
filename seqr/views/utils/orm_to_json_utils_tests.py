from django.contrib.auth.models import User
from django.test import TestCase

from seqr.views.utils.orm_to_json_utils import _get_json_for_user


class JSONUtilsTest(TestCase):
    fixtures = ['users.json']

    def test_json_utils(self):
        for user in User.objects.all():
            user_json = _get_json_for_user(user)
            user_json_keys = set(user_json.keys())

            self.assertSetEqual(
                user_json_keys,
                set(('date_joined', 'email', 'first_name', 'id', 'is_active', 'is_staff', 'last_login', 'last_name', 'username'))
            )
