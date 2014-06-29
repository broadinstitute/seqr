import gzip

import requests
import pymongo
import MySQLdb as mdb
import pandas

from xbrowse import genomeloc
from xbrowse.parsers.gtf import get_data_from_gencode_gtf
import ensembl_parsing_utils
from .utils import get_coding_regions_for_gene
import gene_expression


class Reference(object):
    """
    Reference is a workhorse - it provides an API for looking up any information about the human genome
    Requires an ensembl db connection, an ensembl REST API address, and a mongo db
    """

    def __init__(self, settings_module):

        # TODO: should we store settings module or just parse all the values here?
        self.settings_module = settings_module

        self.has_phenotype_data = settings_module.has_phenotype_data

        self._db = pymongo.Connection()[settings_module.db_name]
        self.ensembl_rest_proxy = EnsemblRESTProxy(
            host=settings_module.ensembl_rest_host,
            port=settings_module.ensembl_rest_port
        )
        self.ensembl_db_proxy = EnsemblDBProxy(
            host=settings_module.ensembl_db_host,
            port=settings_module.ensembl_db_port,
            user=settings_module.ensembl_db_user,
        )

        self._gene_positions = None
        self._ordered_genes = None
        self._gene_symbols = None
        self._gene_symbols_r = None
        self._gene_ids = None
        self._gene_summaries = None

    def load(self):
        """
        Load up reference from data in settings module
        """
        self._db.drop_collection('genes')
        self._db.drop_collection('transcripts')
        self._db.drop_collection('exons')
        self._db.drop_collection('tissue_expression')
        self._ensure_indices()

        for datatype, obj in get_data_from_gencode_gtf(gzip.open(self.settings_module.gencode_gtf_file)):

            if datatype == 'gene':
                gene_id = obj['gene_id']
                obj['symbol'] = obj['gene_name']

                obj['tags'] = {}

                # TODO
                #obj['coding_size'] = loading_utils.get_coding_size_from_gene_structure(obj)
                obj['coding_size'] = 0

                self._db.genes.insert(obj)

            if datatype == 'transcript':
                transcript_id = obj['transcript_id']
                obj['tags'] = {}
                self._db.transcripts.insert(obj)

        self._load_gtex_data()
        self._load_phenotype_data()
        self._load_tags()
        self._reset_reference_cache()

    def _load_gtex_data(self):

        print "Loading tissue-specific expression values"
        for gene_id, expression_array in gene_expression.get_tissue_expression_values_by_gene(
            self.settings_module.gtex_expression_file,
            self.settings_module.gtex_samples_file
        ):
            self._db.tissue_expression.insert({
                'gene_id': gene_id,
                'expression_display_values': expression_array
            })

    def _load_phenotype_data(self):

        print "Loading phenotype data"
        gene_ids = self.get_all_gene_ids()
        for gene_id in gene_ids:
            if self.has_phenotype_data:
                phenotype_info = self.ensembl_rest_proxy.get_phenotype_info(gene_id)
            else:
                phenotype_info = {
                    'has_mendelian_phenotype': True,
                    'mim_id': "180901",
                    'mim_phenotypes': [],
                    'orphanet_phenotypes': [],
                }
            self._db.genes.update(
                {'gene_id': gene_id},
                {'$set': {'phenotype_info': phenotype_info}}
            )

    def _load_tags(self):

        for gene_tag in self.settings_module.gene_tags:
            if gene_tag.get('data_type') == 'bool' and gene_tag.get('storage_type') == 'gene_list_file':
                tag_id = gene_tag.get('slug')
                # first set all genes to false
                self._db.genes.update({}, {'$set': {'tags.'+tag_id: False}}, multi=True)
                gene_ids = [line.strip() for line in open(gene_tag.get('file_path')).readlines()]
                for gene_id in gene_ids:
                    self._db.genes.update({'gene_id': gene_id}, {'$set': {'tags.'+tag_id: True}})

            elif gene_tag.get('data_type') == 'test_statistic':
                tag_id = gene_tag.get('slug')
                # first set all to None
                self._db.genes.update({}, {'$set': {'tags.'+tag_id: None}}, multi=True)
                scores = pandas.DataFrame.from_csv(gene_tag['file_path'])
                ranks = scores.rank(ascending=False)
                for gene_id, score in scores.itertuples():
                    self._db.genes.update({'gene_id': gene_id}, {'$set': {'tags.'+tag_id: score}})
                for gene_id, rank in ranks.itertuples():
                    self._db.genes.update({'gene_id': gene_id}, {'$set': {'tags.'+tag_id+'_rank': [int(rank), len(ranks)]}})

            else:
                raise Exception("Could not parse gene tag: {}".format(gene_tag))

    def _reset_reference_cache(self):
        self._db.reference_cache.remove()
        self._db.reference_cache.ensure_index('key')

        genes = []
        gene_positions = {}
        gene_symbols = {}
        gene_symbols_r = {}
        for gene in self._db.genes.find({}, {'gene_id': 1, 'xstart': 1, 'xstop': 1, 'symbol': 1}):
            genes.append(gene)
            gene_positions[gene['gene_id']] = (gene['xstart'], gene['xstop'])
            gene_symbols[gene['gene_id']] = gene['symbol']
            gene_symbols_r[gene['symbol'].lower().replace('.', '_')] = gene['gene_id']

        ordered_genes = sorted(
            [(gene['gene_id'], gene['xstart'], gene['xstop']) for gene in genes],
            key=lambda x: (x[1], x[2])
        )

        self._db.reference_cache.insert({
            'key': 'gene_positions',
            'val': gene_positions,
        })

        self._db.reference_cache.insert({
            'key': 'ordered_genes',
            'val': ordered_genes,
        })

        self._db.reference_cache.insert({
            'key': 'gene_symbols',
            'val': gene_symbols,
        })

        self._db.reference_cache.insert({
            'key': 'gene_symbols_r',
            'val': gene_symbols_r,
        })

        gene_summaries = {}
        mendelian_phenotype_genes = []
        for gene in self._db.genes.find():
            gene_summary = {
                'gene_id': gene['gene_id'],
                'symbol': gene['symbol'],
                'coding_size': gene['coding_size'],
            }
            gene_summary.update(gene['tags'])
            gene_summaries[gene['gene_id']] = gene_summary

            if gene['phenotype_info']['has_mendelian_phenotype'] is True:
                mendelian_phenotype_genes.append(gene['gene_id'])

        self._db.reference_cache.insert({
            'key': 'gene_summaries',
            'val': gene_summaries,
        })

        self._db.reference_cache.insert({
            'key': 'mendelian_phenotype_genes',
            'val': mendelian_phenotype_genes,
        })

    def _get_reference_cache(self, key): 
        doc = self._db.reference_cache.find_one({'key': key})
        if doc: 
            return doc['val']

    def _ensure_cache(self, key):
        varname = '_' + key
        if getattr(self, varname) is None:
            setattr(self, varname, self._get_reference_cache(key))

    def _ensure_indices(self):
        self._db.genes.ensure_index('gene_id')

        self._db.transcripts.ensure_index('transcript_id')
        self._db.transcripts.ensure_index('gene_id')

        self._db.exons.ensure_index('exon_id')
        self._db.exons.ensure_index('gene_id')

        self._db.expression.ensure_index('gene_id')

    #
    # Gene lookups
    #

    def get_all_gene_ids(self):
        return [doc['gene_id'] for doc in self._db.genes.find(fields={'gene_id': True})]

    def get_all_exon_ids(self):
        raise NotImplementedError

    def get_ordered_genes(self):
        if self._ordered_genes is None:
            self._ordered_genes = self._get_reference_cache('ordered_genes')
        return self._ordered_genes

    def get_gene_bounds(self, gene_id):
        if self._gene_positions is None:
            self._gene_positions = self._get_reference_cache('gene_positions')
        return self._gene_positions[gene_id]

    def get_gene_symbol(self, gene_id):
        if self._gene_symbols is None:
            self._gene_symbols = self._get_reference_cache('gene_symbols')
        return self._gene_symbols.get(gene_id)

    def get_gene_id_from_symbol(self, symbol):
        if self._gene_symbols_r is None:
            self._gene_symbols_r = self._get_reference_cache('gene_symbols_r')
        return self._gene_symbols_r.get(symbol.lower().replace('.', '_'))

    def is_valid_gene_id(self, gene_id):
        self._ensure_cache('gene_symbols')
        return gene_id in self._gene_symbols

    def get_gene(self, gene_id):
        """
        Returns basic information about the gene:
        - structure, ie. exons and transcripts
        - statistics
        """
        return self._db.genes.find_one({'gene_id': gene_id}, fields={'_id': False})

    def get_genes(self, gene_id_list):
        """
        get_gene for a set of genes
        faster because only one db call
        TODO: but haven't optimized yet
        return map of gene_id -> gene
        gene is None if gene_id invalid
        """
        return {gene_id: self.get_gene(gene_id) for gene_id in gene_id_list}

    def get_genes_in_region(self, region_start, region_end):
        """
        List of gene_ids of genes that overlap this region
        Inclusive
        """
        if not hasattr(self, '_genetree'):
            import banyan
            self._genetree = banyan.SortedSet([(t[1], t[2]) for t in self.get_ordered_genes()], updator=banyan.OverlappingIntervalsUpdator)
            self._geneposmap = {(t[1], t[2]): t[0] for t in self.get_ordered_genes()}
        ret = []
        for item in self._genetree.overlap((region_start, region_end)):
            ret.append(self._geneposmap[item])
        return ret
        # return [gene['gene_id'] for gene in self._db.genes.find({
        #     'xstart': {'$lte': region_end},
        #     'xstop': {'$gte': region_start},
        # })]


    def get_gene_summary(self, gene_id):
        self._ensure_cache('gene_summaries')
        return self._gene_summaries[gene_id]

    def get_gene_symbols(self):
        """
        Map of gene_id -> gene symbol for all genes
        """
        if self._gene_symbols is None:
            self._gene_symbols = self._get_reference_cache('gene_symbols')
        return self._gene_symbols

    def get_ordered_exons(self):
        """
        Get a list of all exons in genomic order
        Returns a list of (exon_id, xstart, xstop) tuples
        """
        exon_tuples = self.ensembl_db_proxy.get_all_exons()
        return sorted(exon_tuples, key=lambda x: (x[1], x[2]))

    def get_tissue_expression_display_values(self, gene_id):
        """
        Get the data for displaying tissue expression plot
        This is a list of ~60 expression values for each tissue, so it's pretty big, hence not part of get_gene()
        """
        doc = self._db.tissue_expression.find_one({'gene_id': gene_id})
        if doc is None:
            return None
        return doc['expression_display_values']

    def get_all_coding_regions_sorted(self):
        """
        Return a list of CodingRegions, in order
        "order" implies that cdrs for a gene might not be consecutive
        """
        cdr_list = []
        for gene in self._db.genes.find():
            flattened_cdrs = get_coding_regions_for_gene(gene)
            cdr_list.extend(flattened_cdrs)
        return sorted(cdr_list, key=lambda x: (x.xstart, x.xstop))



class EnsemblRESTProxy(object):
    """
    Wrapper over an Ensembl REST server that a Reference uses as its underlying data source
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def _get_rest_url(self):
        return "http://%s:%d" % (self.host, self.port)

    def get_phenotype_info(self, gene_id):
        """
        Here's what returns for RYR1:
        {
            'has_mendelian_phenotype': true,
            'mim_id': "180901",
            'mim_phenotypes': [
                {'mim_id': '117000', 'description': 'CENTRAL CORE DISEASE OF MUSCLE'},
                ...
            ],
            'orphanet_phenotypes': [
                {'orphanet_id': '178145', 'description': 'Moderate multiminicore disease with hand involvement'},
                ...
            ]
        }
        """

        phenotype_info = {
            'mim_id': None,
            'mim_phenotypes': [],
            'orphanet_phenotypes': []
        }

        url = self._get_rest_url() + '/xrefs/id/%s' % gene_id
        params = {'content-type': 'application/json'}
        xrefs_json = requests.get(url, params=params).json()

        for item in xrefs_json:

            if item['dbname'] == 'MIM_GENE':
                phenotype_info['mim_id'] = item['primary_id']

            elif item['dbname'] == 'MIM_MORBID':
                phenotype_info['mim_phenotypes'].append({
                    'mim_id': item['primary_id'],
                    'description': item['description']
                })

            elif item['dbname'] == 'Orphanet':
                phenotype_info['orphanet_phenotypes'].append({
                    'orphanet_id': item['primary_id'],
                    'description': item['description']
                })

        if len(phenotype_info['mim_phenotypes']) > 0 or len(phenotype_info['orphanet_phenotypes']) > 0:
            phenotype_info['has_mendelian_phenotype'] = True
        else:
            phenotype_info['has_mendelian_phenotype'] = False

        return phenotype_info

    def get_gene_structure(self, gene_id):
        """
        Query ensembl API for the transcript/exon structure of a gene
        This is the foundation of the elements in db.genes
        Exception if can't process gene
        """

        gene = {}

        # gene basics
        url = self._get_rest_url() + '/feature/id/%s' % gene_id
        params = {'content-type': 'application/json', 'feature': 'gene'}
        gene_list_json = requests.get(url, params=params).json()
        gene_list_json = [item for item in gene_list_json if item['ID'] == gene_id]
        if len(gene_list_json) == 0:
            raise Exception("No genes with ID %s" % gene_id)
        if len(gene_list_json) > 1:
            raise Exception(">1 ensembl genes with ID %s" % gene_id)
        gene_json = gene_list_json[0]

        chr = ensembl_parsing_utils.get_chr_from_seq_region_name(gene_json['seq_region_name'])
        if chr is None:
            raise Exception("Gene %s is on a nonstandard chromosome: %s" % (gene_id, chr) )

        gene['chr'] = chr
        gene['start'] = gene_json['start']
        gene['stop'] = gene_json['end']
        gene['xstart'] = genomeloc.get_single_location(chr, gene['start'])
        gene['xstop'] = genomeloc.get_single_location(chr, gene['stop'])

        gene['gene_id'] = gene_json['ID']
        gene['symbol'] = gene_json['external_name']
        gene['description'] = gene_json['description']
        gene['biotype'] = gene_json['biotype']

        # transcripts
        url = self._get_rest_url() + '/feature/id/%s' % gene_id
        params = {'content-type': 'application/json', 'feature': 'transcript'}
        transcript_json = [t for t in requests.get(url, params=params).json() if t['Parent'] == gene_id]

        gene['transcripts'] = []
        for t in transcript_json:
            transcript_id = t['ID']
            transcript = dict(
                transcript_id=transcript_id,
                biotype=t['biotype'],
                start=t['start'],
                stop=t['end']
            )
            transcript['xstart'] = genomeloc.get_single_location(chr, transcript['start'])
            transcript['xstop'] = genomeloc.get_single_location(chr, transcript['stop'])

            # exons_for_transcript
            url = self._get_rest_url() + '/feature/id/%s' % transcript_id
            params = {'content-type': 'application/json', 'feature': 'exon'}
            transcript_exon_json = requests.get(url, params=params).json()
            transcript['exons'] = [
                e['ID'] for e in sorted(transcript_exon_json, key=lambda x: x['start']) if e['Parent'] == transcript_id
            ]

            gene['transcripts'].append(transcript)

        # exons
        url = self._get_rest_url() + '/feature/id/%s' % gene_id
        params = {'content-type': 'application/json', 'feature': 'exon'}
        exon_json = requests.get(url, params=params).json()

        transcript_ids = {t['transcript_id'] for t in gene['transcripts']}
        exon_ids_seen = set()
        gene['exons'] = []
        for e in exon_json:
            exon_id = e['ID']
            # skip exons that aren't actually in one of this gene's transcripts
            if e['Parent'] not in transcript_ids:
                continue
            if exon_id in exon_ids_seen:
                continue
            exon = {
                'exon_id': exon_id,
                'start': e['start'],
                'stop': e['end'],
            }
            exon['xstart'] = genomeloc.get_single_location(chr, exon['start'])
            exon['xstop'] = genomeloc.get_single_location(chr, exon['stop'])
            gene['exons'].append(exon)
            exon_ids_seen.add(e['ID'])

        # cds
        url = self._get_rest_url() + '/feature/id/%s' % gene_id
        params = {'content-type': 'application/json', 'feature': 'cds'}
        cds_json = requests.get(url, params=params).json()

        cds_map = {}  # map from (start, stop) -> {start, stop, transcripts}
        for c in cds_json:
            # skip exons that aren't actually in one of this gene's transcripts
            if c['Parent'] not in transcript_ids:
                continue
            cds_t = (c['start'], c['end'])
            if cds_t not in cds_map:
                cds_map[cds_t] = {
                    'start': c['start'],
                    'stop': c['end'],
                    'xstart': genomeloc.get_single_location(chr, c['start']),
                    'xstop': genomeloc.get_single_location(chr, c['end']),
                    'transcripts': [],
                }
            cds_map[cds_t]['transcripts'].append(c['Parent'])
        gene['cds'] = sorted(cds_map.values(), key=lambda x: (x['start'], x['stop']))
        for i, cds in enumerate(gene['cds']):
            cds['cds_id'] = '%s-%i' % (gene['gene_id'], i+1)
        return gene



class EnsemblDBProxy(object):
    """
    Provides a few direct lookups into an ensembl database that aren't provided by REST server
    Basically a really simple version of a python ensembl API
    """

    def __init__(self, host, port, user):
        self.db_conn = mdb.connect(
            host=host,
            port=port,
            user=user,
            db="homo_sapiens_core_74_37"
        )

    def get_all_gene_ids(self):
        """
        List of all gene IDs (arbitrary order) that we consider in xbrowse
        This does *not* include genes are:
        - not ensembl genes
        - not on a standard chromosome (in genomeloc)
        """
        cursor = self.db_conn.cursor()
        cursor.execute("select gene.stable_id, seq_region.name from gene "
                       "join seq_region on gene.seq_region_id=seq_region.seq_region_id")
        return [row[0] for row in cursor if ensembl_parsing_utils.get_chr_from_seq_region_name(row[1]) is not None]

    def get_all_exons(self):
        """
        Get a list of all exons (order not guaranteed) from ensembl
        Fetched from database, not REST
        """
        cursor = self.db_conn.cursor()
        cursor.execute("select exon.stable_id, seq_region.name, exon.seq_region_start, exon.seq_region_end from exon "
                       "join seq_region on exon.seq_region_id=seq_region.seq_region_id")
        exons = []
        for row in cursor:
            chr = ensembl_parsing_utils.get_chr_from_seq_region_name(row[1])
            start = row[2]
            stop = row[3]
            if chr is None:
                continue
            exon = dict(exon_id=row[0])
            exon['xstart'] = genomeloc.get_single_location(chr, start)
            exon['xstop'] = genomeloc.get_single_location(chr, stop)
            exons.append(exon)
        return exons