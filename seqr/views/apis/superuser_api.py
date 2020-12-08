import logging

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User

from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user
from settings import API_LOGIN_REQUIRED_URL

logger = logging.getLogger(__name__)


@user_passes_test(lambda u: u.is_active and u.is_superuser, login_url=API_LOGIN_REQUIRED_URL)
def get_all_users(request):
    users = [_get_json_for_user(user, is_anvil=False) for user in User.objects.exclude(email='')]

    return create_json_response({'users': users})
