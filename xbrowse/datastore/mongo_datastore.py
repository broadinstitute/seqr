from collections import defaultdict
import random
import string
import copy

import pymongo

from xbrowse import utils as xbrowse_utils
from xbrowse import vcf_stuff
from xbrowse.core.variant_filters import VariantFilter, passes_variant_filter
from xbrowse import Variant
import datastore


GENOTYPE_QUERY_MAP = {

    'ref_ref': 0,
    'ref_alt': 1,
    'alt_alt': 2,

    'has_alt': {'$gte': 1},
    'has_ref': {'$in': [0,1]},

    'not_missing': {'$gte': 0},
    'missing': -1,

}


def _add_genotype_filter_to_variant_query(db_query, genotype_filter):
    """
    Add conditions to db_query from the genotype filter
    Edits in place, returns True if successful
    """
    for indiv_id, genotype in genotype_filter.items():
        key = 'genotypes.%s.num_alt' % indiv_id
        db_query[key] = GENOTYPE_QUERY_MAP[genotype]
    return True


def _make_db_query(genotype_filter=None, variant_filter=None):
    """
    Caller specifies filters to get_variants, but they are evaluated later.
    Here, we just inspect those filters and see what heuristics we can apply to avoid a full table scan,
    Query here must return a superset of the true get_variants results
    Note that the full annotation isn't stored, so use the fields added by _add_index_fields_to_variant
    """
    db_query = {}

    # genotype filter
    if genotype_filter is not None:
        _add_genotype_filter_to_variant_query(db_query, genotype_filter)

    if variant_filter:
        if variant_filter.so_annotations:
            db_query['db_tags'] = {'$in': variant_filter.so_annotations}
        if variant_filter.ref_freqs:
            for population, freq in variant_filter.ref_freqs:
                db_query['db_freqs.' + population] = {'$lte': freq}

    return db_query


def _add_index_fields_to_variant(variant_dict, annotation=None):
    """
    Add fields to the vairant dictionary that you want to index on before load it
    """
    if annotation:
        variant_dict['db_freqs'] = annotation['freqs']
        variant_dict['db_tags'] = annotation['annotation_tags']


class MongoDatastore(datastore.Datastore):

    def __init__(self, db, annotator):
        self._db = db
        self._annotator = annotator

    #
    # Variant search
    #

    def get_variants(self, project_id, family_id, genotype_filter=None, variant_filter=None):

        db_query = _make_db_query(genotype_filter, variant_filter)
        collection = self._get_family_collection(project_id, family_id)
        for variant_dict in collection.find(db_query).sort('xpos'):
            variant = Variant.fromJSON(variant_dict)
            self._annotator.annotate_variant(variant)
            if passes_variant_filter(variant, variant_filter)[0]:
                yield variant

    def get_variants_in_gene(self, project_id, family_id, gene_id, genotype_filter=None, variant_filter=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)

        db_query = _make_db_query(genotype_filter, modified_variant_filter)
        collection = self._get_family_collection(project_id, family_id)

        # we have to collect list in memory here because mongo can't sort on xpos,
        # as result size can get too big.
        # need to find a better way to do this.
        variants = []
        for variant_dict in collection.find(db_query).hint([('gene_ids', pymongo.ASCENDING), ('xpos', pymongo.ASCENDING)]):
            variant = Variant.fromJSON(variant_dict)
            if passes_variant_filter(variant, modified_variant_filter):
                variants.append(variant)
        variants = sorted(variants, key=lambda v: v.unique_tuple())
        for v in variants:
            yield v

    def get_single_variant(self, project_id, family_id, xpos, ref, alt):

        collection = self._get_family_collection(project_id, family_id)
        variant_dict = collection.find_one({'xpos': xpos, 'ref': ref, 'alt': alt})
        if variant_dict:
            variant = Variant.fromJSON(variant_dict)
            self._annotator.annotate_variant(variant)
            return variant
        else:
            return None

    def get_variants_cohort(self, project_id, cohort_id, variant_filter=None):

        db_query = _make_db_query(None, variant_filter)
        collection = self._get_family_collection(project_id, cohort_id)
        for variant in collection.find(db_query).sort('xpos'):
            yield Variant.fromJSON(variant)

    def get_single_variant_cohort(self, project_id, cohort_id, xpos, ref, alt):

        collection = self._get_family_collection(project_id, cohort_id)
        variant = collection.find_one({'xpos': xpos, 'ref': ref, 'alt': alt})
        return Variant.fromJSON(variant)

    #
    # New sample stuff
    #
    def get_all_individuals(self):
        """
        List of all individuals in the datastore
        Items are (project_id, indiv_id) tuples
        """
        return [(i['project_id'], i['indiv_id']) for i in self._db.individuals.find()]

    def get_all_families(self):
        """
        List of all families in the datastore
        Items are (project_id, family_id) tuples
        """
        return [(i['project_id'], i['family_id']) for i in self._db.families.find()]

    def individual_exists(self, project_id, indiv_id):
        return self._db.individuals.find_one({
            'project_id': project_id,
            'indiv_id': indiv_id
        }) is not None

    def add_individual(self, project_id, indiv_id):
        if self.individual_exists(project_id, indiv_id):
            raise Exception("Indiv (%s, %s) already exists" % (project_id, indiv_id))
        indiv = {
            'project_id': project_id,
            'indiv_id': indiv_id,
        }
        self._db.individuals.save(indiv)

    def get_individuals(self, project_id):
        return [ i['indiv_id'] for i in self._db.individuals.find({ 'project_id': project_id }) ]

    def family_exists(self, project_id, family_id):
        return self._db.families.find_one({'project_id': project_id, 'family_id': family_id}) is not None

    def get_individuals_for_family(self, project_id, family_id):
        return self._db.families.find_one({'project_id': project_id, 'family_id': family_id})['individuals']

    def get_family_status(self, project_id, family_id):
        family_doc = self._db.families.find_one({'project_id': project_id, 'family_id': family_id})
        if not family_doc:
            return None
        return family_doc['status']

    def get_family_statuses(self, family_list):
        ret = {f: None for f in family_list}
        by_project = defaultdict(list)
        for project_id, family_id in family_list:
            by_project[project_id].append(family_id)
        for project_id, family_id_list in by_project.items():
            for family_doc in self._db.families.find({'project_id': project_id, 'family_id': {'$in': family_id_list}}):
                ret[(project_id, family_doc['family_id'])] = family_doc['status']
        return ret

    def _get_family_info(self, project_id, family_id):
        return self._db.families.find_one({'project_id': project_id, 'family_id': family_id})

    def _get_family_collection(self, project_id, family_id):
        return self._db[self._get_family_info(project_id, family_id)['coll_name']]

    #
    # Variant loading
    # Unique to mongo datastore, not part of protocol
    #

    def _add_family_info(self, project_id, family_id, individuals):
        """
        Add all the background info about this family
        We try to keep this as simple as possible - just IDs
        After this is run, variants are ready to be loaded
        """

        if self.family_exists(project_id, family_id):
            raise Exception("Family (%s, %s) already exists" % (project_id, family_id))

        for indiv_id in individuals:
            if not self.individual_exists(project_id, indiv_id):
                self.add_individual(project_id, indiv_id)

        family_coll_name = 'family_' + ''.join([random.choice(string.digits) for i in range(8)])
        family = {
            'project_id': project_id,
            'family_id': family_id,
            'individuals': individuals,
            'coll_name': family_coll_name,
            'status': 'loading'
        }

        family_collection = self._db[family_coll_name]
        self._index_family_collection(family_collection)

        self._db.families.save(family, safe=True)

    def add_family(self, project_id, family_id, individuals):
        """
        Add new family
        Adds individuals if they don't exist yet
        Phenotypes and pedigrees aren't stored, just which individuals
        """
        self._add_family_info(project_id, family_id, individuals)

    def load_family(self, project_id, family_id, vcf_file_path, reference_populations=None):
        """
        Load all the variant data for family from scratch
        Used for loading a family for the first time and for reloads
        """
        _refpops = reference_populations if reference_populations is not None else []
        self._load_variants_for_family(project_id, family_id, vcf_file_path, reference_populations=_refpops)
        self._finalize_family_load(project_id, family_id)

    def add_family_set(self, family_list):
        """
        Add a set of families from the same VCF file
        family_list is just a list of dicts with keys of project_id, family_id, individuals
        """
        for fam_info in family_list:
            self._add_family_info(fam_info['project_id'], fam_info['family_id'], fam_info['individuals'])

    def load_family_set(self, vcf_file_path, family_list, reference_populations=None):
        """
        Load a set of families from the same VCF file
        family_list is a list of (project_id, family_id) tuples
        """
        family_info_list = [self._get_family_info(f[0], f[1]) for f in family_list]
        self._load_variants_for_family_set(family_info_list, vcf_file_path, reference_populations=reference_populations)
        for family in family_info_list:
            self._finalize_family_load(family['project_id'], family['family_id'])

    def _load_variants_for_family(self, project_id, family_id, vcf_file, reference_populations=None):
        self._add_vcf_file_for_family(project_id, family_id, vcf_file, reference_populations=reference_populations)

    def _add_vcf_file_for_family(self, project_id, family_id, vcf_file_path, reference_populations=None):

        fam = self._db.families.find_one({'project_id': project_id, 'family_id': family_id})
        collection = self._db[fam['coll_name']]
        indiv_id_list = fam['individuals']

        for i, variant in enumerate(vcf_stuff.iterate_vcf_path(
            vcf_file_path,
            genotypes=True,
            indiv_id_list=indiv_id_list,
        )):
            if i % 10000 == 0:
                print i
            family_variant = variant.make_copy(restrict_to_genotypes=fam['individuals'])
            if xbrowse_utils.is_variant_relevant_for_individuals(family_variant, fam['individuals']) is True:
                self._save_variant_to_collection(family_variant, collection)

    def _load_variants_for_family_set(self, family_info_list, vcf_file_path, reference_populations=None):
        """
        Load variants for a set of families, assuming all come from the same VCF file

        Added after load_variants_for_family to speed up loading - goal is to
        only iterate the VCF once. Here's how it works:

        for each raw variant:
            annotate
            for each family:
                extract family variant from full variant
                update variant inheritance
                if family variant is relevant for family:
                    add to collection

        """
        # map of family_id -> variant collection
        self._add_vcf_file_for_family_set(family_info_list, vcf_file_path, reference_populations=reference_populations)

    def _add_vcf_file_for_family_set(self, family_info_list, vcf_file_path, reference_populations=None):
        collections = {f['family_id']: self._db[f['coll_name']] for f in family_info_list}
        for collection in collections.values():
            collection.drop_indexes()
        indiv_id_list = [i for f in family_info_list for i in f['individuals']]

        for variant in vcf_stuff.iterate_vcf_path(vcf_file_path, genotypes=True, indiv_id_list=indiv_id_list):
            annotation = self._annotator.get_annotation(variant.xpos, variant.ref, variant.alt, populations=reference_populations)
            for family in family_info_list:
                # TODO: can we move this inside the if relevant clause below?
                family_variant = variant.make_copy(restrict_to_genotypes=family['individuals'])
                family_variant_dict = family_variant.toJSON()
                _add_index_fields_to_variant(family_variant_dict, annotation)
                if xbrowse_utils.is_variant_relevant_for_individuals(family_variant, family['individuals']):
                    collection = collections[family['family_id']]
                    collection.insert(family_variant_dict)

    # def _save_variant_to_collection(self, family_variant, collection):
    #     variant_dict = family_variant.toJSON()
    #     annotation = self._annotator.get_ann
    #     _add_index_fields_to_variant(variant_dict)
    #     collection.insert(variant_dict, w=0)

    def _finalize_family_load(self, project_id, family_id):
        """
        Call after family is loaded. Sets status and possibly more in the future
        """
        self._index_family_collection(self._get_family_collection(project_id, family_id))
        family = self._db.families.find_one({'project_id': project_id, 'family_id': family_id})
        family['status'] = 'loaded'
        self._db.families.save(family, safe=True)

    def _index_family_collection(self, collection):
        collection.ensure_index('xpos')
        collection.ensure_index([('gene_ids', 1), ('xpos', 1)])
        collection.ensure_index([('vep_consequence', 1), ('xpos', 1)])
        collection.ensure_index([('freqs', 1), ('xpos', 1)])

    def _clear_all(self):
        self._db.drop_collection('individuals')
        self._db.drop_collection('families')
        names = self._db.collection_names()
        for name in names:
            if name.startswith('family_'):
                self._db.drop_collection(name)

    def delete_project(self, project_id):
        self._db.snp_arrays.remove({'project_id': project_id})
        self._db.individuals.remove({'project_id': project_id})
        for family_info in self._db.families.find({'project_id': project_id}):
            self._db.drop_collection(family_info['coll_name'])
        self._db.families.remove({'project_id': project_id})

    def delete_family(self, project_id, family_id):
        self._db.snp_arrays.remove({'project_id': project_id, 'family_id': family_id})
        for family_info in self._db.families.find({'project_id': project_id, 'family_id': family_id}):
            self._db.drop_collection(family_info['coll_name'])
        self._db.families.remove({'project_id': project_id, 'family_id': family_id})
