import datetime

import google.auth
import google.auth.transport.requests
import google.oauth2.credentials
import pytz

from loading_pipeline.lib.core import FeatureFlag

SERVICE_ACCOUNT_CREDENTIALS = None
CLOUD_PLATFORM_SCOPE = [
    'https://www.googleapis.com/auth/cloud-platform',
]
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid',
]
ONE_MINUTE_S = 60


def get_service_account_credentials() -> google.oauth2.credentials.Credentials:
    global SERVICE_ACCOUNT_CREDENTIALS
    if not SERVICE_ACCOUNT_CREDENTIALS:
        SERVICE_ACCOUNT_CREDENTIALS, _ = google.auth.default(
            scopes=[
                *SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE,
                *(CLOUD_PLATFORM_SCOPE if FeatureFlag.EXPECT_TDR_METRICS else []),
            ],
        )
    tz = pytz.UTC
    if (
        SERVICE_ACCOUNT_CREDENTIALS.token
        and (
            tz.localize(SERVICE_ACCOUNT_CREDENTIALS.expiry)
            - datetime.datetime.now(tz=tz)
        ).total_seconds()
        > ONE_MINUTE_S
    ):
        return SERVICE_ACCOUNT_CREDENTIALS
    SERVICE_ACCOUNT_CREDENTIALS.refresh(
        request=google.auth.transport.requests.Request(),
    )
    return SERVICE_ACCOUNT_CREDENTIALS
