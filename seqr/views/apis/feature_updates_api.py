from dataclasses import dataclass, asdict

from feedparser import parse
from markdownify import markdownify as md

import requests

from seqr.views.utils.json_utils import create_json_response


@dataclass
class FeedEntry:
    """Class representative of one Atom feed entry."""
    title: str
    markdown: str
    published_datestr: str
    link: str
    author: str
    author_link: str


def get_feature_updates(request):
    """
    Fetches the feature-updates GitHub Discussion Atom feed, converts feed entries into markdown, and returns
    markdown and information for each feed entry.
    """
    # url = "https://github.com/broadinstitute/seqr/discussions/categories/feature-updates.atom"
    url = "https://github.com/broadinstitute/seqr/discussions/categories/announcements.atom"
    response = requests.get(url)
    response.raise_for_status()

    feed = parse(response.content)

    entries = []
    for entry in feed.entries:
        # Atom feeds can have multiple content elements per feed entry
        markdown = ''
        for content in entry.content:
            markdown = markdown + (md(content.value)) + md("<br>")

        entries.append(
            asdict(FeedEntry(title=entry.title, markdown=markdown, published_datestr=entry.published, link=entry.link,
                             author=entry.author, author_link=entry.href)))

    return create_json_response({'entries': entries})
