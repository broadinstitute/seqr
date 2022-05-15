import abc

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.urls import resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin

from google.oauth2 import id_token
from google.auth.transport import requests

from seqr.views.utils.permissions_utils import ServiceAccountAccess

from settings import SOCIAL_AUTH_GOOGLE_OAUTH2_KEY


class CheckServiceAccountAccessMiddleware(MiddlewareMixin):

    def process_request(self, request):
        try:
            # do this before any other methods can throw an error
            request.service_account_access = False
            func, _, _ = resolve(request.path)
            request.service_account_access = isinstance(func, ServiceAccountAccess)
        except Resolver404:
            # Some URLs do not resolve, like /login/google-oauth2
            # We're not trying to block anything, so let's just pass along
            pass


class DisableCSRFServiceAccountAccessMiddleware(MiddlewareMixin):

    def process_view(self, request, callback, callback_args, callback_kwargs):
        assert hasattr(request, 'service_account_access'), (
            'The seqr DisableCSRFServiceAccountAccess middleware requires '
            'CheckServiceAccountAccessMiddleware middleware to be installed. '
            'Edit your MIDDLEWARE setting to insert '
            '"seqr.utils.auth_middleware.CheckServiceAccountAccessMiddleware" before '
            '"seqr.utils.auth_middleware.DisableCSRFServiceAccountAccessMiddleware".'
        )

        if request.service_account_access:
            # only exempt CSRF if it's a service account access route
            callback.csrf_exempt = True


class BearerAuth(MiddlewareMixin, abc.ABC):
    def process_request(self, request):
        assert hasattr(request, 'service_account_access'), (
            f'The seqr {self.__class__.__name__} middleware requires '
            'CheckServiceAccountAccessMiddleware middleware to be installed. '
            'Edit your MIDDLEWARE setting to insert '
            '"seqr.utils.auth_middleware.CheckServiceAccountAccessMiddleware" before '
            f'"seqr.utils.auth_middleware.{self.__class__.__name__}".'
        )

        if request.service_account_access:
            authorization_value = request.META.get('HTTP_AUTHORIZATION', '')
            if not authorization_value.startswith('Bearer'):
                raise PermissionDenied('Expected Bearer token authorization for service account route')

            components = authorization_value.split(' ', maxsplit=1)
            if len(components) != 2:
                raise PermissionDenied('The Bearer token was not in the correct format')
            token = components[-1]
            email = self.validate_and_get_email_from_token(token)
            users = User.objects.filter(email__iexact=email)
            if users.count() != 1:
                raise PermissionDenied(f'No user found with email {email}')
            request.user = users.first()

    @abc.abstractmethod
    def validate_and_get_email_from_token(self, token):
        pass


class GoogleBearerAuth(BearerAuth):

    def validate_and_get_email_from_token(self, token):
        """
        From the "Authorization: Bearer {token}" header, validate
        """
        # assert here to allow non-service-account routes to still succeed
        #   (this triggers a 500 error to the client)
        assert SOCIAL_AUTH_GOOGLE_OAUTH2_KEY, (
            'You must specify a "SOCIAL_AUTH_GOOGLE_OAUTH2_CLIENT_ID" to use '
            'the "seqr.utils.auth_middleware.GoogleBearerAuth" middleware'
        )
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            )
        except ValueError as e:
            raise PermissionDenied(', '.join(e.args))

        if not idinfo.get('email_verified', False):
            raise PermissionDenied('The email address on the Bearer claim is not verified')

        email = idinfo.get('email')
        if not email:
            raise PermissionDenied('No email address was found in the Bearer claim')
        return email
