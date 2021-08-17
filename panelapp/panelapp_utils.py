import requests
from django.db import transaction
from django.utils import timezone

from panelapp.models import PaLocusList, PaLocusListGene
from seqr.models import LocusList as SeqrLocusList, LocusListGene as SeqrLocusListGene
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.json_to_orm_utils import update_model_from_json, create_model_from_json
from settings import PANEL_APP_API_URL

logger = SeqrLogger(__name__)


def import_all_panels(user):
    def _extract_ensembl_id_from_json(raw_gene_json):
        return raw_gene_json.get('gene_data', {}).get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get(
            'ensembl_id')

    panels_url = '{}/panels/?page=1'.format(PANEL_APP_API_URL)

    all_panels = _get_all_panels(panels_url, [])

    for panel in all_panels:
        with transaction.atomic():
            pa_locus_list = _create_or_update_locus_list_from_panel(user, panel)
            panel_app_id = panel.get('id')
            panel_genes_url = '{}/panels/{}/genes/?page=1'.format(PANEL_APP_API_URL, panel_app_id)
            all_genes_for_panel = _get_all_genes_for_panel(panel_genes_url, [])
            panel_genes_by_id = {_extract_ensembl_id_from_json(gene): gene for gene in all_genes_for_panel
                                 if _extract_ensembl_id_from_json(gene)}
            raw_ensbl_38_gene_ids_csv = ','.join(panel_genes_by_id.keys())
            genes_by_id, _, invalid_items = parse_locus_list_items({'rawItems': raw_ensbl_38_gene_ids_csv})
            if len(invalid_items) > 0:
                logger.warning('Genes found in panel {} but not in reference data, ignoring genes {}'
                               .format(panel_app_id, invalid_items), user)
            _update_locus_list_genes_bulk(pa_locus_list, genes_by_id, panel_genes_by_id, user)


def _update_locus_list_genes_bulk(pa_locus_list, genes_by_id, panel_genes_by_id, user):
    seqr_locus_list = pa_locus_list.seqr_locus_list
    logger.info('Bulk updating genes for list {}'.format(seqr_locus_list), user)
    SeqrLocusList.bulk_delete(user, queryset=seqr_locus_list.locuslistgene_set.all())
    current_time = timezone.now()

    locuslistgenes = {
        gene_id: SeqrLocusListGene(
            locus_list=seqr_locus_list,
            gene_id=gene_id,
            created_by=user,
            created_date=current_time,
            guid='LL%05d_%s' % (seqr_locus_list.id, gene_id)
        ) for gene_id in genes_by_id.keys()
    }
    created_locuslistgenes = SeqrLocusListGene.objects.bulk_create(locuslistgenes.values(), batch_size=10000)
    created_locuslistgenes_by_id = {lg.gene_id: lg for lg in created_locuslistgenes}

    palocuslistgenes = {
        gene_id: _create_pa_locus_list_gene(created_locuslistgenes_by_id[gene_id], panel_genes_by_id[gene_id])
        for gene_id in genes_by_id.keys()
    }
    PaLocusListGene.objects.bulk_create(palocuslistgenes.values(), batch_size=10000)


def _create_pa_locus_list_gene(seqr_locus_list_gene, panel_gene_json):
    del panel_gene_json['panel']  # No need to keep panel info
    del panel_gene_json['gene_data']  # No need to keep gene info as Seqr already maintain info
    result = PaLocusListGene(
        seqr_locus_list_gene=seqr_locus_list_gene,
        confidence_level=panel_gene_json.get('confidence_level'),
        biotype=panel_gene_json.get('biotype') or None,
        penetrance=panel_gene_json.get('penetrance') or None,
        mode_of_pathogenicity=panel_gene_json.get('mode_of_pathogenicity') or None,
        mode_of_inheritance=panel_gene_json.get('mode_of_inheritance') or None,
        raw_data=panel_gene_json,
    )

    return result


def _get_all_panels(panels_url, all_results):
    resp = requests.get(panels_url)
    resp_json = resp.json()
    curr_page_results = [r for r in resp_json.get('results', []) if r.get('stats', {}).get('number_of_genes', 0) > 0]
    all_results += curr_page_results

    next_page = resp_json.get('next', None)
    if next_page is None:
        return all_results
    else:
        return _get_all_panels(next_page, all_results)


def _get_all_genes_for_panel(panel_genes_url, all_results):
    resp = requests.get(panel_genes_url)
    resp_json = resp.json()
    all_results += resp_json.get('results', [])

    next_page = resp_json.get('next', None)
    if next_page is None:
        return all_results
    else:
        return _get_all_genes_for_panel(next_page, all_results)


def _create_or_update_locus_list_from_panel(user, panel_json):
    panel_app_id = panel_json.get('id')
    existing = _safe_get_locus_list(panel_app_id)

    if existing:
        update_model_from_json(existing.seqr_locus_list, {
            'name': panel_json['name']
        }, user)
        update_model_from_json(existing, {
            'disease_group': panel_json.get('disease_group') or None,
            'disease_sub_group': panel_json.get('disease_sub_group') or None,
            'status': panel_json.get('status') or None,
            'version': panel_json.get('version') or None,
            'version_created': panel_json.get('version_created') or None,
            'raw_data': panel_json,
        }, user)

        return existing
    else:
        seqr_locus_list = create_model_from_json(SeqrLocusList, {
            'name': panel_json['name'],
            'description': None,
            'is_public': True,
        }, user)
        locus_list = PaLocusList.objects.create(seqr_locus_list=seqr_locus_list, panel_app_id=panel_app_id)
        update_model_from_json(locus_list, {
            'disease_group': panel_json.get('disease_group'),
            'disease_sub_group': panel_json.get('disease_sub_group'),
            'status': panel_json.get('status'),
            'version': panel_json.get('version'),
            'version_created': panel_json.get('version_created'),
            'raw_data': panel_json,
        }, user)

        return locus_list


def _safe_get_locus_list(panel_app_id):
    result = PaLocusList.objects.filter(panel_app_id=panel_app_id)

    return result.first() if result else None
