from collections import defaultdict
import collections
import json
import logging
import re
import requests
import tempfile
import openpyxl as xl

from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import prefetch_related_objects
from django.utils import timezone

from seqr.utils.gene_utils import get_genes
from seqr.utils.xpos_utils import get_chrom_pos

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import variant_main_transcript, variant_details
from seqr.views.utils.json_utils import create_json_response, _to_title_case
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals, get_json_for_saved_variant
from reference_data.models import HPO_CATEGORY_NAMES
from seqr.models import Project, Family, VariantTag, VariantTagType, Sample, SavedVariant
from dateutil import relativedelta as rdelta
from django.db.models import Q, Prefetch
from django.shortcuts import render
from settings import LOGIN_URL, SEQR_ID_TO_MME_ID_MAP
from seqr.views.utils.orm_to_json_utils import _get_json_for_project

logger = logging.getLogger(__name__)


ZYGOSITY_MAP = {
    -1: 'no call',
    0: 'homozygous reference',
    1: 'heterozygous',
    2: 'homozygous alt',
}


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def anvil_export(request, project_guid):
    if project_guid == 'all':
        project_guid = None

    if project_guid:
        projects_by_guid = {project_guid: Project.objects.get(guid=project_guid)}
    else:
        projects_by_guid = {p.guid: p for p in Project.objects.filter(projectcategory__name__iexact='anvil')}

    families = _get_over_year_loaded_project_families(projects_by_guid.values())
    prefetch_related_objects(families, 'individual_set')

    saved_variants_by_family = _get_saved_variants_by_family(projects_by_guid.values(), request.user)

    individuals = set()
    for family in families:
        individuals.update(family.individual_set.all())
    rows = _get_json_for_individuals(list(individuals), project_guid=project_guid, family_fields=['family_id', 'coded_phenotype'])

    for row in rows:
        row['Project ID'] = projects_by_guid[row['projectGuid']].name

        saved_variants = saved_variants_by_family[row['familyGuid']]
        row['numSavedVariants'] = len(saved_variants)
        if saved_variants:
            main_gene_ids = {variant['mainTranscript']['geneId'] for variant in saved_variants}
            if len(main_gene_ids) > 1:
                # This occurs in compound hets where some hits have a primary transcripts in different genes
                for gene_id in main_gene_ids:
                    if all(gene_id in variant['transcripts'] for variant in saved_variants):
                        row['geneId'] = gene_id
            else:
                row['geneId'] = main_gene_ids.pop()

            for i, variant in enumerate(saved_variants):
                genotype = variant['genotypes'].get(row['individualGuid'], {})
                variant_fields = {
                    'Zygosity': ZYGOSITY_MAP.get(genotype.get('numAlt')),
                    'Chrom': variant['chrom'],
                    'Pos': variant['pos'],
                    'Ref': variant['ref'],
                    'Alt': variant['alt'],
                    'hgvsc': variant['mainTranscript']['hgvsc'],
                    'hgvsp': variant['mainTranscript']['hgvsp'],
                    'Transcript': variant['mainTranscript']['transcriptId'],
                }
                row.update({'{} - {}'.format(k, i + 1): v for k, v in variant_fields.items()})

    genes_by_id = get_genes({row['geneId'] for row in rows if row.get('geneId')})
    for row in rows:
        if row.get('geneId') and genes_by_id.get(row['geneId']):
            row['Causal gene'] = genes_by_id[row['geneId']]['geneSymbol']

    #
    return create_json_response({'anvilRows': rows})


def _get_over_year_loaded_project_families(projects):
    max_loaded_date = datetime.now() - timedelta(days=365)
    loaded_samples = Sample.objects.filter(
        individual__family__project__in=projects,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_status=Sample.SAMPLE_STATUS_LOADED,
        loaded_date__isnull=False,
        loaded_date__lte=max_loaded_date,
    ).select_related('individual__family__project').order_by('loaded_date')
    
    return list({sample.individual.family for sample in loaded_samples})


def _get_saved_variants_by_family(projects, user):
    tag_type = VariantTagType.objects.get(name='Known gene for phenotype')

    project_saved_variants = SavedVariant.objects.select_related('family').filter(
        project__in=projects,
        varianttag__variant_tag_type=tag_type,
    )

    saved_variants_by_family = collections.defaultdict(list)
    for saved_variant in project_saved_variants:
        variant = get_json_for_saved_variant(saved_variant)
        variant_json = json.loads(saved_variant.saved_variant_json or '{}')
        variant.update(variant_details(variant_json, saved_variant.project, user, genotypes_by_individual_guid=True))

        saved_variants_by_family[saved_variant.family.guid].append(variant)

    return saved_variants_by_family
