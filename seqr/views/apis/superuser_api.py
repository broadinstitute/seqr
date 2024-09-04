from django.contrib.auth.models import User

from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_user
from seqr.views.utils.permissions_utils import superuser_required, get_analyst_user_emails, get_pm_user_emails
from seqr.views.utils.terra_api_utils import is_cloud_authenticated


@superuser_required
def get_all_users(request):
    user_tups = [(user, get_json_for_user(user, fields=[
        'username', 'email', 'last_login', 'date_joined', 'id', 'is_superuser', 'is_active',
        'display_name', 'is_data_manager',
    ])) for user in User.objects.exclude(email='')]
    analyst_users = get_analyst_user_emails(request.user)
    pm_users = get_pm_user_emails(request.user)
    users = [dict(
        hasCloudAuth=is_cloud_authenticated(user),
        isAnalyst=user.email in analyst_users,
        isPm=user.email in pm_users,
        **user_json
    ) for user, user_json in user_tups]

    return create_json_response({'users': users})
