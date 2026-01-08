import requests
from django.utils import timezone
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from urllib3.exceptions import MaxRetryError

from seqr.models import LocusList as SeqrLocusList, LocusListGene as SeqrLocusListGene
from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)

REQUEST_TIMEOUT_S = 300

class TooManyRequestsError(Exception):
    pass


def _extract_ensembl_id_from_json(raw_gene_json):
    ensembl_genes_json = raw_gene_json.get('gene_data', {}).get('ensembl_genes')
    if ensembl_genes_json and isinstance(ensembl_genes_json, dict):
        return ensembl_genes_json \
            .get('GRch38', {}) \
            .get('90', {}) \
            .get('ensembl_id')
    else:
        return None


def get_valid_panel_genes(panel_app_id, panel, panels_api_url, genes_by_panel_id, gene_ids_to_gene):
    if len(genes_by_panel_id[panel_app_id]) != panel['stats']['number_of_genes']:
        panel_genes_url = f'{panels_api_url}/{panel_app_id}/genes'
        _get_all_genes(panel_app_id, panel_genes_url, genes_by_panel_id)

    all_genes_for_panel = genes_by_panel_id[panel_app_id]
    if not all_genes_for_panel:
        return {}

    panel_genes_by_id = {
        _extract_ensembl_id_from_json(gene): gene for gene in all_genes_for_panel
        if _extract_ensembl_id_from_json(gene)
    }
    valid_panel_genes = {
        gene_id: panel_gene for gene_id, panel_gene in panel_genes_by_id.items() if gene_id in gene_ids_to_gene
    }
    if len(panel_genes_by_id) > len(valid_panel_genes):
        invalid_items = sorted(set(panel_genes_by_id.keys()) - set(valid_panel_genes.keys()))
        logger.warning('Genes found in panel {} but not in reference data, ignoring genes {}'
                       .format(panel_app_id, invalid_items), user=None)

    return valid_panel_genes


def update_locus_list_genes_bulk(seqr_locus_list, panel_genes_by_id):
    logger.info('Bulk updating genes for list {}'.format(seqr_locus_list), user=None)
    SeqrLocusList.bulk_delete(user=None, queryset=seqr_locus_list.locuslistgene_set.all())
    current_time = timezone.now()

    locuslistgenes = {
        gene_id: SeqrLocusListGene(
            locus_list=seqr_locus_list,
            gene_id=gene_id,
            created_date=current_time,
            guid='LL%05d_%s' % (seqr_locus_list.id, gene_id)
        ) for gene_id in panel_genes_by_id
    }
    created_locuslistgenes = SeqrLocusListGene.objects.bulk_create(locuslistgenes.values(), batch_size=10000)
    created_locuslistgenes_by_id = {lg.gene_id: lg for lg in created_locuslistgenes}

    return [
        _parse_pa_locus_list_gene(created_locuslistgenes_by_id[gene_id], panel_gene)
        for gene_id, panel_gene in panel_genes_by_id.items()
    ]


def _parse_pa_locus_list_gene(seqr_locus_list_gene, panel_gene_json):
    del panel_gene_json['panel']  # No need to keep panel info
    del panel_gene_json['gene_data']  # No need to keep gene info as Seqr already maintain info
    return dict(
        seqr_locus_list_gene=seqr_locus_list_gene,
        confidence_level=panel_gene_json.get('confidence_level'),
        biotype=panel_gene_json.get('biotype') or None,
        penetrance=panel_gene_json.get('penetrance') or None,
        mode_of_pathogenicity=panel_gene_json.get('mode_of_pathogenicity') or None,
        mode_of_inheritance=panel_gene_json.get('mode_of_inheritance') or None,
    )


def get_updated_panels(panels_url, existing_list_versions):
    resp = requests.get(panels_url, timeout=REQUEST_TIMEOUT_S)
    resp_json = resp.json()
    for result in resp_json.get('results', []):
        current_version = existing_list_versions.get(result.get('id'))
        if result.get('version') != current_version and result.get('stats', {}).get('number_of_genes', 0) > 0:
            yield result

    next_page = resp_json.get('next', None)
    if next_page:
        yield from get_updated_panels(next_page, existing_list_versions)


def _get_all_genes(panel_app_id: int, genes_url: str, results_by_panel_id: dict):
    @retry(
        retry=retry_if_exception_type((MaxRetryError, TooManyRequestsError)),
        wait=wait_exponential(multiplier=1, min=4, max=20),
        stop=stop_after_attempt(5),
    )
    def _get(url):
        resp = requests.get(url, timeout=REQUEST_TIMEOUT_S)
        if resp.status_code == 429:
            raise TooManyRequestsError()
        return resp.json()

    resp_json = _get(genes_url)
    for result in resp_json.get('results', []):
        panel_id = result.get('panel', {}).get('id')
        if panel_id:
            results_by_panel_id[panel_id].append(result)
        if panel_app_id != panel_id:
            results_by_panel_id[panel_app_id].append(result)

    next_page = resp_json.get('next', None)
    if next_page is None:
        return results_by_panel_id
    else:
        return _get_all_genes(panel_app_id, next_page, results_by_panel_id)


def panel_description(panel_app_id, panel, source):
    disease_groups = [d for d in [panel['disease_group'], panel['disease_sub_group']] if d]

    return 'PanelApp_{source}_{panel_app_id}_{version}{disease_groups}'.format(
        panel_app_id=panel_app_id,
        source=source,
        version=panel['version'],
        disease_groups='_{}'.format(';'.join(disease_groups)) if disease_groups else '',
    )
