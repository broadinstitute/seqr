import json
import logging
from django.contrib.admin.views.decorators import staff_member_required

from seqr.views.utils.export_table_utils import export_table
from dateutil.parser import parse
from django.shortcuts import render
from settings import LOGIN_URL
from seqr.models import VariantTagType, VariantTag
from seqr.utils.xpos_utils import get_chrom_pos

logger = logging.getLogger(__name__)

HEADERS = ['project', 'family_id', 'timestamp', 'genes', 'chrom', 'pos', 'ref', 'alt']


@staff_member_required(login_url=LOGIN_URL)
def komp_export(request):

    if "download" in request.GET:
        logger.info("exporting komp tags")
        start_date = parse(request.GET.get('start_date')).strftime('%Y-%m-%d')
        komp_tag_type = VariantTagType.objects.get(guid='VTT_share_with_komp')

        variants = VariantTag.objects.filter(variant_tag_type=komp_tag_type, created_date__gt=start_date)
        rows = [{
            'project': v.saved_variant.project.name,
            'family_id': v.saved_variant.family.family_id,
            'timestamp': v.created_date.strftime('%Y-%m-%d %H:%M:%S'),
            'genes': ', '.join(json.loads(v.saved_variant.saved_variant_json)['extras']['gene_names'].values()),
            'chrom': get_chrom_pos(v.saved_variant.xpos)[0],
            'pos': get_chrom_pos(v.saved_variant.xpos)[1],
            'ref': v.saved_variant.ref,
            'alt': v.saved_variant.alt,
        } for v in variants]

        return export_table('komp_tags', HEADERS, rows, 'xls')

    return render(request, "staff/komp_export.html")
