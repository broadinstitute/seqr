import os

from django.shortcuts import render
from django.conf import settings
from django.utils.encoding import smart_unicode
from django.http import Http404
import markdown

from xbrowse_server.decorators import log_request


DOCS_PAGES = [
    {'title': 'Beta Users Guide', 'slug': 'beta-users'},
    {'title': 'Data Organization', 'slug': 'data-organization'},
    {'title': 'Mendelian Variant Search', 'slug': 'mendelian-variant-search'},
    {'title': 'Combine Mendelian Families', 'slug': 'combine-mendelian-families'},
    {'title': 'Inheritance Methods', 'slug': 'inheritance-methods'},
    {'title': 'Variant Filters', 'slug': 'variant-filters'},
    {'title': 'Feature Reference', 'slug': 'feature-reference'},
]

@log_request('doc_page_id')
def docs_md(request, doc_page_id):

    markdown_file = "%s%s.md" % (settings.DOCS_DIR, doc_page_id)
    if not os.path.exists(markdown_file):
        raise Http404
    html_content = markdown.markdown(smart_unicode(open(markdown_file).read()))

    return render(request, 'docs/docs_base.html', {
        'html_content': html_content,
        'docs_pages': DOCS_PAGES,
    })