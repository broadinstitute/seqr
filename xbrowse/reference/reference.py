import gzip
import os

import itertools
import json
import ensembl_parsing_utils
import gene_expression
import logging
import pandas
import pymongo
import redis
import requests
import settings
from xbrowse import genomeloc
from xbrowse.parsers.gtf import get_data_from_gencode_gtf
from xbrowse.reference.clinvar import parse_clinvar_vcf
from xbrowse.utils import get_progressbar


from .utils import get_coding_regions_from_gene_structure, get_coding_size_from_gene_structure

logger = logging.getLogger(__name__)

class Reference(object):
    """
    Reference is a workhorse - it provides an API for looking up any information about the human genome
    Requires an ensembl db connection, an ensembl REST API address, and a mongo db
    """

    def __init__(self, settings_module):

        # TODO: should we store settings module or just parse all the values here?
        self.settings_module = settings_module
        self.has_phenotype_data = settings_module.has_phenotype_data

        self._db = pymongo.MongoClient(host=os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost'))[settings_module.db_name]

        # these are all lazy loaded
        self._ensembl_rest_proxy = None
        self._ensembl_db_proxy = None
        self._gene_positions = None
        self._ordered_genes = None
        self._gene_symbols = None
        self._gene_symbols_r = None
        self._gene_ids = None
        self._gene_summaries = None

        self._redis_client = None
        if settings.REDIS_SERVICE_HOSTNAME:
            try:
                self._redis_client = redis.StrictRedis(host=settings.REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
                self._redis_client.ping()
            except redis.exceptions.TimeoutError as e:
                logger.warn("Unable to connect to redis: " + str(e))
                self._redis_client = None


    def get_ensembl_db_proxy(self):
        if self._ensembl_db_proxy is None:
            self._ensembl_db_proxy = EnsemblDBProxy(
                host=self.settings_module.ensembl_db_host,
                port=self.settings_module.ensembl_db_port,
                user=self.settings_module.ensembl_db_user,
            )
        return self._ensembl_db_proxy

    def get_ensembl_rest_proxy(self):
        if self._ensembl_rest_proxy is None:
            self._ensembl_rest_proxy = EnsemblRESTProxy(
            host=self.settings_module.ensembl_rest_host,
            port=self.settings_module.ensembl_rest_port
        )
        return self._ensembl_rest_proxy

    def load(self):
        self._load_clinvar()
        self._load_genes()
        self._load_additional_gene_info()
        self._load_tags()
        self._load_gtex_data()
        self._reset_reference_cache()

    def _load_genes(self):

        self._db.drop_collection('genes')
        self._db.genes.ensure_index('gene_id')

        self._db.drop_collection('transcripts')
        self._db.transcripts.ensure_index('transcript_id')
        self._db.transcripts.ensure_index('gene_id')

        self._db.drop_collection('exons')
        self._db.exons.ensure_index('exon_id')
        self._db.exons.ensure_index('gene_id')

        gencode_file = gzip.open(self.settings_module.gencode_gtf_file)
        size = os.path.getsize(self.settings_module.gencode_gtf_file)
        progress = get_progressbar(size, 'Loading gene definitions from GTF')
        for datatype, obj in get_data_from_gencode_gtf(gencode_file):
            progress.update(gencode_file.fileobj.tell())

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

            if datatype == 'exon':
                exon_id = obj['exon_id']
                transcript_id = obj['transcript_id']
                del obj['transcript_id']
                if self._db.exons.find_one({'exon_id': exon_id}):
                    self._db.exons.update({'exon_id': exon_id}, {'$push': {'transcripts': transcript_id}})
                else:
                    obj['transcripts'] = [transcript_id,]
                    obj['tags'] = {}
                    self._db.exons.insert(obj)

            if datatype == 'cds':
                exon_id = obj['exon_id']
                # this works because cds always comes after exon
                # this is obviously an inglorious hack - all the gtf parsing should be improved
                self._db.exons.update({'exon_id': exon_id}, {'$set': {
                    'cds_start': obj['start'],
                    'cds_stop': obj['stop'],
                    'cds_xstart': obj['xstart'],
                    'cds_xstop': obj['xstop'],
                }})

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
        self._db.drop_collection('tissue_expression')
        self._db.tissue_expression.ensure_index('gene_id')

        for gene_id, expression_array in gene_expression.get_tissue_expression_values_by_gene(
            self.settings_module.gtex_expression_file,
            self.settings_module.gtex_samples_file
        ):
            self._db.tissue_expression.insert({
                'gene_id': gene_id,
                'expression_display_values': expression_array
            })

    def _load_additional_gene_info(self):

        gene_ids = self.get_all_gene_ids()
        size = len(gene_ids)
        progress = get_progressbar(size, 'Loading additional info about genes')
        for i, gene_id in enumerate(gene_ids):
            progress.update(i)

            # calculate coding size
            gene_structure = self.get_gene_structure(gene_id)
            coding_size = get_coding_size_from_gene_structure(gene_id, gene_structure)
            self._db.genes.update({'gene_id': gene_id}, {'$set': {'coding_size': coding_size}})

            # phenotypes
            if self.has_phenotype_data:
                phenotype_info = self.get_ensembl_rest_proxy().get_phenotype_info(gene_id)
            else:
                phenotype_info = {
                    'has_mendelian_phenotype': False,
                    'mim_id': "",
                    'mim_phenotypes': [],
                    'orphanet_phenotypes': [],
                }
            self._db.genes.update(
                {'gene_id': gene_id},
                {'$set': {'phenotype_info': phenotype_info}}
            )

    def update_phenotype_info(self, gene_id, phenotype_info):
        """Sets phenotype info for the given gene_id
        Args:
          gene_id: Ensembl gene id

          phenotype_info: for RYR1 it would be:
          {
             'has_mendelian_phenotype': true,
             'mim_id': "180901",  # gene id
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
        assert 'has_mendelian_phenotype' in phenotype_info, "Invalid phenotype_info arg: " + str(phenotype_info)
        assert 'mim_id' in phenotype_info, "Invalid mim_id arg: " + str(phenotype_info)
        assert 'mim_phenotypes' in phenotype_info, "Invalid mim_phenotypes arg: " + str(phenotype_info)
        assert 'orphanet_phenotypes' in phenotype_info, "Invalid orphanet_phenotypes arg: " + str(phenotype_info)

        self._db.genes.update(
                {'gene_id': gene_id},
                {'$set': {'phenotype_info': phenotype_info}}
            )

    def _load_tags(self):
        self._load_gene_list_tags()
        self._load_gene_test_statistic_tags()

    def _load_gene_list_tags(self):
        for gene_tag in self.settings_module.gene_list_tags:
            tag_id = gene_tag['slug']
            # first set all genes to false
            self._db.genes.update({}, {'$set': {'tags.'+tag_id: False}}, multi=True)

            gene_ids = [line.strip() for line in open(gene_tag['file']).readlines()]
            for gene_id in gene_ids:
                self._db.genes.update({'gene_id': gene_id}, {'$set': {'tags.'+tag_id: True}})

    def _load_gene_test_statistic_tags(self):

        score_data = pandas.DataFrame.from_csv(self.settings_module.constraint_scores_file)

        for gene_tag in self.settings_module.gene_test_statistic_tags:
            tag_id = gene_tag['slug']
            tag_field = gene_tag['data_field']

            # first set all to None
            self._db.genes.update({}, {'$set': {'tags.'+tag_id: None}}, multi=True)

            scores = getattr(score_data, tag_field)
            ranks = scores.rank(ascending=False)
            for gene_id, score in scores.iteritems():
                self._db.genes.update({'gene_id': gene_id}, {'$set': {'tags.'+tag_id: score}})
            for gene_id, rank in ranks.iteritems():
                self._db.genes.update({'gene_id': gene_id}, {'$set': {'tags.'+tag_id+'_rank': [int(rank), len(ranks)]}})

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

            if gene.get("phenotype_info") and gene['phenotype_info']['has_mendelian_phenotype'] is True:
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

    #
    # Gene lookups
    #

    def get_all_gene_ids(self):
        return [doc['gene_id'] for doc in self._db.genes.find(projection={'gene_id': True})]

    def get_all_exon_ids(self):
        raise NotImplementedError

    def get_ordered_genes(self):
        if self._ordered_genes is None:
            self._ordered_genes = self._get_reference_cache('ordered_genes')
        return self._ordered_genes

    def get_gene_bounds(self, gene_id):
        if self._gene_positions is None:
            self._gene_positions = self._get_reference_cache('gene_positions')

        return self._gene_positions.get(gene_id)

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
        return self._db.genes.find_one({'gene_id': gene_id}, projection={'_id': False})

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
        redis_key = 'Reference__get_gene_summary__'+str(gene_id)
        if self._redis_client:
            gene_summary_string = self._redis_client.get(redis_key)
            if gene_summary_string is not None:
                gene_summary = json.loads(gene_summary_string)

        self._ensure_cache('gene_summaries')
        gene_summary = self._gene_summaries.get(gene_id, {})

        if self._redis_client:
            self._redis_client.set(redis_key, json.dumps(gene_summary))

        return gene_summary

    def get_gene_symbols(self):
        """
        Map of gene_id -> gene symbol for all genes
        """
        if self._gene_symbols is None:
            self._gene_symbols = self._get_reference_cache('gene_symbols')
            
        if self._gene_symbols is None:
            raise Exception("gene_symbols collection not found in mongodb. If this is a new install, please run python manage.py load_resources")
        return self._gene_symbols

    def get_ordered_exons(self):
        """
        Get a list of all exons in genomic order
        Returns a list of (exon_id, xstart, xstop) tuples
        """
        exon_tuples = self.get_ensembl_rest_proxy().get_all_exons()
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

    def get_gene_structure(self, gene_id):
        d = dict()
        d['transcripts'] = list(self._db.transcripts.find({'gene_id': gene_id}))
        d['exons'] = list(self._db.exons.find({'gene_id': gene_id}))
        return d

    def get_all_coding_regions_sorted(self):
        """
        Return a list of CodingRegions, in order
        "order" implies that cdrs for a gene might not be consecutive
        """
        cdr_list = []
        for gene_id in self.get_all_gene_ids():
            gene = self.get_gene(gene_id)
            if gene['gene_type'] != 'protein_coding':
                continue
            gene_structure = self.get_gene_structure(gene_id)
            flattened_cdrs = get_coding_regions_from_gene_structure(gene_id, gene_structure)
            cdr_list.extend(flattened_cdrs)
        return sorted(cdr_list, key=lambda x: (x.xstart, x.xstop))

    def get_clinvar_info(self, xpos, ref, alt):
        doc = self._db.clinvar.find_one({'xpos': xpos, 'ref': ref, 'alt': alt})
        if doc is None:
            return None, ''
        else:
            return doc['variant_id'], doc['clinsig']


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
            db="homo_sapiens_core_78_37"
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

