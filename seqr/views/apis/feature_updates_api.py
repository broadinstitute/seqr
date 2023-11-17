from feedparser import parse
from markdownify import markdownify as md

import requests

from seqr.views.utils.json_utils import create_json_response

FEED_URL = (
    "https://github.com/broadinstitute/seqr/discussions/categories/feature-updates.atom"
)
TIMEOUT = 5


def get_feature_updates(request):
    """
    Fetches the feature-updates GitHub Discussion Atom feed, converts feed entries into markdown, and returns
    markdown and information for each feed entry.
    """
    response = requests.get(FEED_URL, timeout=TIMEOUT)
    response.raise_for_status()

    feed = parse(response.content)

    entries = []
    for entry in feed.entries:
        # Atom feeds can have multiple content elements per feed entry
        markdown = "".join(md(content.value) for content in entry.content)
        entries.append(
            {
                "author": entry.author,
                "author_link": entry.href,
                "link": entry.link,
                "markdown": markdown,
                "published_datestr": entry.published,
                "title": entry.title,
            }
        )

    return create_json_response({"entries": entries})
