

import mock

from seqr.views.apis.feature_updates_api import get_feature_updates

GET_FEED_RESPONSE = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" xml:lang="en-US">
  <id>tag:github.com,2008:/broadinstitute/seqr/discussions/categories/feature-updates</id>
  <link type="text/html" rel="alternate" href="https://github.com/broadinstitute/seqr/discussions/categories/feature-updates"/>
  <link type="application/atom+xml" rel="self" href="https://github.com/broadinstitute/seqr/discussions/categories/feature-updates.atom"/>
  <title>Recent discussions in broadinstitute/seqr, category: feature-updates</title>
  <updated>2023-11-08T15:11:40+00:00</updated>
  <entry>
    <id>tag:github.com,2008:5828412</id>
    <link type="text/html" rel="alternate" href="https://github.com/broadinstitute/seqr/discussions/3713"/>
    <title>
      Welcome to Feature Updates
    </title>
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
  </entry>
</feed>
'''


class FeatureUpdatesPageTest(object):

    @mock.patch('seer.views.apis.feature_updates_api.requests.get')
    def test_get_feature_updates(self, mock_requests_get):
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.content.return_value = bytes(GET_FEED_RESPONSE, 'utf8')

        actual = get_feature_updates(mock.Mock())

        assert actual == {
            "entries": []
        }
