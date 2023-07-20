from aiohttp.web import HTTPBadRequest
from copy import deepcopy
from collections import defaultdict
import hail as hl
import logging

from hail_search.constants import CHROM_TO_XPOS_OFFSET, AFFECTED, UNAFFECTED, AFFECTED_ID, UNAFFECTED_ID, MALE, \
    VARIANT_DATASET, MITO_DATASET, STRUCTURAL_ANNOTATION_FIELD, VARIANT_KEY_FIELD, GROUPED_VARIANTS_FIELD, \
    GNOMAD_GENOMES_FIELD, POPULATION_SORTS, CONSEQUENCE_SORT_KEY, COMP_HET_ALT, INHERITANCE_FILTERS, GCNV_KEY, SV_KEY, \
    SV_CONSEQUENCE_RANK_OFFSET, SV_TYPE_DISPLAYS, SV_DEL_INDICES, SV_TYPE_MAP, SV_TYPE_DETAILS, CLINVAR_PATH_RANGES, \
    CLINVAR_NO_ASSERTION, HGMD_PATH_RANGES, RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, NEW_SV_FIELD, \
    ALT_ALT, REF_REF, REF_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, CLINVAR_PATH_SIGNIFICANCES, \
    CLINVAR_KEY, HGMD_KEY, PATH_FREQ_OVERRIDE_CUTOFF, SCREEN_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    XPOS_SORT_KEY, GENOME_VERSION_GRCh38_DISPLAY, STRUCTURAL_ANNOTATION_FIELD_SECONDARY

logger = logging.getLogger(__name__)


def _to_camel_case(snake_case_str):
    converted = snake_case_str.replace('_', ' ').title().replace(' ', '')
    return converted[0].lower() + converted[1:]


class BaseHailTableQuery(object):

    GENOTYPE_QUERY_MAP = {
        REF_REF: lambda gt: gt.is_hom_ref(),
        REF_ALT: lambda gt: gt.is_het(),
        COMP_HET_ALT: lambda gt: gt.is_het(),
        ALT_ALT: lambda gt: gt.is_hom_var(),
        HAS_ALT: lambda gt: gt.is_non_ref(),
        HAS_REF: lambda gt: gt.is_hom_ref() | gt.is_het_ref(),
    }

    GENOTYPE_FIELDS = {}
    GENOTYPE_RESPONSE_KEYS = {}
    POPULATIONS = {}
    POPULATION_FIELDS = {}
    PREDICTION_FIELDS_CONFIG = {}
    OMIT_TRANSCRIPT_FIELDS = []
    ANNOTATION_OVERRIDE_FIELDS = []

    CORE_FIELDS = ['xpos']
    BASE_ANNOTATION_FIELDS = {
        'familyGuids': lambda r: r.genotypes.group_by(lambda x: x.familyGuid).keys(),
        'genotypes': lambda r: r.genotypes.group_by(lambda x: x.individualGuid).map_values(lambda x: x[0]),
    }
    ENUM_ANNOTATION_FIELDS = {}
    LIFTOVER_ANNOTATION_FIELDS = {
        'liftedOverGenomeVersion': lambda r: hl.if_else(  # In production - format all rg37_locus fields in main HT?
            hl.is_defined(r.rg37_locus), '37', hl.missing(hl.dtype('str')),
        ),
        'liftedOverChrom': lambda r: hl.if_else(
            hl.is_defined(r.rg37_locus), r.rg37_locus.contig, hl.missing(hl.dtype('str')),
        ),
        'liftedOverPos': lambda r: hl.if_else(
            hl.is_defined(r.rg37_locus), r.rg37_locus.position, hl.missing(hl.dtype('int32')),
        ),
    }

    SORTS = {
        XPOS_SORT_KEY: lambda r: [r.xpos],
    }

    @staticmethod
    def _get_enum_lookup(ht, field, subfield):
        enum_field = ht.enums.get(field, {}).get(subfield)
        if enum_field is None:
            return None
        return {v: i for i, v in enumerate(hl.eval(enum_field))}

    @classmethod
    def populations_configs(cls):
        return {pop: cls._format_population_config(pop_config) for pop, pop_config in cls.POPULATIONS.items()}

    @staticmethod
    def _format_population_config(pop_config):
        base_pop_config = {field.lower(): field for field in ['AF', 'AC', 'AN', 'Hom', 'Hemi', 'Het']}
        base_pop_config.update(pop_config)
        return base_pop_config

    @property
    def annotation_fields(self):
        enums = hl.eval(self._ht.enums)

        annotation_fields = {
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population) for population in self.POPULATIONS.keys()
            }),
            'predictions': lambda r: hl.struct(**{
                prediction: hl.array(enums[path[0]][path[1]])[r[path[0]][f'{path[1]}_id']]
                if enums.get(path[0], {}).get(path[1]) else r[path[0]][path[1]]
                for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
            'transcripts': lambda r: hl.or_else(
                r.sortedTranscriptConsequences, hl.empty_array(r.sortedTranscriptConsequences.dtype.element_type)
            ).map(lambda t: self._enum_field(
                t, enums['sorted_transcript_consequences'], drop_fields=self.OMIT_TRANSCRIPT_FIELDS,
                format=lambda value: value.rename({k: _to_camel_case(k) for k in value.keys()}),
                annotate=self._annotate_transcript,
            )).group_by(lambda t: t.geneId),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)
        annotation_fields.update({
            enum_config.get('response_key', k): lambda r: self._enum_field(r[k], enums[k], r=r, **enum_config)
            for k, enum_config in self.ENUM_ANNOTATION_FIELDS.items()
        })
        if self._genome_version == GENOME_VERSION_GRCh38_DISPLAY:
            annotation_fields.update(self.LIFTOVER_ANNOTATION_FIELDS)
        return annotation_fields

    def population_expression(self, r, population):
        pop_config = self._format_population_config(self.POPULATIONS[population])
        pop_field = self.POPULATION_FIELDS.get(population, population)
        return hl.struct(**{
            response_key: hl.or_else(r[pop_field][field], '' if response_key == 'id' else 0)
            for response_key, field in pop_config.items() if field is not None
        })

    @classmethod
    def _annotate_transcript(cls, *args):
        return {}

    @staticmethod
    def _enum_field(value, enum, r=None, annotate=None, format=None, drop_fields=None, **kwargs):
        annotations = {}
        drop = [] + (drop_fields or [])
        value_keys = value.keys()
        for field, field_enum in enum.items():
            is_array = f'{field}_ids' in value_keys
            value_field = f"{field}_id{'s' if is_array else ''}"
            drop.append(value_field)

            enum_array = hl.array(field_enum)
            if is_array:
                annotations[f'{field}s'] = value[value_field].map(lambda v: enum_array[v])
            else:
                annotations[field] = enum_array[value[value_field]]

        value = value.annotate(**annotations)
        if annotate:
            annotations = annotate(value, enum, r)
            value = value.annotate(**annotations)
        value = value.drop(*drop)

        if format:
            value = format(value)

        return value

    @staticmethod
    def get_major_consequence_id(transcript):
        raise NotImplementedError

    def __init__(self, data_type, sample_data, genome_version,  gene_ids=None, sort=None, sort_metadata=None, num_results=100, **kwargs):
        self._genome_version = genome_version
        self._sort = sort
        self._sort_metadata = sort_metadata
        self._num_results = num_results
        self._comp_het_ht = None
        self._filtered_genes = gene_ids
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None

        self._load_filtered_table(data_type, sample_data, **kwargs)

    def _load_filtered_table(self, data_type, sample_data, intervals=None, variant_ids=None,
                             inheritance_mode=None, pathogenicity=None, annotations=None, annotations_secondary=None,
                             **kwargs):

        consequence_overrides = self._parse_overrides(pathogenicity, annotations, annotations_secondary)

        self._ht, self._family_guids = self.import_filtered_table(
            data_type, sample_data, intervals=self._parse_intervals(intervals, variant_ids), variant_ids=variant_ids,
            consequence_overrides=consequence_overrides, allowed_consequences=self._allowed_consequences,
            allowed_consequences_secondary=self._allowed_consequences_secondary, filtered_genes=self._filtered_genes,
            inheritance_mode=inheritance_mode, genome_version=self._genome_version, **kwargs,
        )

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            is_all_recessive_search = inheritance_mode == RECESSIVE
            self._filter_compound_hets(is_all_recessive_search)
            if is_all_recessive_search:
                self._ht = self._ht.annotate(genotypes=self._ht.genotypes.filter(
                    lambda e: e.is_recessive
                ).map(lambda e: e.drop('is_comp_het', 'is_recessive')))
                self._ht = self._ht.filter(self._ht.genotypes.size() > 0)

                if self._allowed_consequences_secondary:
                    self._ht = self._ht.filter(self._ht.has_allowed_consequence | self._ht.override_consequences)
            else:
                self._ht = None

    @classmethod
    def import_filtered_table(cls, data_type, sample_data, intervals=None, inheritance_mode=None, quality_filter=None,
                              consequence_overrides=None, genome_version=None, **kwargs):
        tables_path = f'/hail_datasets/{genome_version}/{data_type}'
        load_table_kwargs = {'_intervals': intervals, '_filter_intervals': bool(intervals)}

        quality_filter = quality_filter or {}
        vcf_quality_filter = quality_filter.get('vcf_filter')
        quality_affected_only = quality_filter.get('affected_only')
        quality_filter = cls._format_quality_filter(quality_filter)
        clinvar_path_terms = cls._get_clinvar_path_terms(consequence_overrides)

        family_filter_kwargs = dict(
            quality_filter=quality_filter,  vcf_quality_filter=vcf_quality_filter, clinvar_path_terms=clinvar_path_terms, inheritance_mode=inheritance_mode,
            quality_affected_only=quality_affected_only, consequence_overrides=consequence_overrides, genome_version=genome_version, **kwargs)
        family_filter_kwargs.update(cls._get_family_table_filter_kwargs(
            load_table_kwargs=load_table_kwargs, clinvar_path_terms=clinvar_path_terms, **kwargs))

        family_samples = defaultdict(list)
        project_samples = defaultdict(list)
        for s in sample_data:
            family_samples[s['family_guid']].append(s)
            project_samples[s['project_guid']].append(s)

        family_list_fields = {'family_entries'}
        if clinvar_path_terms and quality_filter:
            family_list_fields.add('passes_quality_families')

        logger.info(f'Loading data for {len(family_samples)} families in {len(project_samples)} projects ({cls.__name__})')
        if len(family_samples) == 1:
            family_guid, family_sample_data = list(family_samples.items())[0]
            family_ht = hl.read_table(f'{tables_path}/families/{family_guid}.ht', **load_table_kwargs)
            families_ht = cls._filter_entries_table(
                family_ht, table_name=family_guid, sample_data=family_sample_data, **family_filter_kwargs)
        else:
            filtered_project_hts = []
            exception_messages = set()
            for project_guid, project_sample_data in project_samples.items():
                project_ht = hl.read_table(f'{tables_path}/projects/{project_guid}.ht', **load_table_kwargs)
                try:
                    filtered_project_hts.append(cls._filter_entries_table(
                        project_ht, sample_data=project_sample_data, table_name=project_guid, **family_filter_kwargs))
                except HTTPBadRequest as e:
                    logger.info(f'Skipped {project_guid}: {e}')
                    exception_messages.add(str(e))

            if len(filtered_project_hts) < 1:
                raise HTTPBadRequest(text='; '.join(exception_messages))

            families_ht = filtered_project_hts[0]
            for project_ht in filtered_project_hts[1:]:
                families_ht = families_ht.join(project_ht, how='outer')
                families_ht = families_ht.select(
                    filters=families_ht.filters.union(families_ht.filters_1),
                    **{k: hl.bind(
                        lambda g1, g2: g1.extend(g2),
                        hl.or_else(families_ht[k], hl.empty_array(families_ht[k].dtype.element_type)),
                        hl.or_else(families_ht[f'{k}_1'], hl.empty_array(families_ht[k].dtype.element_type)),
                    ) for k in family_list_fields},
                )

        # logger.info(f'Prefiltered to {families_ht.count()} rows ({cls.__name__})')

        annotations_ht_path = f'{tables_path}/annotations.ht'
        annotation_ht_query_result = hl.query_table(annotations_ht_path, families_ht.key).first().drop(*families_ht.key)
        ht = families_ht.annotate(**annotation_ht_query_result)
        # Add globals
        ht = ht.join(hl.read_table(annotations_ht_path).head(0).select().select_globals('enums', 'versions'), how='left')
        # logger.info(f'Annotated {ht._force_count()} rows ({cls.__name__})')

        if clinvar_path_terms and quality_filter:
            ht = ht.annotate(family_entries=hl.if_else(
                cls._has_clivar_terms_expr(ht, clinvar_path_terms), ht.family_entries,
                hl.enumerate(ht.family_entries).map(lambda x: hl.or_missing(ht.passes_quality_families[x[0]], x[1]))),
            ).drop('passes_quality_families')
            ht = ht.filter(ht.family_entries.any(lambda x: hl.is_defined(x)))
            # logger.info(f'Filter path/quality to {ht.count()} rows')

        genotype_fields = {}
        if inheritance_mode in {COMPOUND_HET, RECESSIVE}:
            fields = ['affected_id']
            if inheritance_mode == RECESSIVE:
                fields += ['is_comp_het', 'is_recessive']
            genotype_fields.update({k: k for k in fields})
        genotype_fields.update(cls.GENOTYPE_FIELDS)
        ht = ht.transmute(
            genotypes=ht.family_entries.flatmap(lambda x: x).filter(
                lambda gt: hl.is_defined(gt.individualGuid)
            ).map(lambda gt: gt.select(
                'sampleId', 'individualGuid', 'familyGuid',
                numAlt=hl.if_else(hl.is_defined(gt.GT), gt.GT.n_alt_alleles(), -1),
                **{cls.GENOTYPE_RESPONSE_KEYS.get(k, k): gt[field] for k, field in genotype_fields.items()}
            ))
        )

        return cls._filter_annotated_table(
            ht, consequence_overrides=consequence_overrides, clinvar_path_terms=clinvar_path_terms,
             **kwargs), set(family_samples.keys())

    @classmethod
    def _get_family_table_filter_kwargs(cls, **kwargs):
        return {}

    @classmethod
    def _filter_entries_table(cls, ht, sample_data=None, inheritance_mode=None, inheritance_filter=None,
                              genome_version=None, quality_filter=None, clinvar_path_terms=None, consequence_overrides=None,
                              vcf_quality_filter=None, quality_affected_only=False, table_name=None, **kwargs):
        # logger.info(f'Initial count for {table_name}: {ht.count()}')

        ht, sample_id_family_index_map = cls._add_entry_sample_families(ht, sample_data)

        if inheritance_mode == X_LINKED_RECESSIVE:
            x_chrom_interval = hl.parse_locus_interval(
                hl.get_reference(genome_version).x_contigs[0], reference_genome=genome_version)
            ht = ht.filter(cls.get_x_chrom_filter(ht, x_chrom_interval))

        ht = cls._filter_inheritance(
            ht, inheritance_mode, inheritance_filter or {}, sample_data, sample_id_family_index_map,
            consequence_overrides=consequence_overrides,
        )

        if vcf_quality_filter:
            ht = cls._filter_vcf_filters(ht)

        if quality_filter:
            ht = ht.annotate(passes_quality_families=ht.family_entries.map(
                lambda entries: entries.all(
                    lambda gt: (gt.affected_id == UNAFFECTED_ID if quality_affected_only else False) |
                               cls._genotype_passes_quality(gt, quality_filter)
                ))
            )
            if not clinvar_path_terms:
                ht = ht.transmute(family_entries=hl.enumerate(ht.family_entries).map(
                    lambda x: hl.or_missing(ht.passes_quality_families[x[0]], x[1])
                ))
                ht = ht.filter(ht.family_entries.any(lambda x: hl.is_defined(x)))

        # logger.info(f'Prefiltered {table_name} to {ht.count()} rows')

        return ht.select_globals()

    @classmethod
    def _add_entry_sample_families(cls, ht, sample_data):
        sample_index_id_map = dict(enumerate(hl.eval(ht.sample_ids)))
        sample_id_index_map = {v: k for k, v in sample_index_id_map.items()}
        sample_index_id_map = hl.dict(sample_index_id_map)
        sample_individual_map = {s['sample_id']: s['individual_guid'] for s in sample_data}
        missing_samples = set(sample_individual_map.keys()) - set(sample_id_index_map.keys())
        if missing_samples:
            raise HTTPBadRequest(
                text=f'The following samples are available in seqr but missing the loaded data: {", ".join(missing_samples)}'
            )

        affected_id_map = {AFFECTED: AFFECTED_ID, UNAFFECTED: UNAFFECTED_ID}
        sample_index_affected_status = hl.dict({
            sample_id_index_map[s['sample_id']]: affected_id_map.get(s['affected']) for s in sample_data
        })
        sample_index_individual_map = hl.dict({
            sample_id_index_map[sample_id]: i_guid for sample_id, i_guid in sample_individual_map.items()
        })
        sample_id_family_map = {s['sample_id']: s['family_guid'] for s in sample_data}
        sample_index_family_map = hl.dict({sample_id_index_map[k]: v for k, v in sample_id_family_map.items()})
        family_index_map = {f: i for i, f in enumerate(sorted(set(sample_id_family_map.values())))}
        family_sample_indices = [None] * len(family_index_map)
        sample_id_family_index_map = {}
        for sample_id, family_guid in sample_id_family_map.items():
            sample_index = sample_id_index_map[sample_id]
            family_index = family_index_map[family_guid]
            if not family_sample_indices[family_index]:
                family_sample_indices[family_index] = []
            sample_id_family_index_map[sample_id] = (family_index, len(family_sample_indices[family_index]))
            family_sample_indices[family_index].append(sample_index)
        family_sample_indices = hl.array(family_sample_indices)

        ht = ht.transmute(
            family_entries=family_sample_indices.map(lambda sample_indices: sample_indices.map(
                lambda i: hl.or_else(ht.entries[i], cls._missing_entry(ht.entries[i])).annotate(
                    sampleId=sample_index_id_map.get(i),
                    individualGuid=sample_index_individual_map.get(i),
                    familyGuid=sample_index_family_map.get(i),
                    affected_id=sample_index_affected_status.get(i),
                )
            ))
        )

        return ht, sample_id_family_index_map

    @classmethod
    def _missing_entry(cls, entry):
        entry_type = dict(**entry.dtype)
        return hl.struct(**{k: hl.missing(v) for k, v in entry_type.items()})

    @classmethod
    def _filter_inheritance(cls, ht, inheritance_mode, inheritance_filter, sample_data, sample_id_family_index_map, **kwargs):
        any_valid_entry = lambda x: cls.GENOTYPE_QUERY_MAP[HAS_ALT](x.GT)

        is_any_affected = inheritance_mode == ANY_AFFECTED
        if is_any_affected:
            prev_any_valid_entry = any_valid_entry
            any_valid_entry = lambda x: prev_any_valid_entry(x) & (x.affected_id == AFFECTED_ID)

        ht = ht.annotate(family_entries=ht.family_entries.map(
            lambda entries: hl.or_missing(entries.any(any_valid_entry), entries))
        )

        if not (inheritance_filter or inheritance_mode):
            return ht

        if inheritance_mode == RECESSIVE:
            ht = ht.annotate(all_family_entries=ht.family_entries)

        if not is_any_affected:
            ht = cls._filter_families_inheritance(
                ht, inheritance_mode, inheritance_filter, sample_id_family_index_map, sample_data)

        if inheritance_mode == RECESSIVE:
            ht = ht.annotate(family_entries=ht.all_family_entries, recessive_family_entries=ht.family_entries)
            ht = cls._filter_families_inheritance(
                ht, COMPOUND_HET, inheritance_filter, sample_id_family_index_map, sample_data)
            ht = ht.transmute(family_entries=hl.enumerate(ht.all_family_entries).map(lambda x: hl.bind(
                lambda is_recessive, is_comp_het: hl.or_missing(
                    is_recessive | is_comp_het,
                    x[1].map(lambda e: e.annotate(is_recessive=is_recessive, is_comp_het=is_comp_het))
                ),
                hl.is_defined(ht.recessive_family_entries[x[0]]),
                hl.is_defined(ht.family_entries[x[0]]),
            )))

        return ht.filter(ht.family_entries.any(lambda x: hl.is_defined(x)))

    @classmethod
    def _filter_families_inheritance(cls, ht, inheritance_mode, inheritance_filter, sample_id_family_index_map, sample_data):
        inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])
        individual_genotype_filter = inheritance_filter.get('genotype') or {}

        entry_indices_by_gt = defaultdict(lambda: defaultdict(list))
        for s in sample_data:
            genotype = individual_genotype_filter.get(s['individual_guid']) or inheritance_filter.get(s['affected'])
            if inheritance_mode == X_LINKED_RECESSIVE and s['affected'] == UNAFFECTED and s['sex'] == MALE:
                genotype = REF_REF
            if genotype:
                family_index, entry_index = sample_id_family_index_map[s['sample_id']]
                entry_indices_by_gt[genotype][family_index].append(entry_index)

        for genotype, entry_indices in entry_indices_by_gt.items():
            entry_indices = hl.dict(entry_indices)
            ht = ht.annotate(family_entries=hl.enumerate(ht.family_entries).map(lambda x: hl.or_missing(
                ~entry_indices.contains(x[0]) | cls._has_valid_family_genotypes(
                    entry_indices[x[0]].map(lambda i: x[1][i].GT), genotype, inheritance_mode,
                ), x[1],
            )))
            
        return ht

    @classmethod
    def _has_valid_family_genotypes(cls, gts, genotype, inheritance_mode):
        is_valid = gts.all(cls.GENOTYPE_QUERY_MAP[genotype])
        if inheritance_mode == COMPOUND_HET and genotype == HAS_REF:
            is_valid &= ((gts.size() < 2) | gts.any(cls.GENOTYPE_QUERY_MAP[REF_REF]))
        return is_valid

    @classmethod
    def _genotype_passes_quality(cls, gt, quality_filter):
        quality_filter_expr = None
        for field, value in quality_filter.items():
            field_filter = (gt[field] >= value) | hl.is_missing(gt[field])
            if quality_filter_expr is None:
                quality_filter_expr = field_filter
            else:
                quality_filter_expr &= field_filter
        return quality_filter_expr

    @classmethod
    def _filter_annotated_table(cls, ht, custom_query=None, frequencies=None, in_silico=None, clinvar_path_terms=None,
                                consequence_overrides=None, filtered_genes=None,
                                allowed_consequences=None, allowed_consequences_secondary=None, **kwargs):
        if custom_query:
            # In production: should either remove the "custom search" functionality,
            # or should come up with a simple json -> hail query parsing here
            raise NotImplementedError

        if filtered_genes:
            ht = cls._filter_gene_ids(ht, filtered_genes)

        ht = cls._filter_by_frequency(ht, frequencies, clinvar_path_terms)
        # logger.info(f'Filtered frequency to {ht.count()} rows')
        ht = cls._filter_by_in_silico(ht, in_silico)
        # logger.info(f'Filtered in silico to {ht.count()} rows')
        ht = cls._filter_by_annotations(ht, allowed_consequences, allowed_consequences_secondary, consequence_overrides)
        # logger.info(f'Filtered annotations to {ht.count()} rows')

        return ht

    @staticmethod
    def _filter_gene_ids(ht, gene_ids):
        gene_id_set = hl.set(gene_ids)
        return ht.filter(ht.sortedTranscriptConsequences.any(lambda t: gene_id_set.contains(t.gene_id)))

    @staticmethod
    def _should_add_chr_prefix(genome_version):
        reference_genome = hl.get_reference(genome_version)
        return any(c.startswith('chr') for c in reference_genome.contigs)

    @staticmethod
    def _formatted_chr_interval(interval):
        return f'[chr{interval.replace("[", "")}' if interval.startswith('[') else f'chr{interval}'

    def _parse_intervals(self, intervals, variant_ids):
        if variant_ids:
            intervals = [f'[{chrom}:{pos}-{pos}]' for chrom, pos, _, _ in variant_ids]
        if intervals:
            add_chr_prefix = self._should_add_chr_prefix(genome_version=self._genome_version)
            raw_intervals = intervals
            intervals = [hl.eval(hl.parse_locus_interval(
                self._formatted_chr_interval(interval) if add_chr_prefix else interval,
                reference_genome=self._genome_version, invalid_missing=True)
            ) for interval in intervals]
            invalid_intervals = [raw_intervals[i] for i, interval in enumerate(intervals) if interval is None]
            if invalid_intervals:
                raise HTTPBadRequest(text=f'Invalid intervals: {", ".join(invalid_intervals)}')
        return intervals

    def _parse_overrides(self, pathogenicity, annotations, annotations_secondary):
        consequence_overrides = {
            CLINVAR_KEY: set((pathogenicity or {}).get('clinvar', [])),
            HGMD_KEY: set((pathogenicity or {}).get('hgmd', [])),
        }

        annotations = {k: v for k, v in (annotations or {}).items() if v}
        consequence_overrides.update({
            field: annotations.pop(field, None) for field in
            [SCREEN_KEY, SPLICE_AI_FIELD, NEW_SV_FIELD, STRUCTURAL_ANNOTATION_FIELD]
        })

        self._allowed_consequences = sorted({ann for anns in annotations.values() for ann in anns})
        if annotations_secondary:
            consequence_overrides[STRUCTURAL_ANNOTATION_FIELD_SECONDARY] = annotations_secondary.get(STRUCTURAL_ANNOTATION_FIELD)
            self._allowed_consequences_secondary = sorted(
                {ann for anns in annotations_secondary.values() for ann in anns})

        return consequence_overrides

    @classmethod
    def _filter_vcf_filters(cls, ht):
        return ht.filter(hl.is_missing(ht.filters) | (ht.filters.length() < 1))

    @classmethod
    def _filter_by_frequency(cls, ht, frequencies, clinvar_path_terms):
        frequencies = {k: v for k, v in (frequencies or {}).items() if k in cls.POPULATIONS}
        if not frequencies:
            return ht

        has_path_override = clinvar_path_terms and any(
            freqs.get('af') or 1 < PATH_FREQ_OVERRIDE_CUTOFF for freqs in frequencies.values())
        populations_configs = cls.populations_configs()

        for pop, freqs in sorted(frequencies.items()):
            pop_filter = None
            pop_field = cls.POPULATION_FIELDS.get(pop, pop)
            if freqs.get('af') is not None:
                af_field = populations_configs[pop].get('filter_af') or populations_configs[pop]['af']
                pop_filter = ht[pop_field][af_field] <= freqs['af']
                if has_path_override and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= (
                        cls._has_clivar_terms_expr(ht, clinvar_path_terms) &
                        (ht[pop_field][af_field] <= PATH_FREQ_OVERRIDE_CUTOFF)
                    )
            elif freqs.get('ac') is not None:
                ac_field = populations_configs[pop]['ac']
                if ac_field:
                    pop_filter = ht[pop_field][ac_field] <= freqs['ac']

            if freqs.get('hh') is not None:
                hom_field = populations_configs[pop]['hom']
                hemi_field = populations_configs[pop]['hemi']
                if hom_field:
                    hh_filter = ht[pop_field][hom_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter
                if hemi_field:
                    hh_filter = ht[pop_field][hemi_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter

            if pop_filter is not None:
                ht = ht.filter(hl.is_missing(ht[pop_field]) | pop_filter)

        return ht

    @classmethod
    def _filter_by_in_silico(cls, ht, in_silico_filters):
        in_silico_filters = {
            k: v for k, v in (in_silico_filters or {}).items()
            if k == 'requireScore' or (k in cls.PREDICTION_FIELDS_CONFIG and v is not None and len(v) != 0)
        }
        require_score = in_silico_filters.pop('requireScore', False)
        if not in_silico_filters:
            return ht

        in_silico_q = None
        missing_in_silico_q = None
        for in_silico, value in in_silico_filters.items():
            score_path = cls.PREDICTION_FIELDS_CONFIG[in_silico]
            enum_lookup = cls._get_enum_lookup(ht, score_path[0], score_path[1])
            if enum_lookup is not None:
                ht_value = ht[score_path[0]][f'{score_path[1]}_id']
                score_filter = ht_value == enum_lookup[value]
            else:
                ht_value = ht[score_path[0]][score_path[1]]
                score_filter = ht_value >= float(value)

            if in_silico_q is None:
                in_silico_q = score_filter
            else:
                in_silico_q |= score_filter

            if not require_score:
                missing_score_filter = hl.is_missing(ht_value)
                if missing_in_silico_q is None:
                    missing_in_silico_q = missing_score_filter
                else:
                    missing_in_silico_q &= missing_score_filter

        if missing_in_silico_q is not None:
            in_silico_q |= missing_in_silico_q

        return ht.filter(in_silico_q)

    @classmethod
    def _filter_by_annotations(cls, ht, allowed_consequences, allowed_consequences_secondary, consequence_overrides):
        annotation_override_filter = cls._get_annotation_override_filter(ht, consequence_overrides)

        secondary_sv_types = STRUCTURAL_ANNOTATION_FIELD_SECONDARY in cls.ANNOTATION_OVERRIDE_FIELDS and \
            consequence_overrides.get(STRUCTURAL_ANNOTATION_FIELD_SECONDARY)
        has_allowed_secondary_consequence = cls._get_has_annotation_expr(ht, allowed_consequences_secondary)
        if secondary_sv_types:
            secondary_override_expr = cls._has_allowed_sv_type_expr(ht, secondary_sv_types)
            if has_allowed_secondary_consequence is False:
                has_allowed_secondary_consequence = secondary_override_expr
            else:
                has_allowed_secondary_consequence |= secondary_override_expr

        annotation_exprs = {
            'override_consequences': False if annotation_override_filter is None else annotation_override_filter,
            'has_allowed_consequence': cls._get_has_annotation_expr(ht, allowed_consequences),
            'has_allowed_secondary_consequence': has_allowed_secondary_consequence,
        }

        ht = ht.annotate(**annotation_exprs)
        filter_fields = [k for k, v in annotation_exprs.items() if v is not False]

        if not filter_fields:
            return ht

        consequence_filter = ht[filter_fields[0]]
        for field in filter_fields[1:]:
            consequence_filter |= ht[field]
        return ht.filter(consequence_filter)

    @classmethod
    def _get_annotation_override_filter(cls, ht, consequence_overrides):
        annotation_filters = []

        consequence_overrides = {k: v for k, v in consequence_overrides.items() if k in cls.ANNOTATION_OVERRIDE_FIELDS}

        if consequence_overrides.get(CLINVAR_KEY):
            annotation_filters.append(cls._has_clivar_terms_expr(ht, consequence_overrides[CLINVAR_KEY]))
        if consequence_overrides.get(HGMD_KEY):
            annotation_filters.append(
                cls._has_terms_range_expr(ht, 'hgmd', 'class', consequence_overrides[HGMD_KEY], HGMD_PATH_RANGES)
            )
        if consequence_overrides.get(SCREEN_KEY):
            screen_enum = cls._get_enum_lookup(ht, 'screen', 'region_type')
            allowed_consequences = hl.set({screen_enum[c] for c in consequence_overrides[SCREEN_KEY]})
            annotation_filters.append(allowed_consequences.contains(ht.screen.region_type_ids.first()))
        if consequence_overrides.get(SPLICE_AI_FIELD):
            splice_ai = float(consequence_overrides[SPLICE_AI_FIELD])
            score_path = cls.PREDICTION_FIELDS_CONFIG[SPLICE_AI_FIELD]
            annotation_filters.append(ht[score_path[0]][score_path[1]] >= splice_ai)
        if consequence_overrides.get(STRUCTURAL_ANNOTATION_FIELD):
            annotation_filters.append(cls._has_allowed_sv_type_expr(ht, consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]))

        if not annotation_filters:
            return None
        annotation_filter = annotation_filters[0]
        for af in annotation_filters[1:]:
            annotation_filter |= af
        return annotation_filter

    @classmethod
    def _get_clinvar_path_terms(cls, consequence_overrides):
        return {
            f for f in consequence_overrides[CLINVAR_KEY] if f in CLINVAR_PATH_SIGNIFICANCES
        } if CLINVAR_KEY in cls.ANNOTATION_OVERRIDE_FIELDS else []

    @classmethod
    def _has_clivar_terms_expr(cls, ht, clinvar_terms):
        return cls._has_terms_range_expr(ht, 'clinvar', 'pathogenicity', clinvar_terms, CLINVAR_PATH_RANGES)

    @classmethod
    def _has_terms_range_expr(cls, ht, field, subfield, terms, range_configs):
        enum_lookup = cls._get_enum_lookup(ht, field, subfield)

        ranges = []
        range = [None, None]
        for path_filter, start, end in range_configs:
            if path_filter in terms:
                if end is None:
                    # Filter for any value greater than start
                    start = start + 1
                    end = len(enum_lookup)
                range[1] = end
                if not range[0]:
                    range[0] = start
            elif range[0]:
                ranges.append([enum_lookup[range[0]], enum_lookup[range[1]]])
                range = [None, None]

        if not ranges:
            return True

        value = ht[field][f'{subfield}_id']
        q = (value >= ranges[0][0]) & (value <= ranges[0][1])
        for range in ranges[1:]:
            q |= (value >= range[0]) & (value <= range[1])

        return q

    @staticmethod
    def _has_allowed_sv_type_expr(ht, sv_types):
        allowed_sv_types = hl.set({SV_TYPE_MAP[t] for t in sv_types})
        return allowed_sv_types.contains(ht.svType_id)

    @classmethod
    def _get_has_annotation_expr(cls, ht, allowed_consequences):
        allowed_consequence_ids = cls._get_allowed_consequence_ids(ht, allowed_consequences)
        if allowed_consequence_ids:
            allowed_consequence_ids = hl.set(allowed_consequence_ids)
            return ht.sortedTranscriptConsequences.any(
                lambda tc: cls._is_allowed_consequence_filter(tc, allowed_consequence_ids))
        return False

    @classmethod
    def _get_allowed_consequence_ids(cls, ht, allowed_consequences):
        enum = cls._get_enum_lookup(ht, 'sorted_transcript_consequences', 'consequence_term')
        return {enum[c] for c in (allowed_consequences or []) if enum.get(c)}

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequence_ids):
        return allowed_consequence_ids.contains(tc.major_consequence_id)

    @classmethod
    def _format_quality_filter(cls, quality_filter):
        parsed_quality_filter = {}
        for filter_k, value in quality_filter.items():
            field = cls.GENOTYPE_FIELDS.get(filter_k.replace('min_', ''))
            if field and value:
                parsed_quality_filter[field] = value
        return parsed_quality_filter

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return x_interval.contains(ht.locus)

    def _filter_compound_hets(self, is_all_recessive_search):
        ch_ht = self._ht
        if is_all_recessive_search:
            ch_ht = ch_ht.annotate(genotypes=ch_ht.genotypes.filter(
                lambda e: e.is_comp_het).map(lambda e: e.drop('is_comp_het', 'is_recessive')))
            ch_ht = ch_ht.filter(ch_ht.genotypes.size() > 0)

        family_guids = hl.array(sorted(self._family_guids))
        ch_ht = ch_ht.annotate(
            gene_ids=hl.set(ch_ht.sortedTranscriptConsequences.map(lambda t: t.gene_id)),
            family_genotypes=hl.bind(
                lambda family_genotypes: family_guids.map(lambda family_guid: family_genotypes.get(family_guid)),
                ch_ht.genotypes.group_by(lambda x: x.familyGuid)
            ),
        )

        # Get possible pairs of variants within the same gene
        ch_ht = ch_ht.explode(ch_ht.gene_ids)
        formatted_rows_expr = hl.agg.collect(ch_ht.row)
        if self._allowed_consequences_secondary:
            v1_expr = hl.agg.filter(
                (ch_ht.override_consequences | ch_ht.has_allowed_consequence), formatted_rows_expr,
            )
            v2_expr = hl.agg.filter(
                (ch_ht.override_consequences | ch_ht.has_allowed_secondary_consequence), formatted_rows_expr,
            )
        else:
            v1_expr = formatted_rows_expr
            v2_expr = formatted_rows_expr

        ch_ht = ch_ht.group_by('gene_ids').aggregate(v1=v1_expr, v2=v2_expr)
        ch_ht = ch_ht.explode(ch_ht.v1)
        ch_ht = ch_ht.explode(ch_ht.v2)
        ch_ht = ch_ht.filter(ch_ht.v1[VARIANT_KEY_FIELD] != ch_ht.v2[VARIANT_KEY_FIELD])

        # Filter variant pairs for family and genotype
        ch_ht = ch_ht.annotate(valid_families=hl.enumerate(ch_ht.v1.family_genotypes).map(
            lambda x: self._is_valid_comp_het_family(ch_ht, x[1], ch_ht.v2.family_genotypes[x[0]])
        ))
        ch_ht = ch_ht.filter(ch_ht.valid_families.any(lambda x: x))

        # Format pairs as lists and de-duplicate
        ch_ht = ch_ht.select(**{GROUPED_VARIANTS_FIELD: hl.array([ch_ht.v1, ch_ht.v2]).map(
            lambda v: v.annotate(
                genotypes=hl.enumerate(ch_ht.valid_families).filter(lambda x: x[1]).flatmap(
                    lambda x: v.family_genotypes[x[0]].map(lambda g: g.drop('affected_id'))
                )
            )
        )})
        ch_ht = ch_ht.key_by(**{
            VARIANT_KEY_FIELD: hl.str(':').join(hl.sorted(ch_ht[GROUPED_VARIANTS_FIELD].map(lambda v: v[VARIANT_KEY_FIELD])))
        })

        self._comp_het_ht = ch_ht.distinct()

    def _is_valid_comp_het_family(self, ch_ht, genotypes_1, genotypes2):
        return hl.is_defined(genotypes_1) & hl.is_defined(genotypes2) & genotypes_1.all(
            lambda g: (g.affected_id != UNAFFECTED_ID) | (g.numAlt == 0) | genotypes2.any(
                lambda g2: (g.individualGuid == g2.individualGuid) & (g2.numAlt == 0)
            )
        )

    def _format_comp_het_results(self, ch_ht):
        formatted_grouped_variants = ch_ht[GROUPED_VARIANTS_FIELD].map(
            lambda v: self._format_results(v).annotate(**{VARIANT_KEY_FIELD: v[VARIANT_KEY_FIELD]})
        )
        ch_ht = ch_ht.annotate(**{GROUPED_VARIANTS_FIELD: hl.sorted(formatted_grouped_variants, key=lambda x: x._sort)})
        return ch_ht.annotate(_sort=ch_ht[GROUPED_VARIANTS_FIELD][0]._sort)

    def _format_results(self, ht):
        annotations = {k: v(ht) for k, v in self.annotation_fields.items()}
        annotations.update({
            '_sort': self._sort_order(ht),
            'genomeVersion': self._genome_version.replace('GRCh', ''),
        })
        results = ht.annotate(**annotations)
        return results.select(*self.CORE_FIELDS, *list(annotations.keys()))

    def search(self):
        ch_ht = None
        if self._comp_het_ht:
            ch_ht = self._format_comp_het_results(self._comp_het_ht)

        if self._ht:
            ht = self._format_results(self._ht)
            if ch_ht:
                ht = ht.join(ch_ht, 'outer')
                ht = ht.transmute(_sort=hl.or_else(ht._sort, ht._sort_1))
        else:
            ht = ch_ht

        (total_results, collected) = ht.aggregate((hl.agg.count(), hl.agg.take(ht.row, self._num_results, ordering=ht._sort)))
        logger.info(f'Total hits: {total_results}. Fetched: {self._num_results}')

        hail_results = [
            self._json_serialize(row.get(GROUPED_VARIANTS_FIELD) or row.drop(GROUPED_VARIANTS_FIELD)) for row in collected
        ]
        return hail_results, total_results

    def gene_counts(self):
        if self._comp_het_ht:
            ht = self._comp_het_ht.explode(self._comp_het_ht[GROUPED_VARIANTS_FIELD])
            ht = ht.transmute(**ht[GROUPED_VARIANTS_FIELD])
            if self._ht:
                ht = ht.join(self._ht, 'outer')
        else:
            ht = self._ht

        ht = ht.select(
            gene_ids=hl.set(ht.sortedTranscriptConsequences.map(lambda t: t.gene_id)),
            families=self.BASE_ANNOTATION_FIELDS['familyGuids'](ht),
        ).explode('gene_ids').explode('families')
        gene_counts = ht.aggregate(hl.agg.group_by(
            ht.gene_ids, hl.struct(total=hl.agg.count(), families=hl.agg.counter(ht.families))
        ))

        return self._json_serialize(gene_counts)

    def _sort_order(self, ht):
        sort_expressions = self._get_sort_expressions(ht, XPOS_SORT_KEY)
        if self._sort != XPOS_SORT_KEY:
            sort_expressions = self._get_sort_expressions(ht, self._sort) + sort_expressions
        return sort_expressions

    def _get_sort_expressions(self, ht, sort):
        if sort in self.SORTS:
            return self.SORTS[sort](ht)
        elif sort == CONSEQUENCE_SORT_KEY:
            return self._consequence_sorts(ht)

        sort_expression = None
        if sort in POPULATION_SORTS:
            pop_fields = [pop for pop in POPULATION_SORTS[sort] if pop in self.POPULATIONS]
            af_exprs = [self.population_expression(ht, pop).af for pop in pop_fields]
            if af_exprs:
                sort_expression = af_exprs[0]
                for af_expr in af_exprs[1:]:
                    sort_expression = hl.or_else(sort_expression, af_expr)

        elif sort in self.PREDICTION_FIELDS_CONFIG:
            prediction_path = self.PREDICTION_FIELDS_CONFIG[sort]
            sort_expression = -ht[prediction_path[0]][prediction_path[1]]

        elif sort == 'in_omim':
            sort_expression = -self._omim_sort(ht, hl.set(set(self._sort_metadata)))

        elif self._sort_metadata:
            sort_expression = self._gene_rank_sort(ht, self._sort_metadata)

        return [sort_expression] if sort_expression is not None else []

    @classmethod
    def _consequence_sorts(cls, ht):
        return [hl.min(ht.sortedTranscriptConsequences.map(cls.get_major_consequence_id))]

    @classmethod
    def _omim_sort(cls, ht, omim_gene_set):
        return ht.sortedTranscriptConsequences.filter(lambda t: omim_gene_set.contains(t.gene_id)).size()

    @staticmethod
    def _gene_rank_sort(ht, gene_ranks):
        gene_ranks = hl.dict(gene_ranks)
        return hl.min(ht.sortedTranscriptConsequences.map(lambda t: gene_ranks.get(t.gene_id)))

    # For production: should use custom json serializer
    @classmethod
    def _json_serialize(cls, result):
        if isinstance(result, list):
            return [cls._json_serialize(o) for o in result]

        if isinstance(result, hl.Struct) or isinstance(result, hl.utils.frozendict):
            result = dict(result)

        if isinstance(result, dict):
            return {k: cls._json_serialize(v) for k, v in result.items()}

        return result


class BaseVariantHailTableQuery(BaseHailTableQuery):

    GENOTYPE_FIELDS = {f.lower(): f for f in ['DP', 'GQ']}
    POPULATIONS = {}
    PREDICTION_FIELDS_CONFIG = {
        'mut_taster': ('dbnsfp', 'MutationTaster_pred'),
        'polyphen': ('dbnsfp', 'Polyphen2_HVAR_pred'),
        'revel': ('dbnsfp', 'REVEL_score'),
        'sift': ('dbnsfp', 'SIFT_pred'),
    }
    OMIT_TRANSCRIPT_FIELDS = ['consequence_terms']
    ANNOTATION_OVERRIDE_FIELDS = [CLINVAR_KEY]

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid']
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),  # In production - format in main HT?
        'mainTranscriptId': lambda r: r.sortedTranscriptConsequences[0].transcript_id,
        'selectedMainTranscriptId': lambda r: hl.or_missing(
            r.selected_transcript != r.sortedTranscriptConsequences[0], r.selected_transcript.transcript_id,
        ),
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)
    ENUM_ANNOTATION_FIELDS = {
        'clinvar': {'annotate': lambda value, enum, r: {
            'conflictingPathogenicities': value.conflictingPathogenicities.map(
                lambda p: p.annotate(pathogenicity=hl.array(enum['pathogenicity'])[p.pathogenicity_id]).drop('pathogenicity_id')
            ),
            'version': r.versions.clinvar,
        }},
    }

    SORTS = {
        PATHOGENICTY_SORT_KEY: lambda r: [hl.or_else(
            r.clinvar.pathogenicity_id,
            # sort variants absent from clinvar between uncertain and benign
            BaseHailTableQuery._get_enum_lookup(r, 'clinvar', 'pathogenicity')[CLINVAR_NO_ASSERTION] + 0.5,
        )],
    }
    SORTS.update(BaseHailTableQuery.SORTS)
    SORTS[PATHOGENICTY_HGMD_SORT_KEY] = SORTS[PATHOGENICTY_SORT_KEY]

    def _selected_main_transcript_expr(self, results):
        all_transcripts = results.sortedTranscriptConsequences

        gene_transcripts = None
        if self._filtered_genes:
            filtered_genes = hl.set(self._filtered_genes)
            gene_transcripts = all_transcripts.filter(lambda t: filtered_genes.contains(t.gene_id))

        consequence_transcripts = None
        if self._allowed_consequences:
            allowed_consequence_ids = hl.set(self._get_allowed_consequence_ids(ht, self._allowed_consequences))
            consequence_transcripts = all_transcripts.filter(
                lambda t: allowed_consequence_ids.contains(self.get_major_consequence_id(t))
            )
            if self._allowed_consequences_secondary:
                allowed_consequence_ids_secondary = hl.set(
                    self._get_allowed_consequence_ids(ht, self._allowed_consequences_secondary)
                )
                consequence_transcripts = hl.if_else(
                    results.has_allowed_consequence, consequence_transcripts,
                    all_transcripts.filter(
                        lambda t: allowed_consequence_ids_secondary.contains(self.get_major_consequence_id(t))
                    )
                )

        if gene_transcripts is not None:
            if consequence_transcripts is None:
                matched_transcripts = gene_transcripts
            else:
                consequence_transcript_ids = hl.set(consequence_transcripts.map(lambda t: t.transcript_id))
                matched_transcripts = hl.bind(
                    lambda t: hl.if_else(t.size() > 0, t, gene_transcripts),
                    gene_transcripts.filter(lambda t: consequence_transcript_ids.contains(t.transcript_id)),
                )
        elif consequence_transcripts is not None:
            matched_transcripts = consequence_transcripts
        else:
            matched_transcripts = all_transcripts

        return matched_transcripts.first()

    @classmethod
    def import_filtered_table(cls, data_type, sample_data, intervals=None, exclude_intervals=False, **kwargs):
        ht, family_guids = super(BaseVariantHailTableQuery, cls).import_filtered_table(
            data_type, sample_data, intervals=None if exclude_intervals else intervals,
            excluded_intervals=intervals if exclude_intervals else None, **kwargs)
        ht = ht.key_by(VARIANT_KEY_FIELD)
        return ht, family_guids

    @classmethod
    def _filter_entries_table(cls, ht, excluded_intervals=None, variant_ids=None, genome_version=None, **kwargs):
        # if excluded_intervals or variant_ids:
        #     logger.info(f'Unfiltered count: {ht.count()}')

        if excluded_intervals:
            ht = hl.filter_intervals(ht, excluded_intervals, keep=False)
        if variant_ids:
            if len(variant_ids) == 1:
                variant_id_q = ht.alleles == [variant_ids[0][2], variant_ids[0][3]]
            else:
                if cls._should_add_chr_prefix(genome_version):
                    variant_ids = [(f'chr{chr}', *v_id) for chr, *v_id in variant_ids]
                variant_id_qs = [
                    (ht.locus == hl.locus(chrom, pos, reference_genome=genome_version)) &
                    (ht.alleles == [ref, alt])
                    for chrom, pos, ref, alt in variant_ids
                ]
                variant_id_q = variant_id_qs[0]
                for q in variant_id_qs[1:]:
                    variant_id_q |= q
            ht = ht.filter(variant_id_q)

        return super(BaseVariantHailTableQuery, cls)._filter_entries_table(ht, genome_version=genome_version, **kwargs)

    @classmethod
    def _filter_annotated_table(cls, ht, rs_ids=None, **kwargs):
        if rs_ids:
            rs_id_set = hl.set(rs_ids)
            ht = ht.filter(rs_id_set.contains(ht.rsid))
        return super(BaseVariantHailTableQuery, cls)._filter_annotated_table(ht, **kwargs)

    @classmethod
    def _annotate_transcript(cls, transcript, *args):
        return {'major_consequence': transcript.consequence_terms.first()}

    @staticmethod
    def get_major_consequence_id(transcript):
        return hl.min(transcript.consequence_term_ids)

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequence_ids):
        return allowed_consequence_ids.intersection(hl.set(tc.consequence_term_ids)).size() > 0

    @classmethod
    def _consequence_sorts(cls, ht):
        return super(BaseVariantHailTableQuery, cls)._consequence_sorts(ht) + [
            cls.get_major_consequence_id(ht.selected_transcript),
        ]

    @classmethod
    def _omim_sort(cls, ht, omim_gene_set):
        return super(BaseVariantHailTableQuery, cls)._omim_sort(ht, omim_gene_set) + hl.if_else(
            hl.is_missing(ht.selected_transcript.consequence_term_ids) |
            omim_gene_set.contains(ht.selected_transcript.gene_id),
            10, 0)

    def _format_results(self, ht):
        ht = ht.annotate(selected_transcript=self._selected_main_transcript_expr(ht))
        return super(BaseVariantHailTableQuery, self)._format_results(ht)


class VariantHailTableQuery(BaseVariantHailTableQuery):

    GENOTYPE_FIELDS = {f.lower(): f for f in ['AB']}
    GENOTYPE_FIELDS.update(BaseVariantHailTableQuery.GENOTYPE_FIELDS)
    POPULATIONS = {
        'seqr': {'hom': 'hom', 'hemi': None, 'het': None},
        'topmed': {'hemi': None},
        'exac': {
            'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi', 'het': 'AC_Het',
        },
        'gnomad_exomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
        GNOMAD_GENOMES_FIELD: {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
    }
    POPULATIONS.update(BaseVariantHailTableQuery.POPULATIONS)
    POPULATION_FIELDS = {'seqr': 'gt_stats'}
    PREDICTION_FIELDS_CONFIG = {
        'cadd': ('cadd', 'PHRED'),
        'eigen': ('eigen', 'Eigen_phred'),
        'fathmm': ('dbnsfp', 'fathmm_MKL_coding_pred'),
        'gnomad_noncoding': ('gnomad_non_coding_constraint', 'z_score'),
        'mpc': ('mpc', 'MPC'),
        'mut_pred': ('dbnsfp', 'MutPred_score'),
        'primate_ai': ('primate_ai', 'score'),
        'splice_ai': ('splice_ai', 'delta_score'),
        'splice_ai_consequence': ('splice_ai', 'splice_consequence'),
        'vest': ('dbnsfp', 'VEST4_score'),
    }
    PREDICTION_FIELDS_CONFIG.update(BaseVariantHailTableQuery.PREDICTION_FIELDS_CONFIG)
    ANNOTATION_OVERRIDE_FIELDS = [HGMD_KEY, SPLICE_AI_FIELD, SCREEN_KEY] + BaseVariantHailTableQuery.ANNOTATION_OVERRIDE_FIELDS

    ENUM_ANNOTATION_FIELDS = {
        'hgmd': {},
        'screen': {
            'response_key': 'screenRegionType',
            'format': lambda value: value.region_types.first(),
        },
    }
    ENUM_ANNOTATION_FIELDS.update(BaseVariantHailTableQuery.ENUM_ANNOTATION_FIELDS)

    SORTS = deepcopy(BaseVariantHailTableQuery.SORTS)
    SORTS[PATHOGENICTY_HGMD_SORT_KEY] = lambda r: BaseVariantHailTableQuery.SORTS[PATHOGENICTY_SORT_KEY](r) + [r.hgmd.class_id]

    @classmethod
    def _filter_annotated_table(cls, ht, **kwargs):
        # TODO remove once all other data types have been updated
        ht = ht.transmute(variantId=ht.variant_id, sortedTranscriptConsequences=ht.sorted_transcript_consequences)
        return super(VariantHailTableQuery, cls)._filter_annotated_table(ht, **kwargs)

    @classmethod
    def _get_family_table_filter_kwargs(cls, frequencies=None, load_table_kwargs=None, clinvar_path_terms=None, **kwargs):
        gnomad_genomes_filter = (frequencies or {}).get(GNOMAD_GENOMES_FIELD, {})
        af_cutoff = gnomad_genomes_filter.get('af')
        if af_cutoff is None and gnomad_genomes_filter.get('ac') is not None:
            af_cutoff = 0.01
        if af_cutoff is None:
            return {}
        if clinvar_path_terms:
            af_cutoff = max(af_cutoff, PATH_FREQ_OVERRIDE_CUTOFF)

        high_af_ht = hl.read_table('/hail_datasets/high_af_variants.ht', **(load_table_kwargs or {}))
        if af_cutoff > 0.01:
            high_af_ht = high_af_ht.filter(high_af_ht.is_gt_10_percent)
        return {'high_af_ht': high_af_ht}

    @classmethod
    def _filter_entries_table(cls, ht, high_af_ht=None, **kwargs):
        if high_af_ht is not None:
            # logger.info(f'No AF filter count: {ht.count()}')
            ht = ht.filter(hl.is_missing(high_af_ht[ht.key]))

        return super(VariantHailTableQuery, cls)._filter_entries_table(ht, **kwargs)

    @classmethod
    def _genotype_passes_quality(cls, gt, quality_filter):
        no_ab_quality_filter = {k: v for k, v in quality_filter.items() if k != 'AB'}
        quality_filter_expr = super(VariantHailTableQuery, cls)._genotype_passes_quality(gt, no_ab_quality_filter)
        ab_value = quality_filter.get('AB')
        if ab_value:
            # AB only relevant for hets
            field_filter = (gt.AB >= ab_value / 100) | ~gt.GT.is_het()
            if quality_filter_expr is None:
                quality_filter_expr = field_filter
            else:
                quality_filter_expr &= field_filter

        return quality_filter_expr


class MitoHailTableQuery(BaseVariantHailTableQuery):

    GENOTYPE_FIELDS = {
        'hl': 'HL',
        'mitoCn': 'mito_cn',
        'contamination': 'contamination',
    }
    GENOTYPE_FIELDS.update(BaseVariantHailTableQuery.GENOTYPE_FIELDS)
    POPULATIONS = {
        pop: {'hom': None, 'hemi': None, 'het': None} for pop in [
            'callset_heteroplasmy', 'gnomad_mito', 'gnomad_mito_heteroplasmy', 'helix', 'helix_heteroplasmy'
        ]
    }
    for pop in ['gnomad_mito_heteroplasmy', 'helix_heteroplasmy']:
        POPULATIONS[pop].update({'max_hl': 'max_hl'})
    POPULATIONS['callset'] = {'hom': None, 'hemi': None, 'het': None}
    POPULATIONS.update(BaseVariantHailTableQuery.POPULATIONS)
    PREDICTION_FIELDS_CONFIG = {
        'apogee': ('mitimpact', 'score'),
        'fathmm': ('dbnsfp', 'FATHMM_pred'),
        'hmtvar': ('hmtvar', 'score'),
        'mitotip': ('mitotip', 'trna_prediction'),
        'haplogroup_defining': ('haplogroup', 'is_defining'),
    }
    PREDICTION_FIELDS_CONFIG.update(BaseVariantHailTableQuery.PREDICTION_FIELDS_CONFIG)
    BASE_ANNOTATION_FIELDS = {
        'commonLowHeteroplasmy': lambda r: r.common_low_heteroplasmy,
        'highConstraintRegion': lambda r: r.high_constraint_region,
        'mitomapPathogenic': lambda r: r.mitomap.pathogenic,
    }
    BASE_ANNOTATION_FIELDS.update(BaseVariantHailTableQuery.BASE_ANNOTATION_FIELDS)

    @classmethod
    def _format_quality_filter(cls, quality_filter):
        return super(MitoHailTableQuery, cls)._format_quality_filter(
            {k: v / 100 if k == 'min_hl' else v for k, v in (quality_filter or {}).items()}
        )


def _no_genotype_override(genotypes, field):
    return genotypes.any(lambda g: (g.numAlt > 0) & hl.is_missing(g[field]))


def _get_genotype_override_field(genotypes, default, field, agg):
    return hl.if_else(
        _no_genotype_override(genotypes, field), default, agg(genotypes.map(lambda g: g[field]))
    )


class BaseSvHailTableQuery(BaseHailTableQuery):

    GENOTYPE_QUERY_MAP = deepcopy(BaseHailTableQuery.GENOTYPE_QUERY_MAP)
    GENOTYPE_QUERY_MAP[COMP_HET_ALT] = GENOTYPE_QUERY_MAP[HAS_ALT]

    GENOTYPE_FIELDS = {'cn': 'CN'}
    GENOTYPE_RESPONSE_KEYS = {'gq_sv': 'gq'}
    POPULATIONS = {
        'sv_callset': {'hemi': None},
    }
    PREDICTION_FIELDS_CONFIG = {
        'strvctvre': ('strvctvre', 'score'),
    }

    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.interval.start.contig.replace('^chr', ''),
        'pos': lambda r: r.interval.start.position,
        'end': lambda r: r.interval.end.position,
        'rg37LocusEnd': lambda r: hl.struct(contig=r.rg37_locus_end.contig, position=r.rg37_locus_end.position),
        'svType': lambda r: hl.array(SV_TYPE_DISPLAYS)[r.svType_id],

    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)
    ANNOTATION_OVERRIDE_FIELDS = [STRUCTURAL_ANNOTATION_FIELD, STRUCTURAL_ANNOTATION_FIELD_SECONDARY, NEW_SV_FIELD]

    SORTS = {
        'size': lambda r: [hl.if_else(
            r.interval.start.contig == r.interval.end.contig, r.interval.start.position - r.interval.end.position, -50,
        )],
    }
    SORTS.update(BaseHailTableQuery.SORTS)

    @classmethod
    def import_filtered_table(cls, data_type, sample_data, intervals=None, exclude_intervals=False, variant_keys=None, **kwargs):
        ht, family_guids = super(BaseSvHailTableQuery, cls).import_filtered_table(data_type, sample_data, variant_keys=variant_keys, **kwargs)
        # For searches with both variant_ids and variant_keys, intervals will cover the variant_ids only
        if intervals and not variant_keys:
            interval_filter = hl.array(intervals).all(lambda interval: not interval.overlaps(ht.interval)) \
                if exclude_intervals else hl.array(intervals).any(lambda interval: interval.overlaps(ht.interval))
            ht = ht.filter(interval_filter)
        return ht, family_guids

    @classmethod
    def _filter_entries_table(cls, ht, variant_keys=None, **kwargs):
        if variant_keys:
            variant_keys_set = hl.set(variant_keys)
            ht = ht.filter(variant_keys_set.contains(ht[VARIANT_KEY_FIELD]))

        return super(BaseSvHailTableQuery, cls)._filter_entries_table(ht, **kwargs)

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return ht.interval.overlaps(x_interval)

    @staticmethod
    def get_major_consequence_id(transcript):
        return transcript.major_consequence_id

    @classmethod
    def _filter_inheritance(cls, ht, *args, consequence_overrides=None):
        ht = super(BaseSvHailTableQuery, cls)._filter_inheritance(ht, *args)
        if consequence_overrides[NEW_SV_FIELD]:
            ht = ht.annotate(family_entries=ht.family_entries.map(
                lambda entries: hl.or_missing(entries.any(lambda x: x.newCall), entries))
            )
            ht = ht.filter(ht.family_entries.any(lambda x: hl.is_defined(x)))
        return ht


class GcnvHailTableQuery(BaseSvHailTableQuery):

    GENOTYPE_FIELDS = {
        f: f for f in ['start', 'end', 'numExon', 'geneIds', 'defragged', 'prevCall', 'prevOverlap', 'newCall']
    }
    GENOTYPE_FIELDS.update({'qs': 'QS'})
    GENOTYPE_FIELDS.update(BaseSvHailTableQuery.GENOTYPE_FIELDS)

    BASE_ANNOTATION_FIELDS = deepcopy(BaseSvHailTableQuery.BASE_ANNOTATION_FIELDS)
    BASE_ANNOTATION_FIELDS.update({
        'pos': lambda r: _get_genotype_override_field(r.genotypes, r.interval.start.position, 'start', hl.min),
        'end': lambda r: _get_genotype_override_field(r.genotypes, r.interval.end.position, 'end', hl.max),
        'numExon': lambda r: _get_genotype_override_field(r.genotypes, r.num_exon, 'numExon', hl.max),
    })

    @classmethod
    def _missing_entry(cls, entry):
        #  gCNV data has no ref/ref calls so a missing entry indicates that call
        return super(GcnvHailTableQuery, cls)._missing_entry(entry).annotate(GT=hl.Call([0, 0]))

    @classmethod
    def _filter_vcf_filters(cls, ht):
        return ht

    @classmethod
    def _filter_annotated_table(cls, ht, **kwargs):
        chrom_to_xpos_offset = hl.dict(CHROM_TO_XPOS_OFFSET)
        ht = ht.annotate(
            sortedTranscriptConsequences=hl.if_else(
                _no_genotype_override(ht.genotypes, 'geneIds'), ht.sortedTranscriptConsequences, hl.bind(
                    lambda gene_ids: ht.sortedTranscriptConsequences.filter(lambda t: gene_ids.contains(t.gene_id)),
                    ht.genotypes.flatmap(lambda g: g.geneIds)
                ),
            ),
            # Remove once data is reloaded
            xpos=chrom_to_xpos_offset.get(ht.interval.start.contig.replace('^chr', '')) + ht.interval.start.position,
        )
        return super(GcnvHailTableQuery, cls)._filter_annotated_table(ht, **kwargs)


class SvHailTableQuery(BaseSvHailTableQuery):

    GENOTYPE_FIELDS = {'gq_sv': 'GQ_SV'}
    GENOTYPE_FIELDS.update(BaseSvHailTableQuery.GENOTYPE_FIELDS)
    POPULATIONS = {
        'gnomad_svs': {'id': 'ID', 'ac': None, 'an': None, 'hom': None, 'hemi': None, 'het': None},
    }
    POPULATIONS.update(BaseSvHailTableQuery.POPULATIONS)

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + [
        'algorithms', 'bothsidesSupport', 'cpxIntervals', 'svSourceDetail',
    ]
    BASE_ANNOTATION_FIELDS = {
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),  # In production - format in main HT?
        'svTypeDetail': lambda r: hl.array(SV_TYPE_DETAILS)[r.svTypeDetail_id],
    }
    BASE_ANNOTATION_FIELDS.update(BaseSvHailTableQuery.BASE_ANNOTATION_FIELDS)


QUERY_CLASS_MAP = {
    VARIANT_DATASET: VariantHailTableQuery,
    MITO_DATASET: MitoHailTableQuery,
    GCNV_KEY: GcnvHailTableQuery,
    SV_KEY: SvHailTableQuery,
}

DATA_TYPE_POPULATIONS_MAP = {data_type: set(cls.POPULATIONS.keys()) for data_type, cls in QUERY_CLASS_MAP.items()}


class MultiDataTypeHailTableQuery(object):

    DATA_TYPE_ANNOTATION_FIELDS = []

    def __init__(self, data_type, *args, **kwargs):
        self._data_types = data_type
        self.POPULATIONS = {}
        self.PREDICTION_FIELDS_CONFIG = {}
        self.BASE_ANNOTATION_FIELDS = {}
        self.SORTS = {}

        self.CORE_FIELDS = set()
        for cls in [QUERY_CLASS_MAP[dt] for dt in self._data_types]:
            self.POPULATIONS.update(cls.POPULATIONS)
            self.PREDICTION_FIELDS_CONFIG.update(cls.PREDICTION_FIELDS_CONFIG)
            self.BASE_ANNOTATION_FIELDS.update(cls.BASE_ANNOTATION_FIELDS)
            self.CORE_FIELDS.update(cls.CORE_FIELDS)
            self.SORTS.update(cls.SORTS)
        self.BASE_ANNOTATION_FIELDS.update({
            k: self._annotation_for_data_type(k) for k in self.DATA_TYPE_ANNOTATION_FIELDS
        })
        self.CORE_FIELDS = list(self.CORE_FIELDS - set(self.BASE_ANNOTATION_FIELDS.keys()))

        super(MultiDataTypeHailTableQuery, self).__init__(data_type, *args, **kwargs)

    def _annotation_for_data_type(self, field):
        def field_annotation(r):
            case = hl.case()
            for cls_type in self._data_types:
                cls = QUERY_CLASS_MAP[cls_type]
                if field in cls.BASE_ANNOTATION_FIELDS:
                    case = case.when(r.dataType == cls_type, cls.BASE_ANNOTATION_FIELDS[field](r))
            return case.or_missing()
        return field_annotation

    def population_expression(self, r, population):
        population_map = hl.dict(DATA_TYPE_POPULATIONS_MAP)
        return hl.or_missing(
            population_map[r.dataType].contains(population),
            super(MultiDataTypeHailTableQuery, self).population_expression(r, population),
        )

    @classmethod
    def import_filtered_table(cls, data_type, sample_data, **kwargs):
        data_type_0 = data_type[0]

        ht, family_guids = QUERY_CLASS_MAP[data_type_0].import_filtered_table(data_type_0, sample_data[data_type_0], **kwargs)
        ht = ht.annotate(dataType=data_type_0)
        fields = {k for k in ht.row.keys()}
        globals = {k for k in ht.globals.keys()}

        for dt in data_type[1:]:
            data_type_cls = QUERY_CLASS_MAP[dt]
            sub_ht, new_family_guids = data_type_cls.import_filtered_table(dt, sample_data[dt], **kwargs)
            family_guids.update(new_family_guids)
            sub_ht = sub_ht.annotate(dataType=dt)
            ht = ht.join(sub_ht, how='outer')

            new_fields = {k for k in sub_ht.row.keys()}
            new_globals = {k for k in sub_ht.globals.keys()}
            to_merge = fields.intersection(new_fields)
            to_merge_globals = globals.intersection(new_globals)
            fields.update(new_fields)
            globals.update(new_globals)
            logger.info(f'Merging fields: {", ".join(to_merge)}')

            transmute_expressions = {
                k: hl.or_else(ht[k], ht[f'{k}_1']) for k in to_merge
                if k not in {'sortedTranscriptConsequences', 'genotypes', VARIANT_KEY_FIELD}
            }
            transmute_expressions.update(cls._merge_nested_structs(ht, 'sortedTranscriptConsequences'))
            transmute_expressions.update(cls._merge_nested_structs(ht, 'genotypes'))
            ht = ht.transmute(**transmute_expressions)
            ht = ht.transmute_globals(**{k: hl.struct(**ht[k], **ht[f'{k}_1']) for k in to_merge_globals})

        return ht, family_guids

    @staticmethod
    def _merge_nested_structs(ht, field):
        struct_type = dict(**ht[field].dtype.element_type)
        new_struct_type = dict(**ht[f'{field}_1'].dtype.element_type)
        is_same_type = struct_type == new_struct_type
        struct_type.update(new_struct_type)

        def format_merged(merge_field):
            table_field = ht[merge_field]
            if is_same_type:
                return table_field
            return table_field.map(
                lambda x: x.select(**{k: x.get(k, hl.missing(v)) for k, v in struct_type.items()})
            )

        return {field: hl.or_else(format_merged(field), format_merged(f'{field}_1'))}


class AllSvHailTableQuery(MultiDataTypeHailTableQuery, BaseSvHailTableQuery):

    DATA_TYPE_ANNOTATION_FIELDS = ['end', 'pos']


class AllVariantHailTableQuery(MultiDataTypeHailTableQuery, VariantHailTableQuery):
    pass


class AllDataTypeHailTableQuery(AllVariantHailTableQuery):

    DATA_TYPE_ANNOTATION_FIELDS = ['chrom', 'pos', 'end', 'selectedMainTranscriptId', 'mainTranscriptId']

    @staticmethod
    def get_major_consequence_id(transcript):
        return hl.if_else(
            hl.is_defined(transcript.consequence_term_ids),
            BaseVariantHailTableQuery.get_major_consequence_id(transcript),
            BaseSvHailTableQuery.get_major_consequence_id(transcript),
        )

    @classmethod
    def _annotate_transcript(cls, transcript, *args):
        return {
            k: hl.or_else(v, transcript[k])
            for k, v in BaseVariantHailTableQuery._annotate_transcript(transcript, *args)
        }

    def _is_valid_comp_het_family(self, ch_ht, genotypes_1, genotypes_2):
        is_valid = super(AllDataTypeHailTableQuery, self)._is_valid_comp_het_family(ch_ht, genotypes_1, genotypes_2)
        return is_valid & (
            genotypes_1.all(lambda g: g.numAlt < 2) | self._is_overlapped_trans_deletion(ch_ht.v1, ch_ht.v2)
        ) & (
             genotypes_2.all(lambda g: g.numAlt < 2) | self._is_overlapped_trans_deletion(ch_ht.v2, ch_ht.v1)
        ) & genotypes_1.all(
            lambda g: (g.affected_id != UNAFFECTED_ID) | (g.numAlt == 0) | genotypes_2.any(
                lambda g2: (g.individualGuid == g2.individualGuid) & (g2.numAlt == 0)
            )
        )

    @staticmethod
    def _is_overlapped_trans_deletion(v1, v2):
        # SNPs overlapped by trans deletions may be incorrectly called as hom alt, and should be
        # considered comp hets with said deletions. Any other hom alt variants are not valid comp hets
        return hl.is_defined(v1.locus) & hl.set(SV_DEL_INDICES).contains(v2.svType_id) & \
               (v2.interval.start.position <= v1.locus.position) & (v1.locus.position <= v2.interval.end.position)

    @classmethod
    def _consequence_sorts(cls, ht):
        rank_sort, variant_sort = super(AllDataTypeHailTableQuery, cls)._consequence_sorts(ht)
        is_sv = hl.is_defined(ht.svType_id)
        return [
            hl.if_else(is_sv, SV_CONSEQUENCE_RANK_OFFSET, rank_sort),
            hl.if_else(is_sv, rank_sort, variant_sort),
        ]
