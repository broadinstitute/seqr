from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ValidationError


class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    """The built-in django login AuthenticationForm form only accepts usernames, not emails.
    This class extends it to allow either usernames or emails to be used to login.

    (based on: http://stackoverflow.com/questions/778382/accepting-email-address-as-username-in-django)
    """

    def clean_username(self):
        username = self.data['username']
        if '@' in username:
            try:
                username = User.objects.get(email=username).username
            except ObjectDoesNotExist:
                raise ValidationError(self.error_messages['invalid_login'],
                                      code='invalid_login',
                                      params={'username': self.username_field.verbose_name })
        return username