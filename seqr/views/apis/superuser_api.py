import logging

from django.contrib.auth.models import User

from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user
from seqr.views.utils.permissions_utils import superuser_required
from seqr.views.utils.terra_api_utils import is_google_authenticated
logger = logging.getLogger(__name__)


@superuser_required
def get_all_users(request):
    user_tups = [(user, _get_json_for_user(user, is_anvil=False)) for user in User.objects.exclude(email='')]
    users = [dict(hasGoogleAuth=is_google_authenticated(user), **user_json) for user, user_json in user_tups]

    return create_json_response({'users': users})
