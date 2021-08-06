from social_core.backends.okta import OktaMixin, OktaOAuth2
from social_core.backends.open_id_connect import OpenIdConnectAuth


class McriOktaMixin(OktaMixin):
    """
    Overridden to fix paths to authorisation server.  At MCRI, we're using Org level authorisation server but
    social_core.backends.okta.OktaMixin assumes Custom Authorisation Server.  See differences between the two:
    https://support.okta.com/help/s/article/Difference-Between-Okta-as-An-Authorization-Server-vs-Custom-Authorization-Server?language=en_US 
    """

    def authorization_url(self):
        return self._url('oauth2/v1/authorize')

    def access_token_url(self):
        return self._url('oauth2/v1/token')


class McriOktaOAuth2(McriOktaMixin, OktaOAuth2):
    """
    Overridden for following reasons:
    * Include custom idp_groups from groups claim
    * Include groups as default scope
    * Fix path to /userinfo as using Org level authorisation server
    """

    def auth_html(self):
        pass

    DEFAULT_SCOPE = [
        'openid', 'profile', 'email', 'groups'
    ]

    def get_user_details(self, response):
        """Return user details from Okta account"""
        return {'username': response.get('preferred_username'),
                'email': response.get('email') or '',
                'first_name': response.get('given_name'),
                'last_name': response.get('family_name'),
                'idp_groups': response.get('groups'),
                }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from Okta"""
        return self.get_json(
            self._url('oauth2/v1/userinfo'),
            headers={
                'Authorization': 'Bearer {}'.format(access_token),
            }
        )


class McriOktaOpenIdConnect(McriOktaOAuth2, OpenIdConnectAuth):
    name = 'okta-openidconnect'
    REDIRECT_STATE = False
    ACCESS_TOKEN_METHOD = 'POST'
    RESPONSE_TYPE = 'code'
