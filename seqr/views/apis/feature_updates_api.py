from dataclasses import dataclass, asdict

from feedparser import parse
from markdownify import markdownify as md

import requests

from seqr.views.utils.json_utils import create_json_response


@dataclass
class FeedEntry:
    """Class representative of one Atom feed entry."""

    author: str
    author_link: str
    link: str
    markdown: str
    published_datestr: str
    title: str


def get_feature_updates(request):
    """
    Fetches the feature-updates GitHub Discussion Atom feed, converts feed entries into markdown, and returns
    markdown and information for each feed entry.
    """
    url = "https://github.com/broadinstitute/seqr/discussions/categories/feature-updates.atom"
    response = requests.get(url, timeout=5)
    response.raise_for_status()

    feed = parse(response.content)

    entries = []
    for entry in feed.entries:
        # Atom feeds can have multiple content elements per feed entry
        markdown = "".join(md(content.value) for content in entry.content)
        entries.append(
            asdict(
                FeedEntry(
                    author=entry.author,
                    author_link=entry.href,
                    link=entry.link,
                    markdown=markdown,
                    published_datestr=entry.published,
                    title=entry.title,
                )
            )
        )

    return create_json_response({"entries": entries})
