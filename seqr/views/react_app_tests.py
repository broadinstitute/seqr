from django.urls.base import reverse
import mock
import responses

from seqr.views.react_app import main_app, no_login_main_app
from seqr.views.utils.terra_api_utils import TerraRefreshTokenFailedException
from seqr.views.utils.test_utils import TEST_OAUTH2_PROVIDER, AuthenticationTestCase, AnvilAuthenticationTestCase, USER_FIELDS

MOCK_GA_TOKEN = 'mock_ga_token' # nosec
FEATURE_UPDATE_FEED = """
<?xml version="1.0" ?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" xml:lang="en-US">
    <id>tag:github.com,2008:/broadinstitute/seqr/discussions/categories/feature-updates</id>
    <link type="text/html" rel="alternate" href="https://github.com/broadinstitute/seqr/discussions/categories/feature-updates"/>
    <link type="application/atom+xml" rel="self" href="https://github.com/broadinstitute/seqr/discussions/categories/feature-updates.atom"/>
    <title>Recent discussions in broadinstitute/seqr, category: feature-updates</title>
    <updated>2023-11-08T15:11:40+00:00</updated>
    <entry>
        <id>tag:github.com,2008:5828412</id>
        <link type="text/html" rel="alternate" href="https://github.com/broadinstitute/seqr/discussions/3713"/>
        <title>Welcome to Feature Updates</title>
        <published>2023-11-08T15:11:31+00:00</published>
        <updated>2023-11-08T15:11:40+00:00</updated>
        <media:thumbnail height="30" width="30" url="https://avatars.githubusercontent.com/u/24598672?s=30&amp;v=4"/>
        <author>
            <name>hanars</name>
            <uri>https://github.com/hanars</uri>
        </author>
        <content type="html">
            &lt;p dir=&quot;auto&quot;&gt;Welcome to the seqr feature update discussion channel! This channel will be used for all announcements of new seqr functionality&lt;/p&gt;
        </content>
        <content type="html">
            &lt;h2 dir=&quot;auto&quot;&gt;Welcome to our discussion forum!&lt;/h2&gt;
            &lt;p dir=&quot;auto&quot;&gt;We\xe2\x80\x99re using Discussions as a place to connect members of the seqr community with our development team and with one another. We hope that you:&lt;/p&gt;
            &lt;ul dir=&quot;auto&quot;&gt;
            &lt;li&gt;Ask questions&lt;/li&gt;
            &lt;li&gt;Describe issues that may be user errors instead of bugs&lt;/li&gt;
            &lt;li&gt;Answer and engage with one another&lt;/li&gt;
            &lt;li&gt;Discuss ideas for enhancements&lt;/li&gt;
            &lt;/ul&gt;
        </content>
    </entry>
    <entry>
        <id>tag:github.com,2008:3913526</id>
        <link type="text/html" rel="alternate" href="https://github.com/broadinstitute/seqr/discussions/2501"/>
        <title>[ACTION REQUIRED] Upcoming Deprecation of older docker images and static JS/CSS assets
        </title>
        <published>2022-03-03T16:25:56+00:00</published>
        <updated>2022-06-23T13:32:55+00:00</updated>
        <media:thumbnail height="30" width="30" url="https://avatars.githubusercontent.com/u/636687?s=30&amp;v=4"/>
        <author>
            <name>sjahl</name>
            <uri>https://github.com/sjahl</uri>
        </author>
        <content type="html">
            &lt;h3 dir=&quot;auto&quot;&gt;What is happening?&lt;/h3&gt;
            &lt;h4 dir=&quot;auto&quot;&gt;Summary&lt;/h4&gt;
            &lt;p dir=&quot;auto&quot;&gt;Seqr is making updates to how our docker images work, and you will need to update your deployment by 2022/04/04. Please see the information below for more details.&lt;/p&gt;
            &lt;h4 dir=&quot;auto&quot;&gt;Slightly Longer Version&lt;/h4&gt;
            &lt;p dir=&quot;auto&quot;&gt;We\xe2\x80\x99re making two functional changes to the way seqr is packaged in Docker.&lt;/p&gt;
            &lt;ol dir=&quot;auto&quot;&gt;
            &lt;li&gt;We will be removing the statically built javascript/CSS/HTML assets that are checked into git. These will now be generated in the docker image when it\xe2\x80\x99s built, rather than provided in the source code tree.&lt;/li&gt;
            &lt;li&gt;New docker images will be built every time we release seqr. These images will no longer &lt;code class=&quot;notranslate&quot;&gt;git pull&lt;/code&gt; to update themselves on startup.&lt;/li&gt;
            &lt;/ol&gt;
            &lt;p dir=&quot;auto&quot;&gt;However, if you are using a docker image from prior to when we made these changes, your installation still has the &lt;code class=&quot;notranslate&quot;&gt;git pull&lt;/code&gt; update functionality. If you do nothing, your seqr installation may break after 2022/04/04 when it pulls down the version of the seqr code that has the assets removed. You will find instructions below on how to proceed.&lt;/p&gt;
        </content>
    </entry>
</feed>
"""


@mock.patch('seqr.views.react_app.DEBUG', False)
@mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
class AppPageTest(object):
    databases = ['default']
    fixtures = ['users']

    def _check_page_html(self, response,  user, user_key='user', vlm_enabled=False, user_email=None, user_fields=None, ga_token_id=None, last_feature_update=None):
        user_fields = user_fields or USER_FIELDS
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertSetEqual(set(initial_json.keys()), {'meta', user_key})
        self.assertSetEqual(set(initial_json[user_key].keys()), user_fields)
        self.assertEqual(initial_json[user_key]['username'], user)
        self.assertDictEqual(initial_json['meta'], {
            'version': mock.ANY,
            'hijakEnabled': False,
            'oauthLoginProvider': self.OAUTH_PROVIDER,
            'vlmEnabled': vlm_enabled,
            'warningMessages': [{'id': 1, 'header': 'Warning!', 'message': 'A sample warning'}],
            'lastFeatureUpdate': last_feature_update,
        })

        self.assertEqual(self.get_initial_page_window('gaTrackingId', response), ga_token_id)
        self.assertEqual(self.get_initial_page_window('userEmail', response), user_email)
        nonce = self.get_initial_page_window('__webpack_nonce__', response)
        self.assertIn('nonce-{}'.format(nonce), response.get('Content-Security-Policy'))

        # test static assets are correctly loaded
        content = response.content.decode('utf-8')
        self.assertEqual(content.count('<script type="text/javascript" nonce="{}">'.format(nonce)), 6)

    @mock.patch('seqr.views.react_app.VLM_CLIENT_ID', 'abc123')
    @mock.patch('seqr.views.react_app.GA_TOKEN_ID', MOCK_GA_TOKEN)
    @responses.activate
    def test_react_page(self, mock_redis):
        url = reverse(main_app)
        self.check_require_login_no_policies(url, login_redirect_url='/login')

        responses.add(
            responses.GET,
            'https://github.com/broadinstitute/seqr/discussions/categories/feature-updates.atom',
            body=FEATURE_UPDATE_FEED,
        )
        response = self.client.get(url)
        self._check_page_html(response, 'test_user_no_policies', user_email='test_user_no_policy@test.com', ga_token_id=MOCK_GA_TOKEN, vlm_enabled=True, last_feature_update='2023-11-08T15:11:31+00:00')

        mock_redis.return_value.set.assert_called_with('feature_updates_latest_date', '"2023-11-08T15:11:31+00:00"')
        mock_redis.return_value.expire.assert_called_with('feature_updates_latest_date', 10800)

    @responses.activate
    def test_local_react_page(self, mock_redis):
        url = reverse(no_login_main_app)
        response = self.client.get(url, HTTP_HOST='localhost:3000')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertNotRegex(content, r'src="/static/app(-.*)js"')
        self.assertContains(response, 'src="/app.js"')
        self.assertNotRegex(content, r'<link\s+href="/static/app.*css"[^>]*>')

    @responses.activate
    def test_no_login_react_page(self, mock_redis):
        url = reverse(no_login_main_app)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertListEqual(list(initial_json.keys()), ['meta'])

        # test set password page correctly includes user from token
        response = self.client.get(
            '/login/set_password/pbkdf2_sha256$30000$y85kZgvhQ539$jrEC343555Itp+14w/T7U6u5XUxtpBZXKv8eh4=')
        self.assertEqual(response.status_code, 200)
        self._check_page_html(
            response, 'test_user_manager', user_key='newUser',
            user_fields={'id', 'firstName', 'lastName', 'username', 'email'},
        )

        response = self.client.get('/login/set_password/invalid_pwd')
        self.assertEqual(response.status_code, 404)

        # Even if page does not require login, include user metadata if logged in
        self.login_analyst_user()
        response = self.client.get(url)
        self._check_page_html(response, 'test_user')

    @responses.activate
    def test_react_page_additional_configs(self, mock_redis):
        url = reverse(main_app)
        self.check_require_login_no_policies(url, login_redirect_url='/login')

        mock_redis.return_value.get.return_value = '"2025-11-18T00:00:00Z"'

        response = self.client.get(url)
        self._check_page_html(response, 'test_user_no_policies', last_feature_update='2025-11-18T00:00:00Z')


class LocalAppPageTest(AuthenticationTestCase, AppPageTest):
    fixtures = ['users']
    OAUTH_PROVIDER = ''


class AnvilAppPageTest(AnvilAuthenticationTestCase, AppPageTest):
    fixtures = ['users']
    OAUTH_PROVIDER = TEST_OAUTH2_PROVIDER

    def test_react_page(self, *args, **kwargs):
        super(AnvilAppPageTest, self).test_react_page(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_group_members.assert_not_called()

        self.mock_get_groups.assert_called_with(self.no_policy_user)

        # check behavior if AnVIL API calls fail
        self.mock_get_groups.side_effect = TerraRefreshTokenFailedException('Refresh Error')
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login?next=/dashboard')
