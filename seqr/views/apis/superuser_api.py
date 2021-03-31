import logging

from django.contrib.auth.models import User

from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user
from seqr.views.utils.permissions_utils import superuser_required
logger = logging.getLogger(__name__)


@superuser_required
def get_all_users(request):
    users = [_get_json_for_user(user, is_anvil=False) for user in User.objects.exclude(email='')]

    return create_json_response({'users': users})
