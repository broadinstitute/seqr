from collections import defaultdict
from copy import deepcopy
import elasticsearch
from elasticsearch_dsl import Search, Q, MultiSearch
import hashlib
import json
from pyliftover.liftover import LiftOver
from sys import maxsize
from itertools import combinations

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual
from seqr.utils.search.constants import XPOS_SORT_KEY, COMPOUND_HET, RECESSIVE, NEW_SV_FIELD, ALL_DATA_TYPES, X_LINKED_RECESSIVE, MAX_VARIANTS, \
    INHERITANCE_FILTERS, REF_REF, ANY_AFFECTED, AFFECTED, UNAFFECTED, HAS_ALT
from seqr.utils.search.elasticsearch.constants import \
    HAS_ALT_FIELD_KEYS, GENOTYPES_FIELD_KEY, POPULATION_RESPONSE_FIELD_CONFIGS, POPULATIONS, \
    SORTED_TRANSCRIPTS_FIELD_KEY, CORE_FIELDS_CONFIG, NESTED_FIELDS, PREDICTION_FIELDS_RESPONSE_CONFIG, \
    QUERY_FIELD_NAMES, GENOTYPE_QUERY_MAP, HGMD_CLASS_MAP, \
    SORT_FIELDS, MAX_COMPOUND_HET_GENES, MAX_INDEX_NAME_LENGTH, QUALITY_QUERY_FIELDS, \
    GRCH38_LOCUS_FIELD, MAX_SEARCH_CLAUSES, SV_SAMPLE_OVERRIDE_FIELD_CONFIGS, \
    PREDICTION_FIELD_LOOKUP, MULTI_FIELD_PREDICTORS, SPLICE_AI_FIELD, CLINVAR_KEY, HGMD_KEY, CLINVAR_PATH_SIGNIFICANCES, \
    PATH_FREQ_OVERRIDE_CUTOFF, CANONICAL_TRANSCRIPT_FILTER, \
    get_prediction_response_key, XSTOP_FIELD, GENOTYPE_FIELDS, SCREEN_KEY, MAX_INDEX_SEARCHES, PREFILTER_SEARCH_SIZE
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.xpos_utils import get_xpos, MIN_POS, MAX_POS, get_chrom_pos
from seqr.views.utils.json_utils import _to_camel_case

logger = SeqrLogger(__name__)

class EsSearch(object):

    AGGREGATION_NAME = 'compound het'
    CACHED_COUNTS_KEY = 'loaded_variant_counts'

    def __init__(self, samples, genome_version, previous_search_results=None, return_all_queried_families=False, user=None, sort=None, skipped_samples=None):
        from seqr.utils.search.utils import InvalidSearchException
        from seqr.utils.search.elasticsearch.es_utils import get_es_client, InvalidIndexException
        self._client = get_es_client()

        self.samples_by_family_index = defaultdict(lambda: defaultdict(dict))
        for s in samples.select_related('individual__family'):
            self.samples_by_family_index[s.elasticsearch_index][s.individual.family.guid][s.sample_id] = s

        self._set_indices(sorted(list(self.samples_by_family_index.keys())))
        self._set_index_metadata()

        if len(self.samples_by_family_index) > len(self.index_metadata):
            raise InvalidIndexException('Could not find expected indices: {}'.format(
                ', '.join(sorted(set(self._indices) - set(self.index_metadata.keys()), reverse = True))
            ))
        elif len(self.index_metadata) > len(self.samples_by_family_index):
            # Some of the indices are an alias
            self._update_alias_metadata()

        invalid_genome_indices = [
            f"{index} ({meta['genomeVersion']})" for index, meta in self.index_metadata.items()
            if meta['genomeVersion'] != genome_version
        ]
        if invalid_genome_indices:
            raise InvalidSearchException(
                f'The following indices do not have the expected genome version {genome_version}: {", ".join(invalid_genome_indices)}')
        self._genome_version = genome_version
        self._skipped_samples = skipped_samples

        self.indices_by_dataset_type = defaultdict(list)
        for index in self._indices:
            dataset_type = self._get_index_dataset_type(index)
            self.indices_by_dataset_type[dataset_type].append(index)

        self.previous_search_results = {} if previous_search_results is None else previous_search_results
        self._return_all_queried_families = return_all_queried_families
        self._user = user

        self._search = Search()
        self._index_searches = defaultdict(list)
        self._family_individual_affected_status = {}
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._consequence_overrides = {}
        self._filtered_gene_ids = None
        self._paired_index_comp_het = False
        self._no_sample_filters = False
        self._any_affected_sample_filters = False

        self._sort = deepcopy(SORT_FIELDS.get(sort, [])) if sort else None
        if self._sort:
            self._sort_variants(samples)

    @staticmethod
    def _parse_xstop(result):
        xstop = result.pop(XSTOP_FIELD, None)
        if xstop:
            end_chrom, end = get_chrom_pos(xstop)
            if end_chrom != result['chrom'] or end != result['end']:
                if result['svType'] == 'INS':
                    result['svSourceDetail'] = {'chrom': end_chrom}
                else:
                    result.update({
                        'endChrom': end_chrom,
                        'end': end,
                    })

    def _get_index_dataset_type(self, index):
        return self.get_index_metadata_dataset_type(self.index_metadata[index])

    @staticmethod
    def get_index_metadata_dataset_type(index_metadata):
        data_type = index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS)
        if data_type == 'VARIANTS':
            data_type = Sample.DATASET_TYPE_VARIANT_CALLS
        return data_type

    def _set_indices(self, indices):
        self._indices = indices
        self._set_index_name()

    def _set_index_name(self):
        self.index_name = ','.join(sorted(self._indices))
        if len(self.index_name) > MAX_INDEX_NAME_LENGTH:
            alias = hashlib.md5(self.index_name.encode('utf-8')).hexdigest() # nosec
            cache_key = 'index_alias__{}'.format(alias)
            if safe_redis_get_json(cache_key) != self.index_name:
                self._client.indices.update_aliases(body={'actions': [
                    {'add': {'indices': self._indices, 'alias': alias}}
                ]})
                safe_redis_set_json(cache_key, self.index_name)
            self.index_name = alias

    def _set_index_metadata(self):
        from seqr.utils.search.elasticsearch.es_utils import get_index_metadata
        self.index_metadata = get_index_metadata(self.index_name, self._client, include_fields=True)

    def _update_alias_metadata(self):
        additional_meta_indices = set(self.index_metadata.keys()) - set(self._indices)
        aliases = [ind for ind in self._indices if ind not in self.index_metadata]
        alias_map = defaultdict(list)
        if len(aliases) == 1:
            alias_map[aliases[0]] = additional_meta_indices
        else:
            for index, index_aliases in self._client.indices.get_alias(index=','.join(aliases)).items():
                for alias in index_aliases['aliases']:
                    alias_map[alias].append(index)
        self._indices = list(self.index_metadata.keys())
        for alias, alias_indices in alias_map.items():
            alias_samples = self.samples_by_family_index.pop(alias, {})
            for alias_index in alias_indices:
                if not self.samples_by_family_index[alias_index]:
                    self.samples_by_family_index[alias_index] = {}
                self.samples_by_family_index[alias_index].update(alias_samples)

    def _set_family_affected_status(self, inheritance_filter):
        for family_samples in list(self.samples_by_family_index.values()):
            for family_guid, samples_by_id in family_samples.items():
                individual_affected_status = _get_family_affected_status(samples_by_id, inheritance_filter)
                if family_guid not in self._family_individual_affected_status:
                    self._family_individual_affected_status[family_guid] = {}
                self._family_individual_affected_status[family_guid].update(individual_affected_status)

    def _dataset_type_indices(self, dataset_type):
        new_indices = self.indices_by_dataset_type[dataset_type]
        if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
            new_indices += self.indices_by_dataset_type[Sample.DATASET_TYPE_MITO_CALLS]
        return new_indices

    def _sort_variants(self, sample_data):
        main_sort_dict = self._sort[0] if len(self._sort) and isinstance(self._sort[0], dict) else None

        # Add parameters to scripts
        if main_sort_dict and main_sort_dict.get('_script', {}).get('script', {}).get('params'):
            called_params = None
            for key, val_func in self._sort[0]['_script']['script']['params'].items():
                if callable(val_func):
                    self._sort[0]['_script']['script']['params'][key] = val_func(sample_data)
                    called_params = self._sort[0]['_script']['script']['params']
            if called_params:
                for sort_dict in self._sort[1:]:
                    sort_dict['_script']['script']['params'] = called_params


        # Add unmapped_type
        if main_sort_dict and 'unmapped_type' in list(main_sort_dict.values())[0]:
            sort_field = list(main_sort_dict.keys())[0]
            field_type = next((
                metadata['fields'][sort_field] for metadata in self.index_metadata.values()
                if metadata['fields'].get(sort_field)
            ), 'double')
            if field_type == 'keyword':
                self._sort[0][sort_field]['unmapped_type'] = field_type
                self._sort[0][sort_field].pop('numeric_type')

        if XPOS_SORT_KEY not in self._sort:
            self._sort.append(XPOS_SORT_KEY)

        # always final sort on variant ID to keep different variants at the same position grouped properly
        if 'variantId' not in self._sort:
            self._sort.append('variantId')

        self._search = self._search.sort(*self._sort)

    def _filter(self, new_filter):
        self._search = self._search.filter(new_filter)
        return self

    def filter_variants(self, inheritance_mode=None, inheritance_filter=None, genes=None, intervals=None, rs_ids=None, variant_ids=None, exclude_locations=False,
                        frequencies=None, pathogenicity=None, in_silico=None, annotations=None, annotations_secondary=None,
                        quality_filter=None, custom_query=None, skip_genotype_filter=False, dataset_type=None, secondary_dataset_type=None, **kwargs):

        self._filter_custom(custom_query)

        self._filter_by_location(genes, intervals, variant_ids, rs_ids, exclude_locations)

        self._parse_annotation_overrides(annotations, pathogenicity)

        self._filter_by_frequency(frequencies)

        self._filter_by_in_silico(in_silico)

        if quality_filter and quality_filter.get('vcf_filter') is not None:
            self._filter(~Q('exists', field='filters'))

        inheritance_filter = inheritance_filter or {}

        quality_affected_only = quality_filter and quality_filter.get('affected_only')
        if inheritance_mode or inheritance_filter or quality_affected_only:
            self._set_family_affected_status(inheritance_filter)

        quality_filters_by_family = self._get_quality_filters_by_family(quality_filter, quality_affected_only)

        comp_het_dataset_type = dataset_type
        if dataset_type != secondary_dataset_type:
            comp_het_dataset_type = None
        if dataset_type == ALL_DATA_TYPES:
            dataset_type = None
            comp_het_dataset_type = None

        has_comp_het_search = inheritance_mode in {RECESSIVE, COMPOUND_HET} and not self.previous_search_results.get('grouped_results')
        if has_comp_het_search:
            self._filter_compound_hets(quality_filters_by_family, annotations_secondary, comp_het_dataset_type)
            if inheritance_mode == COMPOUND_HET:
                return

        self._filter_by_annotations()
        if skip_genotype_filter and not inheritance_mode:
            return

        self._filter_by_genotype(inheritance_mode, inheritance_filter, quality_filters_by_family, dataset_type)

    def _parse_annotation_overrides(self, annotations, pathogenicity):
        clinvar_terms, hgmd_classes = _parse_pathogenicity_filter(pathogenicity or {})

        annotations = {k: v for k, v in (annotations or {}).items() if v}

        # Temporary code, remove it after all the SV indices are reloaded
        if annotations.get('structural_consequence'):
            if 'MSV_EXON_OVERLAP' in annotations['structural_consequence']:
                annotations['structural_consequence'].append('MSV_EXON_OVR')
            if 'INTRAGENIC_EXON_DUP' in annotations['structural_consequence']:
                annotations['structural_consequence'].append('DUP_LOF')

        new_svs = bool(annotations.pop(NEW_SV_FIELD, False))
        splice_ai = annotations.pop(SPLICE_AI_FIELD, None)
        screen = annotations.pop(SCREEN_KEY, None)
        self._allowed_consequences = sorted({ann for anns in annotations.values() for ann in anns})
        if clinvar_terms:
            self._consequence_overrides[CLINVAR_KEY] = clinvar_terms
        if hgmd_classes:
            self._consequence_overrides[HGMD_KEY] = hgmd_classes
        if splice_ai:
            self._consequence_overrides[SPLICE_AI_FIELD] = float(splice_ai)
        if screen:
            self._consequence_overrides[SCREEN_KEY] = screen
        if new_svs:
            self._consequence_overrides[NEW_SV_FIELD] = new_svs

    def _filter_by_location(self, genes, intervals, variant_ids, rs_ids, exclude_locations):
        if genes or intervals:
            self._filter(_location_filter(genes, intervals, exclude_locations))
            if genes and not exclude_locations:
                self._filtered_gene_ids = set(genes.keys())
        elif variant_ids:
            self.filter_by_variant_ids(variant_ids)
        elif rs_ids:
            self._filter(Q('terms', rsid=rs_ids))

    def _filter_custom(self, custom_query):
        if custom_query:
            if not isinstance(custom_query, list):
                custom_query = [custom_query]
            for q_dict in custom_query:
                self._filter(Q(q_dict))

    def _filter_by_in_silico(self, in_silico_filters):
        in_silico_filters = deepcopy(in_silico_filters or {})
        require_score = in_silico_filters.pop('requireScore', False)
        in_silico_filters = {k: v for k, v in in_silico_filters.items() if v is not None and len(v) != 0}
        if in_silico_filters:
            self._filter(self._in_silico_filter(in_silico_filters, require_score=require_score))

    def _in_silico_filter(self, in_silico_filters, require_score):
        prediction_key_lookup = {
            in_silico_filter: PREDICTION_FIELD_LOOKUP.get(in_silico_filter.lower(), in_silico_filter)
            for in_silico_filter in in_silico_filters.keys()
        }

        multi_predictor_fields = {
            in_silico_filter: MULTI_FIELD_PREDICTORS[in_silico_filter.lower()]
            for in_silico_filter in in_silico_filters.keys() if in_silico_filter.lower() in MULTI_FIELD_PREDICTORS
        }
        if multi_predictor_fields:
            all_fields = set()
            for metadata in self.index_metadata.values():
                all_fields.update(metadata['fields'])
            index_fields = {
                k: next(field for field in fields if field in all_fields)
                for k, fields in multi_predictor_fields.items()
            }
            prediction_key_lookup.update(index_fields)

        return _in_silico_filter({prediction_key_lookup[k]: v for k, v in in_silico_filters.items()}, require_score)

    def _filter_by_frequency(self, frequencies):
        frequencies = {pop: v for pop, v in (frequencies or {}).items() if pop in POPULATIONS}
        if not frequencies:
            return

        path_filter = self._get_clinvar_pathogenic_override_filter()
        path_override = path_filter is not None and any(
            freqs.get('af') or 1 < PATH_FREQ_OVERRIDE_CUTOFF for freqs in frequencies.values())

        q = Q()
        path_q = Q()
        for pop, freqs in sorted(frequencies.items()):
            if freqs.get('af') is not None:
                filter_field = next(
                    (field_key for field_key in POPULATIONS[pop]['filter_AF']
                     if any(field_key in index_metadata['fields'] for index_metadata in self.index_metadata.values())),
                    POPULATIONS[pop]['AF'])
                q &= _pop_freq_filter(filter_field, freqs['af'])
                if path_override:
                    path_q &= _pop_freq_filter(filter_field, max(freqs['af'], PATH_FREQ_OVERRIDE_CUTOFF))
            elif freqs.get('ac') is not None:
                q &= _pop_freq_filter(POPULATIONS[pop]['AC'], freqs['ac'])

            if freqs.get('hh') is not None:
                q &= _pop_freq_filter(POPULATIONS[pop]['Hom'], freqs['hh'])
                q &= _pop_freq_filter(POPULATIONS[pop]['Hemi'], freqs['hh'])

        if path_override:
            q |= (path_filter & path_q)

        self._filter(q)

    def _get_clinvar_pathogenic_override_filter(self):
        clinvar_path_terms = [
            f for f in self._consequence_overrides.get(CLINVAR_KEY, []) if f in CLINVAR_PATH_SIGNIFICANCES
        ]
        if clinvar_path_terms:
            return _pathogenicity_filter(clinvar_path_terms)
        return None

    def _get_annotation_override_filter(self):
        filters = []
        pathogenicity_filter = _pathogenicity_filter(
            self._consequence_overrides.get(CLINVAR_KEY), self._consequence_overrides.get(HGMD_KEY),
        )
        if pathogenicity_filter:
            filters.append(pathogenicity_filter)
        splice_ai = self._consequence_overrides.get(SPLICE_AI_FIELD)
        if splice_ai:
            filters.append(self._in_silico_filter({SPLICE_AI_FIELD: splice_ai}, require_score=True))
        screen = self._consequence_overrides.get(SCREEN_KEY)
        if screen:
            filters.append(Q('terms', screen_region_type=screen))

        if not filters:
            return None
        return _or_filters(filters)

    def _filter_by_annotations(self):
        annotation_override_filter = self._get_annotation_override_filter()
        new_svs = self._consequence_overrides.get(NEW_SV_FIELD)

        if self._allowed_consequences:
            consequences_filter = _annotations_filter(self._allowed_consequences)

            if annotation_override_filter:
                # Pathogencicity and transcript consequences act as "OR" filters instead of the usual "AND"
                consequences_filter |= annotation_override_filter
            self._filter(consequences_filter)
        elif annotation_override_filter and not new_svs:
            self._filter(annotation_override_filter)

    def filter_by_variant_ids(self, variant_ids):
        self._filter(Q('terms', variantId=variant_ids))
        return self

    def _filter_by_genotype(self, inheritance_mode, inheritance_filter, quality_filters_by_family, dataset_type):
        has_inheritance_filter = inheritance_filter or inheritance_mode
        all_sample_search = (not quality_filters_by_family) and (inheritance_mode == ANY_AFFECTED or not has_inheritance_filter)
        no_filter_indices = set()

        indices = self._dataset_type_indices(dataset_type) if dataset_type else self._indices
        for index in indices:
            family_samples_by_id = self.samples_by_family_index[index]
            index_fields = self.index_metadata[index]['fields']

            if all_sample_search:
                index_skipped_sample_count = sum([s.elasticsearch_index == index for s in self._skipped_samples or []])
                search_sample_count = sum(len(samples) for samples in family_samples_by_id.values()) + index_skipped_sample_count
                index_sample_count = Sample.objects.filter(elasticsearch_index=index, is_active=True).count()
                if search_sample_count == index_sample_count:
                    if inheritance_mode == ANY_AFFECTED:
                        sample_ids = []
                        for family_guid, samples_by_id in family_samples_by_id.items():
                            sample_ids += [
                                sample_id for sample_id, sample in samples_by_id.items()
                                if self._family_individual_affected_status[family_guid][sample.individual.guid] == Individual.AFFECTED_STATUS_AFFECTED]
                        self._index_searches[index].append(self._search.filter(_any_affected_sample_filter(sample_ids)))
                        self._any_affected_sample_filters = True
                    else:
                        # If searching across all families in an index with no inheritance mode we do not need to explicitly
                        # filter on inheritance, as all variants have some inheritance for at least one family
                        self._no_sample_filters = True
                        no_filter_indices.add(index)
                    continue

            genotypes_qs = [
                self._get_family_sample_query(
                    family_guid, family_samples_by_id, quality_filters_by_family,
                    index_fields, inheritance_mode, inheritance_filter
                ) for family_guid in sorted(family_samples_by_id.keys())
            ]
            if len(genotypes_qs) > MAX_SEARCH_CLAUSES:
                self._index_searches[index].append(self._search.filter(_or_filters(genotypes_qs[:MAX_SEARCH_CLAUSES])))
                genotypes_qs = genotypes_qs[MAX_SEARCH_CLAUSES:]

            self._index_searches[index].append(self._search.filter(_or_filters(genotypes_qs)))

        if no_filter_indices and self._index_searches:
            for index in no_filter_indices:
                self._index_searches[index].append(self._search)

    def _get_family_sample_query(self, family_guid, family_samples_by_id, quality_filters_by_family, index_fields, inheritance_mode, inheritance_filter):
        samples_by_id = family_samples_by_id[family_guid]
        affected_status = self._family_individual_affected_status.get(family_guid)

        # Filter samples by inheritance
        if inheritance_mode == ANY_AFFECTED:
            # Only return variants where at least one of the affected samples has an alt allele
            sample_ids = [sample_id for sample_id, sample in samples_by_id.items()
                          if affected_status[sample.individual.guid] == Individual.AFFECTED_STATUS_AFFECTED]
            family_samples_q = _any_affected_sample_filter(sample_ids)
        elif inheritance_filter or inheritance_mode:
            if inheritance_mode:
                inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

            family_samples_q = _family_genotype_inheritance_filter(
                inheritance_mode, inheritance_filter, samples_by_id, affected_status, index_fields,
            )
        else:
            # If no inheritance specified only return variants where at least one of the requested samples has an alt allele
            family_samples_q = _any_affected_sample_filter(list(samples_by_id.keys()))

        return _named_family_sample_q(family_samples_q, family_guid, quality_filters_by_family)

    def _filter_compound_hets(self, quality_filters_by_family, annotations_secondary, dataset_type):
        comp_het_consequences = set(self._allowed_consequences)
        annotation_override_filter = self._get_annotation_override_filter()
        if annotations_secondary:
            self._allowed_consequences_secondary = sorted({ann for anns in annotations_secondary.values() for ann in anns})
            comp_het_consequences.update(self._allowed_consequences_secondary)

        annotation_filter = _annotations_filter(comp_het_consequences)
        if annotation_override_filter:
            annotation_filter |= annotation_override_filter
        comp_het_search = self._search.filter(annotation_filter)

        comp_het_qs_by_index = defaultdict(list)
        if dataset_type or len(self._indices) <= 1:
            indices = self.indices_by_dataset_type[dataset_type] if dataset_type else self._indices
            for index in sorted(indices, reverse=True):
                family_samples_by_id = self.samples_by_family_index[index]
                index_fields = self.index_metadata[index]['fields']

                for family_guid, samples_by_id in sorted(family_samples_by_id.items()):
                    affected_status = self._family_individual_affected_status[family_guid]
                    family_samples_q = _family_genotype_inheritance_filter(
                        COMPOUND_HET, INHERITANCE_FILTERS[COMPOUND_HET], samples_by_id, affected_status, index_fields,
                    )
                    samples_q = _named_family_sample_q(family_samples_q, family_guid, quality_filters_by_family)
                    comp_het_qs_by_index[index].append(samples_q)
        else:
            self._get_paired_indices_comp_het_queries(comp_het_qs_by_index, quality_filters_by_family)

        for index, compound_het_qs in comp_het_qs_by_index.items():
            comp_het_qs_list = [
                compound_het_qs[:MAX_SEARCH_CLAUSES], compound_het_qs[MAX_SEARCH_CLAUSES:]
            ] if len(compound_het_qs) > MAX_SEARCH_CLAUSES else [compound_het_qs]
            for compound_het_q in comp_het_qs_list:
                compound_het_search = comp_het_search.filter(_or_filters(compound_het_q))
                compound_het_search.aggs.bucket(
                    'genes', 'terms', field='geneIds', min_doc_count=2, size=MAX_COMPOUND_HET_GENES + 1
                ).metric(
                    'vars_by_gene', 'top_hits', size=100, sort=self._sort, _source=QUERY_FIELD_NAMES
                )
                self._index_searches[index].append(compound_het_search)

    def _get_paired_indices_comp_het_queries(self, comp_het_qs_by_index, quality_filters_by_family):
        paired_index_families = defaultdict(dict)
        sv_indices = self.indices_by_dataset_type[Sample.DATASET_TYPE_SV_CALLS]
        variant_indices = self.indices_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS]
        if sv_indices and variant_indices:
            for sv_index in sv_indices:
                sv_families = set(self.samples_by_family_index[sv_index].keys())
                for var_index in variant_indices:
                    overlapping_families = sv_families & set(self.samples_by_family_index[var_index].keys())
                    if overlapping_families:
                        paired_index_families[sv_index].update({var_index: overlapping_families})
                        paired_index_families[var_index].update({sv_index: overlapping_families})

        seen_paired_indices = set()
        for index in sorted(self._indices, reverse=True):
            family_samples_by_id = self.samples_by_family_index[index]
            index_fields = self.index_metadata[index]['fields']
            seen_paired_indices.add(index)

            paired_families = {}
            for pair_index, families in paired_index_families[index].items():
                paired_families.update({family: pair_index for family in families})

            for family_guid in sorted(family_samples_by_id.keys()):
                paired_index = paired_families.get(family_guid)
                if paired_index and paired_index in seen_paired_indices:
                    continue

                samples_by_id = family_samples_by_id[family_guid]

                affected_status = self._family_individual_affected_status[family_guid]
                inheritance_filters = self._comp_het_inheritance_filter(index, paired_index)
                family_samples_q = _family_genotype_inheritance_filter(
                    COMPOUND_HET, inheritance_filters, samples_by_id, affected_status, index_fields,
                )

                family_index = index
                if paired_index:
                    self._paired_index_comp_het = True
                    pair_index_fields = self.index_metadata[paired_index]['fields']
                    pair_samples_by_id = self.samples_by_family_index[paired_index][family_guid]
                    pair_inheritance_filters = self._comp_het_inheritance_filter(paired_index, True)
                    family_samples_q |= _family_genotype_inheritance_filter(
                        COMPOUND_HET, pair_inheritance_filters, pair_samples_by_id, affected_status, pair_index_fields,
                    )
                    family_index = ','.join(sorted([index, paired_index]))

                samples_q = _named_family_sample_q(family_samples_q, family_guid, quality_filters_by_family)
                comp_het_qs_by_index[family_index].append(samples_q)

    def _comp_het_inheritance_filter(self, index, has_paired_index):
        if has_paired_index and self._get_index_dataset_type(index) == Sample.DATASET_TYPE_VARIANT_CALLS:
            # SNPs in trans with deletions may be called as hom alt instead of ref alt
            return {
                AFFECTED: HAS_ALT,
                UNAFFECTED: INHERITANCE_FILTERS[COMPOUND_HET][UNAFFECTED],
            }
        return INHERITANCE_FILTERS[COMPOUND_HET]

    def search(self, page=1, num_results=100):
        indices = self._indices

        logger.info('Searching in elasticsearch indices: {}'.format(', '.join(indices)), self._user)

        is_single_search, search_kwargs = self._should_execute_single_search(page=page, num_results=num_results)

        if is_single_search:
            return self._execute_single_search(**search_kwargs)
        elif not self._index_searches:
            return self._execute_single_search(**search_kwargs)
        else:
            return self._execute_multi_search(**search_kwargs)

    def _is_single_search(self):
        return len(self._indices) == 1 and len(self._index_searches) < 2 and \
               len(self._index_searches.get(self._indices[0], [])) <= 1

    def _should_execute_single_search(self, page=1, num_results=100):
        is_single_search = self._is_single_search()
        num_loaded = len(self.previous_search_results.get('all_results', []))

        if is_single_search and not self.previous_search_results.get('grouped_results'):
            start_index = None
            if (page - 1) * num_results < num_loaded:
                start_index = num_loaded
            return True, {'page': page, 'num_results': num_results, 'start_index': start_index}
        elif not self._index_searches:
            # If doing all project-families all inheritance search, do it as a single query
            # Load all variants, do not skip pages
            num_loaded += self.previous_search_results.get('duplicate_doc_count', 0)
            if num_loaded >= (page - 1) * num_results:
                start_index = num_loaded
            else:
                start_index = 0
            return True, {'page': page, 'num_results': num_results, 'start_index': start_index, 'deduplicate': True}
        else:
            return False, {'page': page, 'num_results': num_results}

    def _execute_single_search(self, page=1, num_results=100, start_index=None, deduplicate=False, **kwargs):
        num_results_for_search = num_results * len(self._indices) if deduplicate else num_results
        if num_results_for_search > MAX_VARIANTS and deduplicate:
            num_results_for_search = MAX_VARIANTS
        searches, log_messages = self._get_paginated_searches(
            self.index_name, page=page, num_results=num_results_for_search, start_index=start_index
        )
        logger.info(log_messages[0], self._user)
        search = searches[0]
        response = self._execute_search(search)
        parsed_response = self._parse_response(response)
        return self._process_single_search_response(
            parsed_response, page=page, num_results=num_results, deduplicate=deduplicate, **kwargs)

    def _process_single_search_response(self, parsed_response, page=1, num_results=100, deduplicate=False, **kwargs):
        variant_results, total_results, is_compound_het, _ = parsed_response
        self.previous_search_results['total_results'] = total_results

        results_start_index = (page - 1) * num_results
        if is_compound_het:
            variant_results = _sort_compound_hets(variant_results)
            self.previous_search_results['grouped_results'] = variant_results
            end_index = min(results_start_index + num_results, total_results)
            return get_compound_het_page(variant_results, results_start_index, end_index)

        if deduplicate:
            variant_results = self._deduplicate_results(variant_results)

        # Only save contiguous pages of results:
        previous_all_results = self.previous_search_results.get('all_results', [])
        if len(previous_all_results) >= results_start_index:
            self.previous_search_results['all_results'] = self.previous_search_results.get('all_results', []) + variant_results
            variant_results = self.previous_search_results['all_results'][results_start_index:]

        return variant_results[:num_results]

    def _execute_multi_search(self, **kwargs):
        indices = sorted(self._index_searches.keys(), reverse = True) or self._indices

        if self.CACHED_COUNTS_KEY and not self.previous_search_results.get(self.CACHED_COUNTS_KEY):
            self.previous_search_results[self.CACHED_COUNTS_KEY] = {}

        paginated_index_searches = {}
        index_logs = {}
        for index_name in indices:
            start_index = 0
            if self.CACHED_COUNTS_KEY:
                if self.previous_search_results[self.CACHED_COUNTS_KEY].get(index_name):
                    index_total = self.previous_search_results[self.CACHED_COUNTS_KEY][index_name]['total']
                    start_index = self.previous_search_results[self.CACHED_COUNTS_KEY][index_name]['loaded']
                    if start_index >= index_total:
                        continue
                else:
                    self.previous_search_results[self.CACHED_COUNTS_KEY][index_name] = {'loaded': 0, 'total': 0}

            searches, log_messages = self._get_paginated_searches(index_name, start_index=start_index, **kwargs)
            if searches:
                paginated_index_searches[index_name] = searches
                index_logs[index_name] = log_messages

        if len(paginated_index_searches) > MAX_INDEX_SEARCHES:
            index_possible_variants, all_inheritance_response = self._get_possible_hit_indices()
            if index_possible_variants:
                paginated_index_searches = {
                    index_name: [
                        search.query('ids', values=possible_ids) for search in paginated_index_searches[index_name]
                    ] for index_name, possible_ids in index_possible_variants.items()
                    if paginated_index_searches.get(index_name)
                }
            elif all_inheritance_response is not None:
                # all inheritance search succeeded but has no results, return an empty response
                return self._process_single_search_response(self._parse_response(all_inheritance_response), **kwargs)

        ms = MultiSearch()
        for index_name, searches in paginated_index_searches.items():
            for search in searches:
                ms = ms.add(search)
            for message in index_logs[index_name]:
                logger.info(message, self._user)

        responses = self._execute_search(ms) if ms._searches else []
        parsed_responses = [self._parse_response(response) for response in responses]
        return self._process_multi_search_responses(parsed_responses, **kwargs)

    def _get_possible_hit_indices(self):
        no_inheritance_search = self._search.index(self.index_name).source('')[:PREFILTER_SEARCH_SIZE]
        response = no_inheritance_search.using(self._client).execute()
        if response.hits.total['value'] > len(response.hits):
            return None, None

        index_possible_variants = defaultdict(list)
        for hit in response.hits:
            index_possible_variants[hit.meta.index].append(hit.meta.id)

        logger.info(f'Filtering search to {len(index_possible_variants)} indices with possible hits', self._user)
        return index_possible_variants, response

    def _process_multi_search_responses(self, parsed_responses, page=1, num_results=100):
        new_results = []
        compound_het_results = self.previous_search_results.get('compound_het_results', [])
        loaded_counts = defaultdict(lambda: defaultdict(int))
        for response_hits, response_total, is_compound_het, index_name in parsed_responses:
            if not response_hits:
                continue

            if is_compound_het:
                compound_het_results += response_hits
                loaded_count = response_total
                index_name = '{}_compound_het'.format(index_name)
                if not self.previous_search_results['loaded_variant_counts'].get(index_name):
                    self.previous_search_results['loaded_variant_counts'][index_name] = {'total': 0, 'loaded': 0}
            else:
                new_results += response_hits
                loaded_count = len(response_hits)

            loaded_counts[index_name]['total'] += response_total
            loaded_counts[index_name]['loaded'] += loaded_count

        for index_name, counts in loaded_counts.items():
            self.previous_search_results['loaded_variant_counts'][index_name]['total'] = counts['total']
            self.previous_search_results['loaded_variant_counts'][index_name]['loaded'] += counts['loaded']

        total_results = sum(
            counts['total'] for counts in self.previous_search_results['loaded_variant_counts'].values())
        self.previous_search_results['total_results'] = total_results

        # combine new results with unsorted previously loaded results to correctly sort/paginate
        all_loaded_results = self.previous_search_results.get('all_results', [])
        new_results += self.previous_search_results.get('variant_results', [])

        new_results = sorted(new_results, key=lambda variant: variant['_sort'])
        variant_results = self._deduplicate_results(new_results)

        if compound_het_results or self.previous_search_results.get('grouped_results'):
            if compound_het_results:
                compound_het_results = self._deduplicate_compound_het_results(compound_het_results)
                compound_het_results = _sort_compound_hets(compound_het_results)
            loaded_results = sum(
                counts['loaded'] for counts in self.previous_search_results['loaded_variant_counts'].values())
            return self._process_compound_hets(
                compound_het_results, variant_results, num_results, all_loaded=loaded_results == total_results)
        else:
            end_index = num_results * page
            num_loaded = num_results * page - len(all_loaded_results)
            self.previous_search_results['all_results'] = all_loaded_results + variant_results[:num_loaded]
            self.previous_search_results['variant_results'] = variant_results[num_loaded:]
            return self.previous_search_results['all_results'][end_index-num_results:end_index]

    def _parse_response(self, response):
        index_name = response.hits[0].meta.index if response.hits else None
        if hasattr(response.aggregations, 'genes') and response.hits:
            response_hits, response_total = self._parse_compound_het_response(response)
            return response_hits, response_total, True, index_name

        response_total = response.hits.total['value']
        logger.info('Total hits: {} ({} seconds)'.format(response_total, response.took / 1000.0), self._user)
        return [self._parse_hit(hit) for hit in response], response_total, False, index_name


    def _parse_hit(self, raw_hit):
        hit = {k: raw_hit[k] for k in QUERY_FIELD_NAMES if k in raw_hit}
        index_name = raw_hit.meta.index
        index_family_samples = self.samples_by_family_index[index_name]
        data_type = self._get_index_dataset_type(index_name)

        family_guids, genotypes = self._parse_genotypes(raw_hit, hit, index_family_samples, data_type)

        result = _get_field_values(hit, CORE_FIELDS_CONFIG, format_response_key=str)
        result.update({
            field_name: _get_field_values(hit, fields, lookup_field_prefix=field_name)
            for field_name, fields in NESTED_FIELDS.items()
        })
        if hasattr(raw_hit.meta, 'sort'):
            result['_sort'] = [_parse_es_sort(sort, self._sort[i]) for i, sort in enumerate(raw_hit.meta.sort)]

        result['genomeVersion'] = self._genome_version
        if self._genome_version == GENOME_VERSION_GRCh38:
            self._add_liftover(result, hit)
        self._parse_xstop(result)
        result[CLINVAR_KEY]['version'] = self.index_metadata[index_name].get('clinvar_version')

        # If an SV has genotype-specific coordinates that differ from the main coordinates, use those
        if data_type == Sample.DATASET_TYPE_SV_CALLS and genotypes:
            self._set_sv_genotype_coords(genotypes, result)

        populations = {
            population: _get_field_values(
                hit, POPULATION_RESPONSE_FIELD_CONFIGS, format_response_key=lambda key: key.lower(),
                lookup_field_prefix=population,
                existing_fields=self.index_metadata[index_name]['fields'],
                get_addl_fields=lambda field: pop_config[field] if isinstance(pop_config[field], list) else [pop_config[field]],
                skip_fields=[field for field, val in pop_config.items() if val is None],
            )
            for population, pop_config in POPULATIONS.items()
        }

        sorted_transcripts = [
            {_to_camel_case(k): v for k, v in transcript.to_dict().items()}
            for transcript in hit[SORTED_TRANSCRIPTS_FIELD_KEY] or []
        ]

        # Temporary code, remove it after all the SV indices are reloaded
        for trans in sorted_transcripts:
            if trans.get('majorConsequence'):
                if trans['majorConsequence'] == 'MSV_EXON_OVR':
                    trans['majorConsequence'] = 'MSV_EXON_OVERLAP'
                elif trans['majorConsequence'] == 'DUP_LOF':
                    trans['majorConsequence'] = 'INTRAGENIC_EXON_DUP'

        transcripts = defaultdict(list)
        for transcript in sorted_transcripts:
            if transcript['geneId']:
                transcripts[transcript['geneId']].append(transcript)
        gene_ids = result.pop('geneIds', None)
        if gene_ids:
            transcripts = {gene_id: ts for gene_id, ts in transcripts.items() if gene_id in gene_ids}
        main_transcript_id, selected_main_transcript_id = self._get_main_transcript(sorted_transcripts)

        result.update({
            'familyGuids': sorted(family_guids),
            'genotypes': genotypes,
            'mainTranscriptId': main_transcript_id,
            'selectedMainTranscriptId': selected_main_transcript_id,
            'populations': populations,
            'predictions': _get_field_values(
                hit, PREDICTION_FIELDS_RESPONSE_CONFIG, format_response_key=get_prediction_response_key,
                get_addl_fields=lambda field: MULTI_FIELD_PREDICTORS.get(field, [])
            ),
            'transcripts': dict(transcripts),
        })
        return result

    def _parse_genotypes(self, raw_hit, hit, index_family_samples, data_type):
        if hasattr(raw_hit.meta, 'matched_queries'):
            family_guids = list(raw_hit.meta.matched_queries)
        elif self._return_all_queried_families:
            family_guids = list(index_family_samples.keys())
        else:
            # Searches for all inheritance and all families do not filter on inheritance so there are no matched_queries
            alt_allele_samples = set()
            for alt_samples_field in HAS_ALT_FIELD_KEYS:
                if alt_samples_field in hit:
                    alt_allele_samples.update(hit[alt_samples_field])

            if self._any_affected_sample_filters:
                # If using the any inheritance filter only include matched families
                def _is_matched_sample(family_guid, sample):
                    return self._family_individual_affected_status[family_guid][sample.individual.guid] == \
                           Individual.AFFECTED_STATUS_AFFECTED
            else:
                _is_matched_sample = lambda *args: True

            family_guids = [family_guid for family_guid, samples_by_id in index_family_samples.items()
                if any(sample_id in alt_allele_samples and _is_matched_sample(family_guid, sample)
                       for sample_id, sample in samples_by_id.items())]

        genotypes = {}
        genotype_fields_config = GENOTYPE_FIELDS[data_type]
        for family_guid in family_guids:
            samples_by_id = index_family_samples[family_guid]
            for genotype_hit in hit[GENOTYPES_FIELD_KEY]:
                sample = samples_by_id.get(genotype_hit['sample_id'])
                if sample:
                    genotype_hit['sample_type'] = sample.sample_type
                    genotypes[sample.individual.guid] = _get_field_values(genotype_hit, genotype_fields_config)

            if len(samples_by_id) != len(genotypes) and data_type == Sample.DATASET_TYPE_SV_CALLS:
                # Family members with no variants are not included in the SV index
                for sample_id, sample in samples_by_id.items():
                    if sample.individual.guid not in genotypes:
                        genotypes[sample.individual.guid] = _get_field_values(
                            {'sample_id': sample_id}, genotype_fields_config)
                        genotypes[sample.individual.guid]['isRef'] = True
                        genotypes[sample.individual.guid]['cn'] = \
                            1 if hit['contig'] == 'X' and sample.individual.sex == Individual.SEX_MALE else 2

        return family_guids, genotypes

    @classmethod
    def _set_sv_genotype_coords(cls, genotypes, result):
        # If an SV has genotype-specific coordinates that differ from the main coordinates, use those
        if any(not gen.get('isRef') for gen in genotypes.values()) and all(
                (gen.get('isRef') or gen.get('start') or gen.get('end')) for gen in genotypes.values()):
            for field, conf in SV_SAMPLE_OVERRIDE_FIELD_CONFIGS.items():
                gen_field = conf.get('genotype_field', field)
                val = conf['select_val']([
                    gen.get(gen_field) or result.get(field) for gen in genotypes.values() if not gen.get('isRef')
                ])
                if val != result.get(field):
                    result[field] = val
                    if field == 'pos':
                        result['xpos'] = get_xpos(result['chrom'], val)

            for gen in genotypes.values():
                for field, conf in SV_SAMPLE_OVERRIDE_FIELD_CONFIGS.items():
                    gen_field = conf.get('genotype_field', field)
                    compare_func = conf.get('equal') or (lambda a, b: a == b)
                    if compare_func(gen.get(gen_field), result.get(field)):
                        gen[gen_field] = None

    def _get_main_transcript(self, sorted_transcripts):
        main_transcript_id = sorted_transcripts[0]['transcriptId'] \
            if len(sorted_transcripts) and 'transcriptRank' in sorted_transcripts[0] else None

        selected_main_transcript_id = None
        if main_transcript_id and (self._filtered_gene_ids or self._allowed_consequences):
            gene_transcripts = [
                t for t in sorted_transcripts if t.get('geneId') in self._filtered_gene_ids
            ] if  self._filtered_gene_ids else sorted_transcripts

            selected_main_transcript_id = gene_transcripts[0].get('transcriptId')
            if self._allowed_consequences:
                consequence_transcript_id = next((
                    t.get('transcriptId') for t in gene_transcripts if
                    self._is_matched_transcript(t, self._allowed_consequences)), None)
                if not consequence_transcript_id and self._allowed_consequences_secondary:
                    consequence_transcript_id = next((
                        t.get('transcriptId') for t in gene_transcripts if self._is_matched_transcript(t, self._allowed_consequences_secondary)
                    ), None)
                selected_main_transcript_id = consequence_transcript_id or selected_main_transcript_id
            if selected_main_transcript_id == main_transcript_id:
                selected_main_transcript_id = None

        return main_transcript_id, selected_main_transcript_id

    @staticmethod
    def _is_matched_transcript(t, allowed_consequences):
        is_match = t.get('majorConsequence') in allowed_consequences
        if CANONICAL_TRANSCRIPT_FILTER in allowed_consequences and t.get('canonical') and \
                t.get('majorConsequence') == 'non_coding_transcript_exon_variant':
            is_match = True
        return is_match

    @staticmethod
    def _add_liftover(result, hit):
        lifted_over_genome_version = None
        lifted_over_chrom = None
        lifted_over_pos = None
        grch37_locus = hit.get(GRCH38_LOCUS_FIELD, None)
        if grch37_locus:
            lifted_over_genome_version = GENOME_VERSION_GRCh37
            lifted_over_chrom = grch37_locus['contig']
            lifted_over_pos = grch37_locus['position']
        else:
            # TODO once all projects are lifted in pipeline, remove this code (https://github.com/broadinstitute/seqr/issues/1010)
            liftover_grch38_to_grch37 = _liftover_grch38_to_grch37()
            if liftover_grch38_to_grch37:
                grch37_coord = liftover_grch38_to_grch37.convert_coordinate(
                    'chr{}'.format(hit['contig'].lstrip('chr')), int(hit['start'])
                )
                if grch37_coord and grch37_coord[0]:
                    lifted_over_genome_version = GENOME_VERSION_GRCh37
                    lifted_over_chrom = grch37_coord[0][0].lstrip('chr')
                    lifted_over_pos = grch37_coord[0][1]
        result.update({
            'liftedOverGenomeVersion': lifted_over_genome_version,
            'liftedOverChrom': lifted_over_chrom,
            'liftedOverPos': lifted_over_pos,
        })

    def _parse_compound_het_response(self, response):
        if len(response.aggregations.genes.buckets) > MAX_COMPOUND_HET_GENES:
            from seqr.utils.search.utils import InvalidSearchException
            raise InvalidSearchException('This search returned too many compound heterozygous variants. Please add stricter filters')

        family_unaffected_individual_guids = {
            family_guid: {individual_guid for individual_guid, affected_status in individual_affected_status.items() if
                          affected_status == Individual.AFFECTED_STATUS_UNAFFECTED}
            for family_guid, individual_affected_status in self._family_individual_affected_status.items()
        }

        self._allowed_consequences += self._consequence_overrides.keys()
        if self._allowed_consequences_secondary:
            self._allowed_consequences_secondary += self._consequence_overrides.keys()

        compound_het_pairs_by_gene = {}
        for gene_agg in response.aggregations.genes.buckets:
            self._parse_compound_het_gene(gene_agg, compound_het_pairs_by_gene, family_unaffected_individual_guids)

        total_compound_het_results = sum(len(compound_het_pairs) for compound_het_pairs in compound_het_pairs_by_gene.values())
        logger.info('Total compound het hits: {}'.format(total_compound_het_results), self._user)

        compound_het_results = []
        for k, compound_het_pairs in compound_het_pairs_by_gene.items():
            compound_het_results.extend([{k: compound_het_pair} for compound_het_pair in compound_het_pairs])
        return compound_het_results, total_compound_het_results

    def _parse_compound_het_gene(self, gene_agg, compound_het_pairs_by_gene, family_unaffected_individual_guids):
        gene_variants = [self._parse_hit(hit) for hit in gene_agg['vars_by_gene']]
        gene_id = gene_agg['key']

        if gene_id in compound_het_pairs_by_gene:
            return

        # Variants are returned if any transcripts have the filtered consequence, but to be compound het
        # the filtered consequence needs to be present in at least one transcript in the gene of interest
        if self._allowed_consequences:
            gene_variants = self._filter_invalid_annotation_compound_hets(gene_id, gene_variants)

        if len(gene_variants) < 2:
            return

        # Do not include groups multiple times if identical variants are in the same multiple genes
        if any((not variant['mainTranscriptId']) or all(t['transcriptId'] != variant['mainTranscriptId']
                                                        for t in variant['transcripts'][gene_id]) for variant in
               gene_variants):
            if not self._is_primary_compound_het_gene(gene_id, gene_variants, compound_het_pairs_by_gene):
                return

        family_compound_het_pairs = defaultdict(list)
        for variant in gene_variants:
            for family_guid in variant['familyGuids']:
                family_compound_het_pairs[family_guid].append(variant)

        self._filter_invalid_family_compound_hets(gene_id, family_compound_het_pairs,
                                                  family_unaffected_individual_guids)

        gene_compound_het_pairs = [ch_pair for ch_pairs in family_compound_het_pairs.values() for ch_pair in ch_pairs]
        for compound_het_pair in gene_compound_het_pairs:
            for variant in compound_het_pair:
                variant['familyGuids'] = [family_guid for family_guid in variant['familyGuids']
                                          if len(family_compound_het_pairs[family_guid]) > 0]
                variant.pop('gene_consequences', None)
        gene_compound_het_pairs = [compound_het_pair for compound_het_pair in gene_compound_het_pairs
                                   if compound_het_pair[0]['familyGuids'] and compound_het_pair[1]['familyGuids']]
        if gene_compound_het_pairs:
            compound_het_pairs_by_gene[gene_id] = gene_compound_het_pairs

    def _is_primary_compound_het_gene(self, gene_id, gene_variants, compound_het_pairs_by_gene):
        primary_genes = set()
        for variant in gene_variants:
            if variant['mainTranscriptId']:
                for gene, transcripts in variant['transcripts'].items():
                    if any(t['transcriptId'] == variant['mainTranscriptId'] for t in transcripts):
                        primary_genes.add(gene)
                        break
        if len(primary_genes) == 1:
            is_valid_gene = True
            primary_gene = primary_genes.pop()
            if self._allowed_consequences:
                is_valid_gene = all(any(
                    consequence in self._allowed_consequences for consequence in
                    variant['gene_consequences'].get(primary_gene, [])
                ) for variant in gene_variants)
            if is_valid_gene:
                if primary_gene != gene_id:
                    return False

        else:
            variant_ids = [variant['variantId'] for variant in gene_variants]
            for gene in primary_genes:
                if variant_ids == [compound_het_pair[0]['variantId'] for compound_het_pair in
                                   compound_het_pairs_by_gene.get(gene, [])] and \
                        variant_ids == [compound_het_pair[1]['variantId'] for compound_het_pair in
                                        compound_het_pairs_by_gene.get(gene, [])]:
                    return False
        return True

    def _filter_invalid_annotation_compound_hets(self, gene_id, gene_variants):
        allowed_consequences = self._allowed_consequences + (self._allowed_consequences_secondary or [])
        has_canonical_transcript_filter = CANONICAL_TRANSCRIPT_FILTER in allowed_consequences
        for variant in gene_variants:
            all_gene_consequences = []
            if variant.get('svType'):
                all_gene_consequences.append(variant['svType'])
            if _is_matched_clinvar_significance(variant.get(CLINVAR_KEY, {}).get('clinicalSignificance'), self._consequence_overrides.get(CLINVAR_KEY)):
                all_gene_consequences.append(CLINVAR_KEY)
            if variant.get(HGMD_KEY, {}).get('class') in self._consequence_overrides.get(HGMD_KEY, []):
                all_gene_consequences.append(HGMD_KEY)
            splice_ai = variant.get('predictions', {}).get(SPLICE_AI_FIELD)
            if splice_ai and splice_ai >= self._consequence_overrides.get(SPLICE_AI_FIELD, 100):
                all_gene_consequences.append(SPLICE_AI_FIELD)

            variant['gene_consequences'] = {}
            for k, transcripts in variant['transcripts'].items():
                transcript_consequences = [
                    (transcript['majorConsequence'], transcript.get('canonical'))
                    for transcript in transcripts if transcript.get('majorConsequence')
                ]
                variant['gene_consequences'][k] = all_gene_consequences + [
                    consequence for consequence, _ in transcript_consequences
                ]
                if has_canonical_transcript_filter and any(
                        canonical for consequence, canonical in transcript_consequences
                        if consequence == 'non_coding_transcript_exon_variant'):
                    variant['gene_consequences'][k].append(CANONICAL_TRANSCRIPT_FILTER)

        return [variant for variant in gene_variants if any(
            consequence in allowed_consequences
            for consequence in variant['gene_consequences'].get(gene_id, [])
        )]

    def _filter_invalid_family_compound_hets(self, gene_id, family_compound_het_pairs, family_unaffected_individual_guids):
        for family_guid, variants in family_compound_het_pairs.items():
            unaffected_individuals = family_unaffected_individual_guids.get(family_guid, [])

            hom_alt_variant_ids = set()
            if self._paired_index_comp_het:
                hom_alt_variant_ids = {
                    var['variantId'] for var in variants if any(gen.get('numAlt') == 2 for gen in var['genotypes'].values())
                }

            valid_combinations = []
            for ch_1_index, ch_2_index in combinations(range(len(variants)), 2):
                variant_1 = variants[ch_1_index]
                variant_2 = variants[ch_2_index]

                if hom_alt_variant_ids:
                    # SNPs overlapped by trans deletions may be incorrectly called as hom alt, and should be
                    # considered comp hets with said deletions. Any other hom alt variants are not valid comp hets
                    hom_alt_var = next(
                        (var for var in [variant_1, variant_2] if var['variantId'] in hom_alt_variant_ids), None)
                    if hom_alt_var:
                        pair_var = variant_1 if hom_alt_var == variant_2 else variant_2
                        is_valid = pair_var.get('svType') == 'DEL' and pair_var['pos'] <= hom_alt_var['pos'] <= pair_var['end']
                        if not is_valid:
                            continue

                is_valid_for_individual = True
                for individual_guid in unaffected_individuals:
                    genotype_1 = variant_1['genotypes'].get(individual_guid)
                    genotype_2 = variant_2['genotypes'].get(individual_guid)
                    if genotype_1 and genotype_2 and genotype_1.get('numAlt') != 0 and not genotype_1.get('isRef') and \
                            genotype_2.get('numAlt') != 0 and not genotype_2.get('isRef'):
                        is_valid_for_individual = False
                        break
                if not is_valid_for_individual:
                    continue

                if self._allowed_consequences and self._allowed_consequences_secondary:
                    # Make a copy of lists to prevent blowing up memory usage
                    consequences = [] + variant_1['gene_consequences'].get(gene_id, [])
                    consequences += variant_2['gene_consequences'].get(gene_id, [])
                    if all(consequence not in self._allowed_consequences for consequence in consequences) or all(
                            consequence not in self._allowed_consequences_secondary for consequence in consequences):
                        continue

                valid_combinations.append([ch_1_index, ch_2_index])

            family_compound_het_pairs[family_guid] = [
                [variants[valid_ch_1_index], variants[valid_ch_2_index]] for
                valid_ch_1_index, valid_ch_2_index in valid_combinations]

    def _deduplicate_results(self, sorted_new_results):
        original_result_count = len(sorted_new_results)
        variant_results = []
        for variant in sorted_new_results:
            if variant_results and variant_results[-1]['variantId'] == variant['variantId']:
                self._merge_duplicate_variants(variant_results[-1], variant)
            else:
                variant_results.append(variant)

        previous_duplicates = self.previous_search_results.get('duplicate_doc_count', 0)
        new_duplicates = original_result_count - len(variant_results)
        self.previous_search_results['duplicate_doc_count'] = previous_duplicates + new_duplicates

        self.previous_search_results['total_results'] -= self.previous_search_results['duplicate_doc_count']

        return variant_results

    @classmethod
    def _merge_duplicate_variants(cls, variant, duplicate_variant):
        for guid, genotype in duplicate_variant['genotypes'].items():
            if guid in variant['genotypes']:
                variant['genotypes'][guid]['otherSample'] = {k: v for k, v in genotype.items() if k != 'otherSample'}
            else:
                variant['genotypes'][guid] = genotype
        variant['familyGuids'] = sorted(set(variant['familyGuids'] + duplicate_variant['familyGuids']))

        # Always show the most up-to-date clinvar
        clinvar_version = variant[CLINVAR_KEY]['version'] or '1900-01-01'
        dup_clinvar_version = duplicate_variant[CLINVAR_KEY]['version'] or '1900-01-01'
        if dup_clinvar_version > clinvar_version:
            variant[CLINVAR_KEY] = duplicate_variant[CLINVAR_KEY]

    def _deduplicate_compound_het_results(self, compound_het_results):
        duplicates = 0
        results = {}
        for gene_compound_het_pair in compound_het_results:
            gene = next(iter(gene_compound_het_pair))
            compound_het_pair = gene_compound_het_pair[gene]
            if gene in results:
                variant_ids = {variant['variantId'] for variant in compound_het_pair}
                existing_index = next(
                    (i for i, existing in enumerate(results[gene]) if
                     {variant['variantId'] for variant in existing} == variant_ids), None,
                )
                if existing_index is not None:
                    existing_compound_het_pair = results[gene][existing_index]
                    self._merge_duplicate_variants(existing_compound_het_pair[0], compound_het_pair[0])
                    self._merge_duplicate_variants(existing_compound_het_pair[1], compound_het_pair[1])
                    duplicates += 1
                else:
                    results[gene].append(compound_het_pair)
            else:
                results[gene] = [compound_het_pair]

        deduplicated_results = []
        for gene, compound_het_pairs in results.items():
            deduplicated_results += [{gene: ch_pair} for ch_pair in compound_het_pairs]

        self.previous_search_results['duplicate_doc_count'] = duplicates + self.previous_search_results.get('duplicate_doc_count', 0)
        self.previous_search_results['total_results'] -= duplicates

        return deduplicated_results

    def _process_compound_hets(self, compound_het_results, variant_results, num_results, all_loaded=False):
        if not self.previous_search_results.get('grouped_results'):
            self.previous_search_results['grouped_results'] = []

        # Sort merged result sets
        grouped_variants = [{None: [var]} for var in variant_results]
        grouped_variants = compound_het_results + grouped_variants
        grouped_variants = _sort_compound_hets(grouped_variants)

        # Get requested page of variants
        merged_variant_results = []
        num_compound_hets = 0
        num_single_variants = 0
        for variants_group in grouped_variants:
            variants = next(iter(variants_group.values()))

            self.previous_search_results['grouped_results'].append(variants_group)
            if len(variants) > 1:
                merged_variant_results.append(variants)
                num_compound_hets += 1
            else:
                merged_variant_results += variants
                num_single_variants += 1
            if not all_loaded and len(merged_variant_results) >= num_results:
                break

        self.previous_search_results['compound_het_results'] = compound_het_results[num_compound_hets:]
        self.previous_search_results['variant_results'] = variant_results[num_single_variants:]
        return merged_variant_results

    def _get_paginated_searches(self, index_name, page=1, num_results=100, start_index=None):
        searches = []
        log_messages = []
        for search in self._index_searches.get(index_name, [self._search]):
            search = search.index(index_name.split(','))

            if search.aggs.to_dict():
                # For compound het search get results from aggregation instead of top level hits
                search = search[:1]
                log_messages.append('Loading {}s for {}'.format(self.AGGREGATION_NAME, index_name))
            else:
                end_index = page * num_results
                if start_index is None:
                    start_index = end_index - num_results

                search = search[start_index:end_index]
                search = search.source(QUERY_FIELD_NAMES)
                log_messages.append('Loading {} records {}-{}'.format(index_name, start_index, end_index))

            searches.append(search)
        return searches, log_messages

    def _execute_search(self, search):
        logger.debug(json.dumps(search.to_dict(), indent=2), self._user)
        try:
            return search.using(self._client).execute()
        except elasticsearch.exceptions.ConnectionTimeout as e:
            tasks = self._get_long_running_tasks()
            if tasks:
                logger.error('ES Query Timeout: Found {} long running searches'.format(len(tasks)), self._user, detail=tasks)
            else:
                logger.warning('ES Query Timeout. No long running searches found', self._user)
            raise e

    def _get_long_running_tasks(self):
        search_tasks = self._client.tasks.list(actions='*search', group_by='parents')
        long_running = []
        for parent_id, task in search_tasks['tasks'].items():
            if task['running_time_in_nanos'] > 10 ** 11:
                long_running.append({'task': task, 'parent_task_id': parent_id})
        return long_running

    def _get_quality_filters_by_family(self, quality_filter, affected_only):
        quality_field_configs = {
            'min_{}'.format(field): {'field': field, 'step': step} for field, step in QUALITY_QUERY_FIELDS.items()
        }
        quality_filter = dict({field: 0 for field in quality_field_configs.keys()}, **(quality_filter or {}))
        for field, config in quality_field_configs.items():
            if quality_filter[field] % config['step'] != 0:
                raise Exception('Invalid {} filter {}'.format(config['field'], quality_filter[field]))

        quality_filters_by_family = {}
        new_svs = self._consequence_overrides.get(NEW_SV_FIELD)
        if new_svs or any(quality_filter[field] for field in quality_field_configs.keys()):
            family_sample_ids = defaultdict(set)
            for index in self._indices:
                family_samples_by_id = self.samples_by_family_index[index]
                for family_guid, samples_by_id in family_samples_by_id.items():
                    if affected_only:
                        family_affected_status = self._family_individual_affected_status[family_guid]
                        sample_ids = {
                            sample_id for sample_id, sample in samples_by_id.items()
                            if family_affected_status[sample.individual.guid] == Individual.AFFECTED_STATUS_AFFECTED
                        }
                    else:
                        sample_ids = samples_by_id.keys()
                    family_sample_ids[family_guid].update(sample_ids)

            path_filter = self._get_clinvar_pathogenic_override_filter()
            for family_guid, sample_ids in sorted(family_sample_ids.items()):
                quality_q = Q('terms', samples_new_call=sorted(sample_ids)) if new_svs else Q()
                for sample_id in sorted(sample_ids):
                    for field, config in sorted(quality_field_configs.items()):
                        if quality_filter[field]:
                            q = _build_or_filter('term', [
                                {'samples_{}_{}_to_{}'.format(config['field'], i, i + config['step']): sample_id}
                                for i in range(0, quality_filter[field], config['step'])
                            ])
                            if field == 'min_ab':
                                #  AB only relevant for hets
                                quality_q &= ~Q(q) | ~Q('term', samples_num_alt_1=sample_id)
                            else:
                                quality_q &= ~Q(q)
                if path_filter:
                    quality_q |= path_filter
                quality_filters_by_family[family_guid] = quality_q
        return quality_filters_by_family


# TODO  move liftover to hail pipeline once upgraded to 0.2 (https://github.com/broadinstitute/seqr/issues/1010)
LIFTOVER_GRCH38_TO_GRCH37 = None
def _liftover_grch38_to_grch37():
    global LIFTOVER_GRCH38_TO_GRCH37
    if not LIFTOVER_GRCH38_TO_GRCH37:
        try:
            LIFTOVER_GRCH38_TO_GRCH37 = LiftOver('hg38', 'hg19')
        except Exception as e:
            logger.error('ERROR: Unable to set up liftover. {}'.format(e), user=None)
    return LIFTOVER_GRCH38_TO_GRCH37


def _get_family_affected_status(samples_by_id, inheritance_filter):
    individual_affected_status = inheritance_filter.get('affected') or {}
    affected_status = {}
    for sample in samples_by_id.values():
        indiv = sample.individual
        affected_status[indiv.guid] = individual_affected_status.get(indiv.guid) or indiv.affected

    return affected_status


def _any_affected_sample_filter(sample_ids):
    sample_ids = sorted(sample_ids)
    return Q('terms', samples_num_alt_1=sample_ids) | Q('terms', samples_num_alt_2=sample_ids) | Q('terms', samples=sample_ids)


def _family_genotype_inheritance_filter(inheritance_mode, inheritance_filter, samples_by_id, individual_affected_status, index_fields):
    samples_q = None

    individuals = [sample.individual for sample in samples_by_id.values()]

    individual_genotype_filter = inheritance_filter.get('genotype') or {}

    if inheritance_mode == X_LINKED_RECESSIVE:
        samples_q = Q('range', xpos={'gte': get_xpos('X', 1), 'lte': get_xpos('Y', 1)})
        for individual in individuals:
            if individual_affected_status[individual.guid] == Individual.AFFECTED_STATUS_UNAFFECTED \
                    and individual.sex == Individual.SEX_MALE:
                individual_genotype_filter[individual.guid] = REF_REF

    is_sv_comp_het = inheritance_mode == COMPOUND_HET and 'samples' in index_fields
    for sample_id, sample in sorted(samples_by_id.items()):

        individual_guid = sample.individual.guid
        affected = individual_affected_status[individual_guid]

        genotype = individual_genotype_filter.get(individual_guid) or inheritance_filter.get(affected)
        if genotype:
            if is_sv_comp_het and affected == Individual.AFFECTED_STATUS_UNAFFECTED:
                # Unaffected individuals for SV compound het search can have any genotype so are not included
                continue

            not_allowed_num_alt = [
                num_alt for num_alt in GENOTYPE_QUERY_MAP[genotype].get('not_allowed_num_alt', [])
                if num_alt in index_fields
            ]
            allowed_num_alt = [
                num_alt for num_alt in GENOTYPE_QUERY_MAP[genotype].get('allowed_num_alt', [])
                if num_alt in index_fields
            ]
            num_alt_to_filter = not_allowed_num_alt or allowed_num_alt
            sample_filters = [{num_alt_key: sample_id} for num_alt_key in num_alt_to_filter]

            sample_q = _build_or_filter('term', sample_filters)
            if not_allowed_num_alt:
                sample_q = ~Q(sample_q)

            if not samples_q:
                samples_q = sample_q
            else:
                samples_q &= sample_q

    return samples_q


def _named_family_sample_q(family_samples_q, family_guid, quality_filters_by_family):
    sample_queries = [family_samples_q]
    quality_q = quality_filters_by_family.get(family_guid)
    if quality_q:
        sample_queries.append(quality_q)

    return Q('bool', must=sample_queries, _name=family_guid)


def _location_filter(genes, intervals, exclude_locations):
    q = None

    if genes:
        q = Q('terms', geneIds=list(genes.keys()))

    if intervals:
        for interval in intervals:
            if interval.get('offset'):
                offset_pos = int((interval['end'] - interval['start']) * interval['offset'])
                interval_q = Q(
                    'range', xpos=_pos_offset_range_filter(interval['chrom'], interval['start'], offset_pos)) & Q(
                    'range', xstop=_pos_offset_range_filter(interval['chrom'], interval['end'], offset_pos))
            else:
                xstart = get_xpos(interval['chrom'], interval['start'])
                xstop = get_xpos(interval['chrom'], interval['end'])
                range_filters = [{
                    key: {
                        'gte': xstart,
                        'lte': xstop,
                    }
                } for key in ['xpos', 'xstop']]
                interval_q = _build_or_filter('range', range_filters)
                interval_q |= Q('range', xpos={'lte': xstart}) & Q('range', xstop={'gte': xstop}) & \
                              Q('range', xpos={'gte': get_xpos(interval['chrom'], MIN_POS)}) & \
                              Q('range', xstop={'lte': get_xpos(interval['chrom'], MAX_POS)})

            if q:
                q |= interval_q
            else:
                q = interval_q

    if exclude_locations:
        return ~q
    else:
        return q


def _pos_offset_range_filter(chrom, pos, offset):
    return {
        'lte': get_xpos(chrom, min(pos + offset, MAX_POS)),
        'gte': get_xpos(chrom, max(pos - offset, MIN_POS)),
    }

def _parse_pathogenicity_filter(pathogenicity):
    clinvar_filters = pathogenicity.get(CLINVAR_KEY, [])
    hgmd_filters = pathogenicity.get(HGMD_KEY, [])

    hgmd_class = set()
    if hgmd_filters:
        for hgmd_filter in hgmd_filters:
            hgmd_class.update(HGMD_CLASS_MAP.get(hgmd_filter, []))

    return sorted(clinvar_filters), sorted(hgmd_class)


VUS_FILTER = 'vus_or_conflicting'
VUS_REGEX = 'Conflicting_interpretations_of_pathogenicity.*|~((.*[Bb]enign.*)|(.*[Pp]athogenic.*))'


def _pathogenicity_filter(clinvar_filters, hgmd_classes=None):
    pathogenicity_filter = None

    path_regex = '|'.join([
        VUS_REGEX if clinvar_filter == VUS_FILTER else f'.*{clinvar_filter.capitalize()}.*'
        for clinvar_filter in clinvar_filters or []
    ])
    if path_regex:
        pathogenicity_filter = Q('regexp', clinvar_clinical_significance=path_regex)

    if hgmd_classes:
        hgmd_q = Q('terms', hgmd_class=hgmd_classes)
        pathogenicity_filter = pathogenicity_filter | hgmd_q if pathogenicity_filter else hgmd_q

    return pathogenicity_filter


def _is_matched_clinvar_significance(clinical_significance, clinvar_filters):
    if not (clinical_significance and clinvar_filters):
        return False

    if VUS_FILTER in clinvar_filters:
        exclude = [
            path.capitalize() for path in ['pathogenic',  'likely_pathogenic', 'likely_benign',  'benign']
            if path not in clinvar_filters
        ]
        return all(substring not in clinical_significance for substring in exclude)

    return any(clinvar_filter.capitalize() in clinical_significance for clinvar_filter in clinvar_filters)


def _annotations_filter(vep_consequences):
    consequences_filter = Q('terms', transcriptConsequenceTerms=sorted(vep_consequences))

    if 'intergenic_variant' in vep_consequences:
        # VEP doesn't add annotations for many intergenic variants so match variants where no transcriptConsequenceTerms
        consequences_filter |= ~Q('exists', field='transcriptConsequenceTerms')

    return consequences_filter


def _in_silico_filter(in_silico_filters, require_score):
    in_silico_qs = []
    for prediction_key, value in in_silico_filters.items():
        try:
            score_q = Q('range', **{prediction_key: {'gte': float(value)}})
        except ValueError:
            score_q = Q('prefix', **{prediction_key: value})

        if not require_score:
            score_q |= ~Q('exists', field=prediction_key)

        in_silico_qs.append(score_q)

    return _or_filters(in_silico_qs)


def _pop_freq_filter(filter_key, value):
    return Q('range', **{filter_key: {'lte': value}}) | ~Q('exists', field=filter_key)


def _build_or_filter(op, filters):
    return  _or_filters([Q(op, **filter_kwargs) for filter_kwargs in filters])


def _or_filters(filter_qs):
    q = filter_qs[0]
    for filter_q in filter_qs[1:]:
        q |= filter_q
    return q


def _sort_compound_hets(grouped_variants):
    return sorted(grouped_variants, key=lambda variants: next(iter(variants.values()))[0]['_sort'])


def get_compound_het_page(grouped_variants, start_index, end_index):
    skipped = 0
    variant_results = []
    variant_count = 0
    for variants in grouped_variants:
        curr_variant = next(iter(variants.values()))
        if skipped < start_index:
            skipped += 1
        else:
            if len(curr_variant) == 1:
                variant_results += curr_variant
            else:
                variant_results.append(curr_variant)
            variant_count += 1
        if variant_count + skipped >= end_index:
            return variant_results
    return None


def _parse_es_sort(sort, sort_config):
    if sort in {'Infinity', '-Infinity', None}:
        # ES returns these values for sort when a sort field is missing, using the correct value for the given direction
        sort = maxsize
    elif hasattr(sort_config, 'values') and any(cfg.get('order') == 'desc' for cfg in sort_config.values()):
        sort = float(sort) * -1

    return sort


def _get_field_values(hit, field_configs, format_response_key=_to_camel_case, get_addl_fields=None, lookup_field_prefix='', existing_fields=None, skip_fields=None):
    return {
        field_config.get('response_key') or format_response_key(field): _value_if_has_key(
            hit,
            (get_addl_fields(field) if get_addl_fields else []) +
            ['{}_{}'.format(lookup_field_prefix, field) if lookup_field_prefix else field],
            existing_fields=existing_fields,
            **field_config
        ) if field not in (skip_fields or []) else None
        for field, field_config in field_configs.items()
    }


def _value_if_has_key(hit, keys, format_value=None, default_value=None, existing_fields=None, **kwargs):
    for key in keys:
        if key in hit:
            return format_value(default_value if hit[key] is None else hit[key]) if format_value else hit[key]
    return default_value if not existing_fields or any(key in existing_fields for key in keys) else None
