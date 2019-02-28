import collections
import json
import logging

from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import prefetch_related_objects

from seqr.utils.gene_utils import get_genes
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.variant_utils import variant_details
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals, get_json_for_saved_variants
from seqr.models import Project, VariantTagType, Sample, SavedVariant, Individual

logger = logging.getLogger(__name__)


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

    # Handle compound het genes
    compound_het_gene_id_by_family = {}
    for family_guid, saved_variants in saved_variants_by_family.items():
        if len(saved_variants) > 1:
            potential_compound_het_variants = [
                variant for variant in saved_variants if all(gen['numAlt'] < 2 for gen in variant['genotypes'].values())
            ]
            main_gene_ids = {variant['mainTranscript']['geneId'] for variant in potential_compound_het_variants}
            if len(main_gene_ids) > 1:
                # This occurs in compound hets where some hits have a primary transcripts in different genes
                for gene_id in main_gene_ids:
                    if all(gene_id in variant['transcripts'] for variant in potential_compound_het_variants):
                        compound_het_gene_id_by_family[family_guid] = gene_id

    individuals = set()
    for family in families:
        individuals.update(family.individual_set.all())
    rows = _get_json_for_individuals(list(individuals), project_guid=project_guid, family_fields=['family_id', 'coded_phenotype'])

    gene_ids = set()
    for row in rows:
        row['Project ID'] = projects_by_guid[row['projectGuid']].name

        saved_variants = saved_variants_by_family[row['familyGuid']]
        row['numSavedVariants'] = len(saved_variants)
        for i, variant in enumerate(saved_variants):
            genotype = variant['genotypes'].get(row['individualGuid'], {})
            if genotype.get('numAlt', -1) > 0:
                gene_id = compound_het_gene_id_by_family.get(row['familyGuid']) or variant['mainTranscript']['geneId']
                gene_ids.add(gene_id)
                variant_fields = {
                    'Zygosity': 'heterozygous' if genotype['numAlt'] == 1 else 'homozygous',
                    'Chrom': variant['chrom'],
                    'Pos': variant['pos'],
                    'Ref': variant['ref'],
                    'Alt': variant['alt'],
                    'hgvsc': variant['mainTranscript']['hgvsc'],
                    'hgvsp': variant['mainTranscript']['hgvsp'],
                    'Transcript': variant['mainTranscript']['transcriptId'],
                    'geneId': gene_id,
                }
                row.update({'{} - {}'.format(k, i + 1): v for k, v in variant_fields.items()})

    genes_by_id = get_genes(gene_ids)
    for row in rows:
        for key, gene_id in row.items():
            if key.startswith('geneId') and genes_by_id.get(gene_id):
                row[key.replace('geneId', 'Gene')] = genes_by_id[gene_id]['geneSymbol']

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

    project_saved_variants = SavedVariant.objects.select_related('family', 'project').filter(
        project__in=projects,
        varianttag__variant_tag_type=tag_type,
    )

    individuals = Individual.objects.filter(family__project__in=projects).only('guid', 'individual_id')
    individual_guids_by_id = {i.individual_id: i.guid for i in individuals}
    project_saved_variants_json = get_json_for_saved_variants(
        project_saved_variants, add_tags=True, add_details=True, user=user, individual_guids_by_id=individual_guids_by_id)

    saved_variants_by_family = collections.defaultdict(list)
    for variant in project_saved_variants_json:
        saved_variants_by_family[variant['familyGuid']].append(variant)

    return saved_variants_by_family
