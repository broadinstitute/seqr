import os
import itertools
import logging
import pymongo
from xbrowse import genomeloc
from xbrowse.reference.clinvar import parse_clinvar_vcf

logger = logging.getLogger(__name__)

class Reference(object):
    """
    Reference is a workhorse - it provides an API for looking up any information about the human genome
    Requires an ensembl db connection, an ensembl REST API address, and a mongo db
    """

    def __init__(self, settings_module):

        # TODO: should we store settings module or just parse all the values here?
        self.settings_module = settings_module
        from seqr.utils import gene_utils
        self.gene_utils = gene_utils

        self._db = pymongo.MongoClient(host=os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost'))[settings_module.db_name]

    def load(self):
        raise Exception('Attempting to load deprecated MongoDB reference data')

    def _load_genes(self):
        raise Exception('Attempting to load deprecated MongoDB reference data')

    def _load_clinvar(self, clinvar_vcf_path=None):
        self._db.drop_collection('clinvar')
        self._db.clinvar.ensure_index([('xpos', 1), ('ref', 1), ('alt', 1)])

        iterator = parse_clinvar_vcf(clinvar_vcf_path=clinvar_vcf_path)
        while True:
            chunk = list(itertools.islice(iterator, 0, 1000))
            if len(chunk) == 0:
                break
            try:
                self._db.clinvar.bulk_write(list(map(pymongo.InsertOne, chunk)))
            except pymongo.bulk.BulkWriteError as bwe:
                # If ref/alt are too long to index, drop the variant. Otherwise, raise an error
                fatal_errors = [err['errmsg'] for err in bwe.details['writeErrors'] if 'key too large to index' not in err['errmsg']]
                if fatal_errors:
                    raise Exception(fatal_errors)

    def _load_gtex_data(self):
        raise Exception('Attempting to load deprecated MongoDB reference data')

    def update_phenotype_info(self, gene_id, phenotype_info):
        raise Exception('Attempting to load deprecated MongoDB reference data')

    def _load_tags(self):
        raise Exception('Attempting to load deprecated MongoDB reference data')

    def _reset_reference_cache(self):
        raise Exception('Attempting to load deprecated MongoDB reference data')


    #
    # Gene lookups
    #

    def get_all_gene_ids(self):
        return self.gene_utils.get_filtered_gene_ids({})

    def get_all_exon_ids(self):
        raise NotImplementedError

    def get_gene_bounds(self, gene_id):
        gene = self.gene_utils.get_genes([gene_id]).get(gene_id)
        if not gene:
            return (None, None, None)
        build = 'Grch37' if gene['chromGrch37'] else 'Grch38'
        chrom = gene['chrom{}'.format(build)]
        start = gene['start{}'.format(build)]
        end = gene['end{}'.format(build)]
        return (genomeloc.get_xpos(chrom, start), genomeloc.get_xpos(chrom, end))

    def get_gene_symbol(self, gene_id):
        return self.gene_utils.get_genes([gene_id]).get(gene_id, {}).get('geneSymbol')

    def get_gene_id_from_symbol(self, symbol, use_latest_gene_if_multiple=False):
        gene_ids = self.gene_utils.get_gene_ids_for_gene_symbols([symbol]).get(symbol, [])
        if len(gene_ids) == 1 or (use_latest_gene_if_multiple and gene_ids):
            return gene_ids[0]
        return None

    def is_valid_gene_id(self, gene_id):
        return bool(self.get_gene_symbol(gene_id))

    def get_gene(self, gene_id):
        """
        Returns basic information about the gene:
        - structure, ie. exons and transcripts
        - statistics
        """

        return self.get_genes([gene_id]).get(gene_id)

    def get_genes(self, gene_id_list):
        """
        get_gene for a set of genes
        faster because only one db call
        TODO: but haven't optimized yet
        return map of gene_id -> gene
        gene is None if gene_id invalid
        """
        genes = {gene_id: {
            'gene_id': gene['geneId'],
            'symbol': gene['geneSymbol'],
            'chrom': gene['chromGrch37'],
            'start': gene['startGrch37'],
            'stop': gene['endGrch37'],
            'gene_type': gene['gencodeGeneType'],
            'coding_size': gene['codingRegionSizeGrch37'],
            'function_desc': gene['functionDesc'],
            'disease_desc': gene['diseaseDesc'],
            'tags': {
                'missense_constraint': gene['constraints'].get('misZ'),
                'missense_constraint_rank': [gene['constraints'].get('misZRank'), gene['constraints'].get('totalGenes')],
                'lof_constraint': gene['constraints'].get('pli'),
                'lof_constraint_rank': [gene['constraints'].get('pliRank'), gene['constraints'].get('totalGenes')],
            },
            'phenotype_info': {
                'has_mendelian_phenotype': len(gene['omimPhenotypes']) > 0,
                'mim_id': gene['omimPhenotypes'][0]['mimNumber'] if len(gene['omimPhenotypes']) else None,
                'mim_phenotypes': [{
                    'mim_id': phenotype['phenotypeMimNumber'],
                    'description': phenotype['phenotypeDescription']
                } for phenotype in gene['omimPhenotypes']],
                'orphanet_phenotypes': [],
            },
        } for gene_id, gene in self.gene_utils.get_genes(gene_id_list, add_dbnsfp=True, add_omim=True, add_constraints=True).items()}
        return {gene_id: genes.get(gene_id) for gene_id in gene_id_list}

    def get_genes_in_region(self, chrom, region_start, region_end):
        """
        List of gene_ids of genes that overlap this region
        Inclusive
        """
        return self.gene_utils.get_filtered_gene_ids({
            'chrom_grch37': chrom,
            'start_grch37__gte': region_start,
            'end_grch37__lte': region_end
        })

    def get_gene_summary(self, gene_id):
        gene = self.gene_utils.get_genes([gene_id], add_constraints=True).get(gene_id)

        return {
            'gene_id': gene['geneId'],
            'symbol': gene['geneSymbol'],
            'coding_size': gene['codingRegionSizeGrch37'],
            'tags': {
                'missense_constraint': gene['constraints'].get('misZ'),
                'missense_constraint_rank': [gene['constraints'].get('misZRank'),
                                             gene['constraints'].get('totalGenes')],
                'lof_constraint': gene['constraints'].get('pli'),
                'lof_constraint_rank': [gene['constraints'].get('pliRank'), gene['constraints'].get('totalGenes')],
            },
        } if gene else {}

    def get_gene_symbols(self):
        """
        Map of gene_id -> gene symbol for all genes
        """
        return {gene_id: gene['geneSymbol'] for gene_id, gene in self.gene_utils.get_genes(None).values()}

    def get_ordered_exons(self):
        """
        Get a list of all exons in genomic order
        Returns a list of (exon_id, xstart, xstop) tuples
        """
        raise NotImplementedError

    def get_tissue_expression_display_values(self, gene_id):
        """
        Get the data for displaying tissue expression plot

        This is a list of ~60 expression values for each tissue, so it's pretty big, hence not part of get_gene()
        """
        return self.gene_utils.get_genes([gene_id], add_expression=True).get(gene_id, {}).get('expression')

    def get_gene_structure(self, gene_id):
        raise NotImplementedError

    def get_all_coding_regions_sorted(self):
        """
        Return a list of CodingRegions, in order
        "order" implies that cdrs for a gene might not be consecutive
        """
        raise NotImplementedError

    def get_clinvar_info(self, xpos, ref, alt):
        doc = self._db.clinvar.find_one({'xpos': xpos, 'ref': ref, 'alt': alt})
        if doc is None:
            return None, ''
        else:
            return doc['variant_id'], doc['clinsig']
