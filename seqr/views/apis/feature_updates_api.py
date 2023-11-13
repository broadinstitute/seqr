import feedparser
import requests

from seqr.views.utils.json_utils import create_json_response


def get_feature_updates(request):
    response = requests.get(
        "https://github.com/broadinstitute/seqr/discussions/categories/feature-updates.atom"
    )
    response.raise_for_status()

    parsed_feed = feedparser.parse(response.content)

    json_response = {
        'link': parsed_feed.feed.link,
        'entries': parsed_feed.entries,
    }
    return create_json_response(json_response)
