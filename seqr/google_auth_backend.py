import logging

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from google.oauth2 import id_token
from google.auth.transport import requests

from seqr.models import AnvilUser
from seqr.models import CAN_EDIT, IS_OWNER
from seqr.views.utils.terra_api_utils import AnvilSession, scopes, service_account_session, anvilSessionStore

logger = logging.getLogger(__name__)


class AuthenticationBackend(ModelBackend):

    def authenticate(self, request, token, creds):

        try:
            # Decode the id token (It is a JWT token actually) to get user ID info
            idinfo = id_token.verify_oauth2_token(token, requests.Request())
        except:
            return

        # Use user's Google ID to look for the user record in the model
        anvil_user = AnvilUser.objects.filter(email__iexact = idinfo['email']).first()

        if anvil_user:  # The user has registered on seqr
            user = anvil_user.user
        else:  # Un-registered user, auto-register the Google account to the local account with the same email address
            user, created = User.objects.get_or_create(email__iexact = idinfo['email'])
            if created:
                user.username = User.objects.make_random_password()
                user.save()
            AnvilUser(user = user, email = idinfo['email']).save()

        session = AnvilSession(credentials = creds, scopes = scopes)
        try:
            # Todo: Update user names according to the profile from AnVIL
            profile = session.get_anvil_profile()
        except:
            logger.warning("Failed to get user profile for user {}".format(idinfo['email']))
            return

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def has_perm(self, user, perm, project=None):
        session = anvilSessionStore.get_session(user)
        if hasattr(project, 'workspace') and session:
            session = service_account_session # Todo: remove this line after seqr is whitelisted
            workspace = project.workspace.split('/') if project.workspace is not None else ''
            if len(workspace) == 2:
                collaborators = session.get_workspace_acl(workspace[0], workspace[1])
                if user.anviluser.email in collaborators.keys():
                    permission = collaborators[user.anviluser.email]
                    if permission['pending']:
                        return False
                    if perm is IS_OWNER:
                        return permission['accessLevel'] == 'OWNER'
                    if perm is CAN_EDIT:
                        return (permission['accessLevel'] == 'WRITER') or (permission['accessLevel'] == 'OWNER')
                    return True
                return False

        # if the project hasn't been connected to an AnVIL workspace yet than use the local permissions
        return super().has_perm(user, perm, project)

