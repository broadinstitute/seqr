from collections import defaultdict
import os
import random
import string
import copy

import pymongo
from xbrowse.utils import compressed_file, get_progressbar

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





def _add_index_fields_to_variant(variant_dict, annotation=None):
    """
    Add fields to the vairant dictionary that you want to index on before load it
    """
    if annotation:
        variant_dict['db_freqs'] = annotation['freqs']
        variant_dict['db_tags'] = annotation['annotation_tags']
        variant_dict['db_gene_ids'] = annotation['gene_ids']


class MongoDatastore(datastore.Datastore):

    def __init__(self, db, annotator, custom_population_store=None, custom_populations_map=None):
        self._db = db
        self._annotator = annotator
        self._custom_population_store = custom_population_store
        self._custom_populations_map = custom_populations_map
        if self._custom_populations_map is None:
            self._custom_populations_map = {}

    def _make_db_query(self, genotype_filter=None, variant_filter=None):
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
            if variant_filter.genes:
                db_query['db_gene_ids'] = {'$in': variant_filter.genes}
            if variant_filter.ref_freqs:
                for population, freq in variant_filter.ref_freqs:
                    if population in self._annotator.reference_population_slugs:
                        db_query['db_freqs.' + population] = {'$lte': freq}

        return db_query

    #
    # Variant search
    #

    def get_variants(self, project_id, family_id, genotype_filter=None, variant_filter=None):

        db_query = self._make_db_query(genotype_filter, variant_filter)
        print("Getting variants from collection for %s, %s" % (project_id, family_id))
        collection = self._get_family_collection(project_id, family_id)
        for variant_dict in collection.find(db_query).sort('xpos'):
            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            if passes_variant_filter(variant, variant_filter)[0]:
                yield variant

    def get_variants_in_gene(self, project_id, family_id, gene_id, genotype_filter=None, variant_filter=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)

        db_query = self._make_db_query(genotype_filter, modified_variant_filter)
        collection = self._get_family_collection(project_id, family_id)

        # we have to collect list in memory here because mongo can't sort on xpos,
        # as result size can get too big.
        # need to find a better way to do this.
        variants = []
        for variant_dict in collection.find(db_query).hint([('db_gene_ids', pymongo.ASCENDING), ('xpos', pymongo.ASCENDING)]):
            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            if passes_variant_filter(variant, modified_variant_filter):
                variants.append(variant)
        variants = sorted(variants, key=lambda v: v.unique_tuple())
        for v in variants:
            yield v

    def get_single_variant(self, project_id, family_id, xpos, ref, alt):

        collection = self._get_family_collection(project_id, family_id)
        if not collection:
            return None
        variant_dict = collection.find_one({'xpos': xpos, 'ref': ref, 'alt': alt})
        if variant_dict:
            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            return variant
        else:
            return None

    def get_variants_cohort(self, project_id, cohort_id, variant_filter=None):

        db_query = self._make_db_query(None, variant_filter)
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
        family_info = self._get_family_info(project_id, family_id)
        if not family_info:
            return None
        return self._db[family_info['coll_name']]

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

    def add_family_set(self, family_list):
        """
        Add a set of families from the same VCF file
        family_list is just a list of dicts with keys of project_id, family_id, individuals
        """
        for fam_info in family_list:
            self._add_family_info(fam_info['project_id'], fam_info['family_id'], fam_info['individuals'])

    def load_family_set(self, vcf_file_path, family_list, reference_populations=None, vcf_id_map=None):
        """
        Load a set of families from the same VCF file
        family_list is a list of (project_id, family_id) tuples
        """
        family_info_list = [self._get_family_info(f[0], f[1]) for f in family_list]
        self._load_variants_for_family_set(
            family_info_list,
            vcf_file_path,
            reference_populations=reference_populations,
            vcf_id_map=vcf_id_map
        )
        for family in family_info_list:
            self._finalize_family_load(family['project_id'], family['family_id'])

    def _load_variants_for_family_set(self, family_info_list, vcf_file_path, reference_populations=None, vcf_id_map=None):
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
        self._add_vcf_file_for_family_set(
            family_info_list,
            vcf_file_path,
            reference_populations=reference_populations,
            vcf_id_map=vcf_id_map
        )

    def _add_vcf_file_for_family_set(self, family_info_list, vcf_file_path, reference_populations=None, vcf_id_map=None):
        collections = {f['family_id']: self._db[f['coll_name']] for f in family_info_list}
        for collection in collections.values():
            collection.drop_indexes()
        indiv_id_list = [i for f in family_info_list for i in f['individuals']]

        print("Loading variants for families %(family_info_list)s from %(vcf_file_path)s" % locals())

        vcf_file = compressed_file(vcf_file_path)
        size = os.path.getsize(vcf_file_path)
        progress = get_progressbar(size, 'Loading VCF: {}'.format(vcf_file_path))
        for variant in vcf_stuff.iterate_vcf(vcf_file, genotypes=True, indiv_id_list=indiv_id_list, vcf_id_map=vcf_id_map):
            progress.update(vcf_file.tell_progress())
            try:
                annotation = self._annotator.get_annotation(variant.xpos, variant.ref, variant.alt, populations=reference_populations)
            except ValueError, e:
                print("WARNING: " + str(e))
                continue
            for family in family_info_list:
                # TODO: can we move this inside the if relevant clause below?
                family_variant = variant.make_copy(restrict_to_genotypes=family['individuals'])
                family_variant_dict = family_variant.toJSON()
                _add_index_fields_to_variant(family_variant_dict, annotation)
                if xbrowse_utils.is_variant_relevant_for_individuals(family_variant, family['individuals']):
                    collection = collections[family['family_id']]
                    collection.insert(family_variant_dict)

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
        collection.ensure_index([('db_freqs', 1), ('xpos', 1)])
        collection.ensure_index([('db_tags', 1), ('xpos', 1)])
        collection.ensure_index([('db_gene_ids', 1), ('xpos', 1)])

    def delete_project(self, project_id):
        self._db.individuals.remove({'project_id': project_id})
        for family_info in self._db.families.find({'project_id': project_id}):
            self._db.drop_collection(family_info['coll_name'])
        self._db.families.remove({'project_id': project_id})

    def delete_family(self, project_id, family_id):
        for family_info in self._db.families.find({'project_id': project_id, 'family_id': family_id}):
            self._db.drop_collection(family_info['coll_name'])
        self._db.families.remove({'project_id': project_id, 'family_id': family_id})

    def add_annotations_to_variant(self, variant, project_id):
        self._annotator.annotate_variant(variant)
        if self._custom_population_store:
            custom_pop_slugs = self._custom_populations_map.get(project_id)
            if custom_pop_slugs:
                self._custom_population_store.add_populations_to_variants([variant], custom_pop_slugs)


    #
    # This stuff is all copied in from ProjectDatastore
    #

    def _get_project_collection(self, project_id):
        project = self._db.projects.find_one({'project_id': project_id})
        return self._db[project['collection_name']]

    def add_variants_to_project_from_vcf(self, vcf_file, project_id, indiv_id_list=None):
        """
        This is how variants are loaded
        """
        project_collection = self._get_project_collection(project_id)
        reference_populations = self._annotator.reference_population_slugs + self._custom_populations_map.get(project_id)
        for variant in vcf_stuff.iterate_vcf(vcf_file, genotypes=True, indiv_id_list=indiv_id_list):
            variant_dict = project_collection.find_one({'xpos': variant.xpos, 'ref': variant.ref, 'alt': variant.alt})
            if not variant_dict:
                variant_dict = variant.toJSON()
                try:
                    annotation = self._annotator.get_annotation(variant.xpos, variant.ref, variant.alt, populations=reference_populations)
                except ValueError, e:
                    print("WARNING: " + str(e))
                    continue
                _add_index_fields_to_variant(variant_dict, annotation)
            else:
                for indiv_id, genotype in variant.get_genotypes():
                    if genotype.num_alt != 0:
                        variant_dict['genotypes'][indiv_id] = genotype._asdict()
            project_collection.save(variant_dict)

    def project_exists(self, project_id):
        return self._db.projects.find_one({'project_id': project_id})

    def add_project(self, project_id):
        """
        Add all the background info about this family
        We try to keep this as simple as possible - just IDs
        After this is run, variants are ready to be loaded
        """

        if self.project_exists(project_id):
            raise Exception("Project {} exists".format(project_id))

        project = {
            'project_id': project_id,
            'collection_name': 'project_' + ''.join([random.choice(string.digits) for i in range(8)]),
        }
        self._db.projects.insert(project)
        project_collection = self._db[project['collection_name']]
        self._index_family_collection(project_collection)

    def delete_project_store(self, project_id):
        project = self._db.projects.find_one({'project_id': project_id})
        if project:
            self._db.drop_collection(project['collection_name'])
        self._db.projects.remove({'project_id': project_id})

    def get_project_variants_in_gene(self, project_id, gene_id, variant_filter=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)

        db_query = self._make_db_query(None, modified_variant_filter)
        collection = self._get_project_collection(project_id)

        # we have to collect list in memory here because mongo can't sort on xpos,
        # as result size can get too big.
        # need to find a better way to do this.
        variants = []
        for variant_dict in collection.find(db_query).hint([('db_gene_ids', pymongo.ASCENDING), ('xpos', pymongo.ASCENDING)]):
            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            if passes_variant_filter(variant, modified_variant_filter):
                variants.append(variant)
        variants = sorted(variants, key=lambda v: v.unique_tuple())
        for v in variants:
            yield v