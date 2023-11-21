from django.test import TestCase
from django.urls.base import reverse

import mock

from seqr.views.apis.feature_updates_api import get_feature_updates

GET_FEED_RESPONSE_XML = """
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


class FeatureUpdatesPageTestCase(TestCase):
    @mock.patch("seqr.views.apis.feature_updates_api.requests.get")
    def test_get_feature_updates(self, mock_requests_get):
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.content = bytes(GET_FEED_RESPONSE_XML, "utf-8")

        url = reverse(get_feature_updates)
        response = self.client.get(url)

        expected_response_json = {
            "entries": [
                {
                    "author": "hanars",
                    "author_link": "https://github.com/hanars",
                    "link": "https://github.com/broadinstitute/seqr/discussions/3713",
                    "markdown": "Welcome to the seqr feature update discussion channel! This channel will be used for all announcements of new seqr functionality\n\nWelcome to our discussion forum!\n--------------------------------\n\n\nWe’re using Discussions as a place to connect members of the seqr community with our development team and with one another. We hope that you:\n\n\n* Ask questions\n* Describe issues that may be user errors instead of bugs\n* Answer and engage with one another\n* Discuss ideas for enhancements\n",
                    "published_datestr": "2023-11-08T15:11:31+00:00",
                    "title": "Welcome to Feature Updates",
                },
                {
                    "author": "sjahl",
                    "author_link": "https://github.com/sjahl",
                    "link": "https://github.com/broadinstitute/seqr/discussions/2501",
                    "markdown": "### What is happening?\n\n\n#### Summary\n\n\nSeqr is making updates to how our docker images work, and you will need to update your deployment by 2022/04/04. Please see the information below for more details.\n\n\n#### Slightly Longer Version\n\n\nWe’re making two functional changes to the way seqr is packaged in Docker.\n\n\n1. We will be removing the statically built javascript/CSS/HTML assets that are checked into git. These will now be generated in the docker image when it’s built, rather than provided in the source code tree.\n2. New docker images will be built every time we release seqr. These images will no longer `git pull` to update themselves on startup.\n\n\nHowever, if you are using a docker image from prior to when we made these changes, your installation still has the `git pull` update functionality. If you do nothing, your seqr installation may break after 2022/04/04 when it pulls down the version of the seqr code that has the assets removed. You will find instructions below on how to proceed.\n\n",
                    "published_datestr": "2022-03-03T16:25:56+00:00",
                    "title": "[ACTION REQUIRED] Upcoming Deprecation of older docker images and static JS/CSS assets",
                },
            ]
        }
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), expected_response_json)

    @mock.patch("seqr.views.apis.feature_updates_api.requests.get")
    def test_get_feature_updates_raises_error(self, mock_requests_get):
        mock_requests_get.side_effect = Exception("Unable to fetch.")

        url = reverse(get_feature_updates)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"], "Unable to fetch.")
