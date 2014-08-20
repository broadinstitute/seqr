import random
import string
import copy

import pymongo

from xbrowse import vcf_stuff
from xbrowse import Variant
from xbrowse.core.variant_filters import VariantFilter, passes_variant_filter


class ProjectDatastore():
    """
    Stores all variants in a project, but only nonreference genotypes (including missing)
    Data stored in a project_* collection; not annotated
    """

    def __init__(self, db, annotator):
        self._db = db
        self._annotator = annotator

    def project_exists(self, project_id):
        return self._db.projects.find_one({'project_id': project_id})

    def add_project(self, project_id, reference_populations):
        project = {
            'project_id': project_id,
            'collection_name': 'project_' + ''.join([random.choice(string.digits) for i in range(8)]),
            'reference_populations': reference_populations,
        }
        self._db.projects.insert(project)

        collection = self._get_project_collection(project_id)
        collection.ensure_index([('xpos', 1)])
        collection.ensure_index([('gene_ids', 1), ('xpos', 1)])
        collection.ensure_index([('vep_consequence', 1), ('xpos', 1)])
        collection.ensure_index([('freqs', 1), ('xpos', 1)])

    def _get_project_collection(self, project_id):
        project = self._db.projects.find_one({'project_id': project_id})
        return self._db[project['collection_name']]

    def _get_project_reference_populations(self, project_id):
        project = self._db.projects.find_one({'project_id': project_id})
        return project['reference_populations']

    def add_variants_to_project_from_vcf(self, vcf_file, project_id, indiv_id_list=None):
        """
        This is how variants are loaded
        """
        project_collection = self._get_project_collection(project_id)
        reference_populations = self._get_project_reference_populations(project_id)
        for i, variant in enumerate(vcf_stuff.iterate_vcf(vcf_file, genotypes=True, indiv_id_list=indiv_id_list)):
            if i % 1000 == 0:
                print i
            variant_dict = project_collection.find_one({'xpos': variant.xpos, 'ref': variant.ref, 'alt': variant.alt})
            if not variant_dict:
                self._annotator.annotate_variant(variant, reference_populations)
                variant_dict = variant.toJSON()
                variant_dict['vep_consequence'] = variant.annotation['vep_consequence']
                variant_dict['freqs'] = variant.annotation['freqs']
            else:
                for indiv_id, genotype in variant.get_genotypes():
                    if genotype.num_alt != 0:
                        variant_dict['genotypes'][indiv_id] = genotype._asdict()
            project_collection.save(variant_dict)

    def get_variants(self, project_id, variant_filter=None):

        variant_filter_t = VariantFilter(**(variant_filter if variant_filter else {}))

        db_query = self._make_db_query(None, variant_filter)
        collection = self._get_project_collection(project_id)
        for variant_dict in collection.find(db_query).sort('xpos'):
            variant = Variant.fromJSON(variant_dict)
            if variant_filter is None:
                yield variant
            if passes_variant_filter(variant, variant_filter_t)[0]:
                yield variant

    def get_variants_in_gene(self, project_id, gene_id, variant_filter=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)

        db_query = self._make_db_query(None, modified_variant_filter)
        collection = self._get_project_collection(project_id)

        variants = []
        for variant_dict in collection.find(db_query).hint([('gene_ids', pymongo.ASCENDING), ('xpos', pymongo.ASCENDING)]):
            variant = Variant.fromJSON(variant_dict)
            if passes_variant_filter(variant, modified_variant_filter):
                variants.append(variant)
        variants = sorted(variants, key=lambda v: v.unique_tuple())
        return variants

    def delete_project(self, project_id):
        project = self._db.projects.find_one({'project_id': project_id})
        if project:
            self._get_project_collection(project_id).remove()
        self._db.projects.remove({'project_id': project_id})