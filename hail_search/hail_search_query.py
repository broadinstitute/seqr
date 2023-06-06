from aiohttp.web import HTTPBadRequest
from copy import deepcopy
from collections import defaultdict
import hail as hl
import logging

from hail_search.constants import CHROM_TO_XPOS_OFFSET, AFFECTED, UNAFFECTED, MALE, VARIANT_DATASET, \
    MITO_DATASET, STRUCTURAL_ANNOTATION_FIELD, VARIANT_KEY_FIELD, GROUPED_VARIANTS_FIELD, \
    GNOMAD_GENOMES_FIELD, POPULATION_SORTS, CONSEQUENCE_SORT_KEY, COMP_HET_ALT, INHERITANCE_FILTERS, GCNV_KEY, SV_KEY, \
    CONSEQUENCE_RANKS, CONSEQUENCE_RANK_MAP, SV_CONSEQUENCE_RANK_OFFSET, SCREEN_CONSEQUENCES, SCREEN_CONSEQUENCE_RANK_MAP, \
    SV_CONSEQUENCE_RANKS, SV_CONSEQUENCE_RANK_MAP, SV_TYPE_DISPLAYS, SV_DEL_INDICES, SV_TYPE_MAP, SV_TYPE_DETAILS, \
    CLINVAR_SIGNIFICANCES, CLINVAR_SIG_MAP, CLINVAR_SIG_BENIGN_OFFSET, HGMD_SIGNIFICANCES, HGMD_SIG_MAP, \
    PREDICTION_FIELD_ID_LOOKUP, RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, NEW_SV_FIELD, ALT_ALT, \
    REF_REF, REF_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, CLINVAR_SIGNFICANCE_MAP, HGMD_CLASS_MAP, CLINVAR_PATH_SIGNIFICANCES, \
    CLINVAR_KEY, HGMD_KEY, PATH_FREQ_OVERRIDE_CUTOFF, SCREEN_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    XPOS_SORT_KEY, GENOME_VERSION_GRCh38_DISPLAY

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
    PREDICTION_FIELDS_CONFIG = {}
    TRANSCRIPT_FIELDS = ['gene_id']
    ANNOTATION_OVERRIDE_FIELDS = []

    CORE_FIELDS = ['genotypes', 'xpos']
    BASE_ANNOTATION_FIELDS = {
        'familyGuids': lambda r: hl.array(r.familyGuids),
    }
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
    COMPUTED_ANNOTATION_FIELDS = {}

    SORTS = {
        XPOS_SORT_KEY: lambda r: [r.xpos],
    }

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
        annotation_fields = {
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population) for population in self.POPULATIONS.keys()
            }),
            'predictions': lambda r: hl.struct(**{
                prediction: hl.array(PREDICTION_FIELD_ID_LOOKUP[prediction])[r[path[0]][path[1]]]
                if prediction in PREDICTION_FIELD_ID_LOOKUP else r[path[0]][path[1]]
                for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
            'transcripts': lambda r: hl.or_else(
                r.sortedTranscriptConsequences, hl.empty_array(r.sortedTranscriptConsequences.dtype.element_type)
            ).map(lambda t: hl.struct(
                majorConsequence=self.get_major_consequence(t),
                **{_to_camel_case(k): t[k] for k in self.TRANSCRIPT_FIELDS},
            )).group_by(lambda t: t.geneId),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)
        if self._genome_version == GENOME_VERSION_GRCh38_DISPLAY:
            annotation_fields.update(self.LIFTOVER_ANNOTATION_FIELDS)
        return annotation_fields

    def population_expression(self, r, population):
        pop_config = self._format_population_config(self.POPULATIONS[population])
        return hl.struct(**{
            response_key: hl.or_else(r[population][field], '' if response_key == 'id' else 0)
            for response_key, field in pop_config.items() if field is not None
        })

    @staticmethod
    def get_major_consequence_id(transcript):
        raise NotImplementedError

    @staticmethod
    def get_major_consequence(transcript):
        raise NotImplementedError

    def __init__(self, data_type, sample_data, genome_version, requester_email=None, gene_ids=None, sort=None, sort_metadata=None, num_results=100, **kwargs):
        self._genome_version = genome_version
        self._sort = sort
        self._sort_metadata = sort_metadata
        self._num_results = num_results
        self._requester_email = requester_email  # In production: log user associated with request
        self._comp_het_ht = None
        self._filtered_genes = gene_ids
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None

        self._load_filtered_table(data_type, sample_data, **kwargs)

    def _load_filtered_table(self, data_type, sample_data, intervals=None, variant_ids=None, exclude_intervals=False,
                             inheritance_mode=None, pathogenicity=None, annotations=None, annotations_secondary=None,
                             **kwargs):

        consequence_overrides = self._parse_overrides(pathogenicity, annotations, annotations_secondary)

        self._ht, self._family_guid = self.import_filtered_table(
            data_type, sample_data, intervals=self._parse_intervals(intervals, variant_ids), variant_ids=variant_ids,
            consequence_overrides=consequence_overrides, allowed_consequences=self._allowed_consequences,
            allowed_consequences_secondary=self._allowed_consequences_secondary, filtered_genes=self._filtered_genes,
            inheritance_mode=inheritance_mode, has_location_search=bool(intervals) and not exclude_intervals,
            exclude_intervals=exclude_intervals, genome_version=self._genome_version, **kwargs,
        )

        self._ht = self._ht.annotate(_sort=self._sort_order())

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            is_all_recessive_search = inheritance_mode == RECESSIVE
            self._filter_compound_hets(is_all_recessive_search)
            if is_all_recessive_search:
                self._ht = self._ht.filter(hl.is_defined(self._ht.recessiveFamilies) & (self._ht.recessiveFamilies.size() > 0))
                self._ht = self._ht.transmute(familyGuids=self._ht.recessiveFamilies)
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
        quality_filter = cls._format_quality_filter(quality_filter)
        clinvar_path_terms = cls._get_clinvar_path_terms(consequence_overrides)

        family_filter_kwargs = dict(
            quality_filter=quality_filter, clinvar_path_terms=clinvar_path_terms, inheritance_mode=inheritance_mode,
            consequence_overrides=consequence_overrides, genome_version=genome_version, **kwargs)
        family_filter_kwargs.update(cls._get_family_table_filter_kwargs(
            load_table_kwargs=load_table_kwargs, clinvar_path_terms=clinvar_path_terms, **kwargs))

        family_samples = defaultdict(list)
        project_samples = defaultdict(list)
        for s in sample_data:
            family_samples[s['family_guid']].append(s)
            project_samples[s['project_guid']].append(s)

        family_set_fields, family_dict_fields = cls._get_families_annotation_fields(inheritance_mode)
        if clinvar_path_terms and quality_filter:
            family_set_fields.add('failQualityFamilies')

        logger.info(f'Loading data for {len(family_samples)} families in {len(project_samples)} projects ({cls.__name__})')
        family_guid = None
        if len(family_samples) == 1:
            family_guid, family_sample_data = list(family_samples.items())[0]
            family_ht = hl.read_table(f'{tables_path}/families/{family_guid}.ht', **load_table_kwargs)
            families_ht = cls._filter_entries_table(
                family_ht, family_guid=family_guid, sample_data=family_sample_data, **family_filter_kwargs)
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
                    genotypes=hl.bind(
                        lambda g1, g2: g1.extend(g2),
                        hl.or_else(families_ht.genotypes, hl.empty_array(families_ht.genotypes.dtype.element_type)),
                        hl.or_else(families_ht.genotypes_1, hl.empty_array(families_ht.genotypes.dtype.element_type)),
                    ),
                    **{k: hl.bind(
                        lambda s1, s2: s1.union(s2),
                        hl.or_else(families_ht[k], hl.empty_set(hl.tstr)),
                        hl.or_else(families_ht[f'{k}_1'], hl.empty_set(hl.tstr)),
                    ) for k in family_set_fields},
                    **{k: hl.bind(
                        lambda d1, d2: hl.dict(d1.items().extend(d2.items())),
                        hl.or_else(families_ht[k], hl.empty_dict(hl.tstr, families_ht[k].dtype.value_type)),
                        hl.or_else(families_ht[f'{k}_1'], hl.empty_dict(hl.tstr, families_ht[k].dtype.value_type)),
                    ) for k in family_dict_fields},
                )

        logger.info(f'Prefiltered to {families_ht.count()} rows ({cls.__name__})')

        annotation_ht_query_result = hl.query_table(
            f'{tables_path}/annotations.ht', families_ht.key).first().drop(*families_ht.key)
        ht = families_ht.annotate(**annotation_ht_query_result)
        ct, ann = ht.aggregate((hl.agg.count(), hl.agg.take(ht.row, 10)))
        logger.info(f'Annotated {ct} rows ({cls.__name__})')

        if clinvar_path_terms and quality_filter:
            ht = ht.annotate(genotypes=hl.if_else(
                cls._has_clivar_terms_expr(ht, clinvar_path_terms),
                ht.genotypes, ht.genotypes.filter(lambda x: ~ht.failQualityFamilies.contains(x.familyGuid))
            )).drop('failQualityFamilies')
            ht = ht.filter(ht.genotypes.size() > 0)

        ht = ht.annotate(
            familyGuids=ht.genotypes.group_by(lambda x: x.familyGuid).key_set(),
            genotypes=ht.genotypes.group_by(lambda x: x.individualGuid).map_values(lambda x: x[0]),
        )
        return cls._filter_annotated_table(
            ht, consequence_overrides=consequence_overrides, clinvar_path_terms=clinvar_path_terms,
            vcf_quality_filter=vcf_quality_filter, **kwargs), family_guid

    @classmethod
    def _get_family_table_filter_kwargs(cls, **kwargs):
        return {}

    @staticmethod
    def _get_families_annotation_fields(inheritance_mode):
        family_dict_fields = set()
        family_set_fields = set()
        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            family_dict_fields.add('compHetFamilyCarriers')
            if inheritance_mode == RECESSIVE:
                family_set_fields.add('recessiveFamilies')
        return family_set_fields, family_dict_fields

    @classmethod
    def _filter_entries_table(cls, ht, family_guid=None, sample_data=None, inheritance_mode=None, inheritance_filter=None,
                              genome_version=None, quality_filter=None, clinvar_path_terms=None, consequence_overrides=None,
                              table_name=None, **kwargs):
        table_name = family_guid or table_name
        logger.info(f'Initial count for {table_name}: {ht.count()}')

        ht, sample_id_index_map = cls._add_entry_sample_families(ht, sample_data, family_guid)

        if inheritance_mode == X_LINKED_RECESSIVE:
            x_chrom_interval = hl.parse_locus_interval(
                hl.get_reference(genome_version).x_contigs[0], reference_genome=genome_version)
            ht = ht.filter(cls.get_x_chrom_filter(ht, x_chrom_interval))

        ht = cls._filter_inheritance(
            ht, inheritance_mode, inheritance_filter or {}, sample_data, sample_id_index_map,
            consequence_overrides=consequence_overrides,
        )

        if quality_filter:
            ht = ht.annotate(failQualityFamilies=hl.set(ht.entries.filter(
                lambda gt: ~cls._genotype_passes_quality(gt, quality_filter)).map(lambda x: x.familyGuid)))
            if not clinvar_path_terms:
                ht = ht.transmute(families=ht.families.difference(ht.failQualityFamilies))
                ht = ht.filter(ht.families.size() > 0)

        if not family_guid:
            ht = ht.annotate(entries=ht.entries.filter(lambda x: ht.families.contains(x.familyGuid)))

        logger.info(f'Prefiltered {table_name} to {ht.count()} rows')

        return ht.transmute(
            genotypes=ht.entries.filter(lambda gt: hl.is_defined(gt.individualGuid)).map(lambda gt: gt.select(
                'sampleId', 'individualGuid', 'familyGuid',
                numAlt=hl.if_else(hl.is_defined(gt.GT), gt.GT.n_alt_alleles(), -1),
                **{cls.GENOTYPE_RESPONSE_KEYS.get(k, k): gt[field] for k, field in cls.GENOTYPE_FIELDS.items()}
            ))).select_globals()

    @classmethod
    def _add_entry_sample_families(cls, ht, sample_data, family_guid):
        sample_index_id_map = dict(enumerate(hl.eval(ht.sample_ids)))
        sample_id_index_map = {v: k for k, v in sample_index_id_map.items()}
        sample_individual_map = {s['sample_id']: s['individual_guid'] for s in sample_data}
        missing_samples = set(sample_individual_map.keys()) - set(sample_id_index_map.keys())
        if missing_samples:
            raise HTTPBadRequest(
                text=f'The following samples are available in seqr but missing the loaded data: {", ".join(missing_samples)}'
            )
        sample_index_individual_map = {
            sample_id_index_map[sample_id]: i_guid for sample_id, i_guid in sample_individual_map.items()
        }
        sample_index_family_map = {sample_id_index_map[s['sample_id']]: s['family_guid'] for s in sample_data}

        ht = ht.annotate(entries=hl.enumerate(ht.entries).map(
            lambda x: hl.or_else(x[1], cls._missing_entry(x[1])).annotate(
                sampleId=hl.dict(sample_index_id_map).get(x[0]),
                individualGuid=hl.dict(sample_index_individual_map).get(x[0]),
                familyGuid=hl.dict(sample_index_family_map).get(x[0]),
            )))
        ht = ht.annotate(families=hl.set(
            {family_guid} if family_guid else ht.entries.map(lambda x: x.familyGuid).filter(lambda x: hl.is_defined(x))
        ))

        return ht, sample_id_index_map

    @classmethod
    def _missing_entry(cls, entry):
        entry_type = dict(**entry.dtype)
        return hl.struct(**{k: hl.missing(v) for k, v in entry_type.items()})

    @classmethod
    def _filter_inheritance(cls, ht, inheritance_mode, inheritance_filter, sample_data, sample_id_index_map, **kwargs):
        if not (inheritance_filter or inheritance_mode):
            return ht

        if inheritance_mode == ANY_AFFECTED:
            affected_status_samples = {s['sample_id'] for s in sample_data if s['affected'] == AFFECTED}
            ht = ht.annotate(families=hl.set(ht.entries.filter(
                lambda x: hl.set(affected_status_samples).contains(x.sampleId) & cls.GENOTYPE_QUERY_MAP[HAS_ALT](x.GT)
            ).map(lambda x: x.familyGuid)))
        else:
            ht = cls._filter_families_inheritance(
                ht, inheritance_mode, inheritance_filter, sample_id_index_map, sample_data)

            if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
                ht = cls._annotate_possible_comp_hets(ht, sample_data)
        
                if inheritance_mode == RECESSIVE:
                    ht = ht.annotate(recessiveFamilies=ht.families, families=ht.compHetFamilyCarriers.key_set())
                    ht = cls._filter_families_inheritance(
                        ht, COMPOUND_HET, inheritance_filter, sample_id_index_map, sample_data)
                    ht = ht.annotate(
                        compHetFamilyCarriers=hl.dict(ht.compHetFamilyCarriers.items().filter(
                            lambda item: ht.families.contains(item[0])
                        )),
                        families=ht.families.union(ht.recessiveFamilies),
                    )
                else:
                    ht = ht.annotate(families=ht.families.intersection(ht.compHetFamilyCarriers.key_set()))

        return ht.filter(ht.families.size() > 0)

    @classmethod
    def _filter_families_inheritance(cls, ht, inheritance_mode, inheritance_filter, sample_id_index_map, sample_data):
        inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])
        individual_genotype_filter = inheritance_filter.get('genotype') or {}
        
        for s in sample_data:
            genotype = individual_genotype_filter.get(s['individual_guid']) or inheritance_filter.get(s['affected'])
            if inheritance_mode == X_LINKED_RECESSIVE and s['affected'] == UNAFFECTED and s['sex'] == MALE:
                genotype = REF_REF
            if genotype:
                entry_index = sample_id_index_map[s['sample_id']]
                ht = ht.annotate(families=hl.if_else(
                    cls.GENOTYPE_QUERY_MAP[genotype](ht.entries[entry_index].GT), ht.families,
                    ht.families.remove(ht.entries[entry_index].familyGuid)
                ))
            
        return ht
    
    @classmethod
    def _annotate_possible_comp_hets(cls, ht, sample_data):
        unaffected_samples = {s['sample_id'] for s in sample_data if s['affected'] == UNAFFECTED}

        return ht.annotate(compHetFamilyCarriers=hl.dict(ht.entries.group_by(lambda x: x.familyGuid).items().map(
            # group unaffected sample entries by family
            lambda item: (item[0], item[1].filter(lambda x: hl.set(unaffected_samples).contains(x.sampleId)))
        ).filter(
            # remove comp het variants where all unaffected individuals are carriers
            lambda item: hl.is_defined(item[0]) & ((item[1].size() < 2) | item[1].any(lambda x: cls.GENOTYPE_QUERY_MAP[REF_REF](x.GT)))
        ).map(lambda item: (
            # get carrier sample IDs per family
            item[0], hl.set(item[1].filter(lambda x: ~cls.GENOTYPE_QUERY_MAP[REF_REF](x.GT)).map(lambda x: x.sampleId))
        ))))

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
                                vcf_quality_filter=None, consequence_overrides=None, filtered_genes=None,
                                allowed_consequences=None, allowed_consequences_secondary=None, **kwargs):
        if custom_query:
            # In production: should either remove the "custom search" functionality,
            # or should come up with a simple json -> hail query parsing here
            raise NotImplementedError

        if filtered_genes:
            ht = cls._filter_gene_ids(ht, filtered_genes)

        ht = cls._filter_by_frequency(ht, frequencies, clinvar_path_terms)
        ht = cls._filter_by_in_silico(ht, in_silico)
        ht = cls._filter_by_annotations(ht, allowed_consequences, allowed_consequences_secondary, consequence_overrides)
        if vcf_quality_filter is not None:
            ht = cls._filter_vcf_filters(ht)

        return ht

    @staticmethod
    def _filter_gene_ids(ht, gene_ids):
        return ht.filter(ht.sortedTranscriptConsequences.any(lambda t: hl.set(gene_ids).contains(t.gene_id)))

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
        consequence_overrides = {CLINVAR_KEY: set(), HGMD_KEY: set()}
        for clinvar_filter in (pathogenicity or {}).get('clinvar', []):
            consequence_overrides[CLINVAR_KEY].update(CLINVAR_SIGNFICANCE_MAP.get(clinvar_filter, []))
        for hgmd_filter in (pathogenicity or {}).get('hgmd', []):
            consequence_overrides[HGMD_KEY].update(HGMD_CLASS_MAP.get(hgmd_filter, []))

        annotations = {k: v for k, v in (annotations or {}).items() if v}
        consequence_overrides.update({
            field: annotations.pop(field, None) for field in
            [SCREEN_KEY, SPLICE_AI_FIELD, NEW_SV_FIELD, STRUCTURAL_ANNOTATION_FIELD]
        })

        self._allowed_consequences = sorted({ann for anns in annotations.values() for ann in anns})
        if annotations_secondary:
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
            if freqs.get('af') is not None:
                af_field = populations_configs[pop].get('filter_af') or populations_configs[pop]['af']
                pop_filter = ht[pop][af_field] <= freqs['af']
                if has_path_override and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= (
                        cls._has_clivar_terms_expr(ht, clinvar_path_terms) &
                        (ht[pop][af_field] <= PATH_FREQ_OVERRIDE_CUTOFF)
                    )
            elif freqs.get('ac') is not None:
                ac_field = populations_configs[pop]['ac']
                if ac_field:
                    pop_filter = ht[pop][ac_field] <= freqs['ac']

            if freqs.get('hh') is not None:
                hom_field = populations_configs[pop]['hom']
                hemi_field = populations_configs[pop]['hemi']
                if hom_field:
                    hh_filter = ht[pop][hom_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter
                if hemi_field:
                    hh_filter = ht[pop][hemi_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter

            if pop_filter is not None:
                ht = ht.filter(hl.is_missing(ht[pop]) | pop_filter)

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
            ht_value = ht[score_path[0]][score_path[1]]
            if in_silico in PREDICTION_FIELD_ID_LOOKUP:
                score_filter = ht_value == PREDICTION_FIELD_ID_LOOKUP[in_silico].index(value)
            else:
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
        annotation_exprs = {}

        annotation_override_filter = cls._get_annotation_override_filter(ht, consequence_overrides)
        annotation_exprs['override_consequences'] = False if annotation_override_filter is None else annotation_override_filter

        allowed_consequence_ids = cls._get_allowed_consequence_ids(allowed_consequences)
        if allowed_consequence_ids:
            annotation_exprs['has_allowed_consequence'] = ht.sortedTranscriptConsequences.any(
                lambda tc: cls._is_allowed_consequence_filter(tc, allowed_consequence_ids))

        allowed_secondary_consequence_ids = cls._get_allowed_consequence_ids(allowed_consequences_secondary)
        if allowed_consequences_secondary:
            annotation_exprs['has_allowed_secondary_consequence'] = ht.sortedTranscriptConsequences.any(
                lambda tc: cls._is_allowed_consequence_filter(tc, allowed_secondary_consequence_ids))

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
            annotation_filters.append(hl.set({
                CLINVAR_SIG_MAP[s] for s in consequence_overrides[CLINVAR_KEY]
            }).contains(ht.clinvar.clinical_significance_id))
        if consequence_overrides.get(HGMD_KEY):
            allowed_classes = hl.set({HGMD_SIG_MAP[s] for s in consequence_overrides[HGMD_KEY]})
            annotation_filters.append(allowed_classes.contains(ht.hgmd.class_id))
        if consequence_overrides.get(SCREEN_KEY):
            allowed_consequences = hl.set({SCREEN_CONSEQUENCE_RANK_MAP[c] for c in consequence_overrides[SCREEN_KEY]})
            annotation_filters.append(allowed_consequences.intersection(hl.set(ht.screen.region_type_id)).size() > 0)
        if consequence_overrides.get(SPLICE_AI_FIELD):
            splice_ai = float(consequence_overrides[SPLICE_AI_FIELD])
            score_path = cls.PREDICTION_FIELDS_CONFIG[SPLICE_AI_FIELD]
            annotation_filters.append(ht[score_path[0]][score_path[1]] >= splice_ai)
        if consequence_overrides.get(STRUCTURAL_ANNOTATION_FIELD):
            allowed_sv_types = hl.set({SV_TYPE_MAP[t] for t in consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]})
            annotation_filters.append(allowed_sv_types.contains(ht.svType_id))

        if not annotation_filters:
            return None
        annotation_filter = annotation_filters[0]
        for af in annotation_filters[1:]:
            annotation_filter |= af
        return annotation_filter

    @classmethod
    def _get_clinvar_path_terms(cls, consequence_overrides):
        return [
            CLINVAR_SIG_MAP[f] for f in consequence_overrides[CLINVAR_KEY] if f in CLINVAR_PATH_SIGNIFICANCES
        ] if CLINVAR_KEY in cls.ANNOTATION_OVERRIDE_FIELDS else []

    @staticmethod
    def _has_clivar_terms_expr(ht, clinvar_terms):
        return hl.set(clinvar_terms).contains(ht.clinvar.clinical_significance_id)

    @staticmethod
    def _get_allowed_consequence_ids(allowed_consequences):
        return {
            SV_CONSEQUENCE_RANK_MAP[c] for c in (allowed_consequences or []) if SV_CONSEQUENCE_RANK_MAP.get(c)
        }

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequence_ids):
        return hl.set(allowed_consequence_ids).contains(tc.major_consequence_id)

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
        ch_ht = self._ht.annotate(
            gene_ids=hl.set(self._ht.sortedTranscriptConsequences.map(lambda t: t.gene_id)),
            compHetFamilies=self._ht.familyGuids.intersection(self._ht.compHetFamilyCarriers.key_set()),
        )

        if is_all_recessive_search:
            ch_ht = ch_ht.filter(hl.is_defined(ch_ht.compHetFamilies) & (ch_ht.compHetFamilies.size() > 0))

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
        ch_ht = ch_ht.annotate(family_guids=self._valid_comp_het_families_expr(ch_ht))

        ch_ht = ch_ht.filter(ch_ht.family_guids.size() > 0)
        ch_ht = ch_ht.annotate(
            v1=self._format_results(ch_ht.v1).annotate(**{
                'familyGuids': hl.array(ch_ht.family_guids), VARIANT_KEY_FIELD: ch_ht.v1[VARIANT_KEY_FIELD]
            }),
            v2=self._format_results(ch_ht.v2).annotate(**{
                'familyGuids': hl.array(ch_ht.family_guids), VARIANT_KEY_FIELD: ch_ht.v2[VARIANT_KEY_FIELD]
            }),
        )

        # Format pairs as lists and de-duplicate
        ch_ht = ch_ht.select(**{GROUPED_VARIANTS_FIELD: hl.sorted([ch_ht.v1, ch_ht.v2], key=lambda x: x._sort)})
        ch_ht = ch_ht.annotate(_sort=ch_ht[GROUPED_VARIANTS_FIELD][0]._sort)
        ch_ht = ch_ht.key_by(
            **{VARIANT_KEY_FIELD: hl.str(':').join(ch_ht[GROUPED_VARIANTS_FIELD].map(lambda v: v[VARIANT_KEY_FIELD]))})

        self._comp_het_ht = ch_ht.distinct()

    def _valid_comp_het_families_expr(self, ch_ht):
        both_var_families = ch_ht.v1.compHetFamilies.intersection(ch_ht.v2.compHetFamilies)
        # filter variants that are non-ref for any unaffected individual in both variants
        return both_var_families.filter(
            lambda family_guid: ch_ht.v1.compHetFamilyCarriers[family_guid].intersection(
                ch_ht.v2.compHetFamilyCarriers[family_guid]).size() == 0)

    def _format_results(self, ht):
        results = ht.annotate(
            genomeVersion=self._genome_version.replace('GRCh', ''),
            **{k: v(ht) for k, v in self.annotation_fields.items()},
        )
        results = results.annotate(
            **{k: v(self, results) for k, v in self.COMPUTED_ANNOTATION_FIELDS.items()},
        )
        return results.select(
            'genomeVersion', '_sort', *self.CORE_FIELDS,
            *set(list(self.COMPUTED_ANNOTATION_FIELDS.keys()) + list(self.annotation_fields.keys())))

    def search(self):
        if self._ht:
            ht = self._format_results(self._ht)
            if self._comp_het_ht:
                ht = ht.join(self._comp_het_ht, 'outer')
                ht = ht.transmute(_sort=hl.or_else(ht._sort, ht._sort_1))
        else:
            ht = self._comp_het_ht

        (total_results, collected) = ht.aggregate((hl.agg.count(), hl.agg.take(ht.row, self._num_results, ordering=ht._sort)))
        logger.info(f'Total hits: {total_results}. Fetched: {self._num_results}')

        hail_results = [
            self._json_serialize(row.get(GROUPED_VARIANTS_FIELD) or row.drop(GROUPED_VARIANTS_FIELD)) for row in collected
        ]
        return hail_results, total_results

    def _sort_order(self):
        sort_expressions = self._get_sort_expressions(XPOS_SORT_KEY)
        if self._sort != XPOS_SORT_KEY:
            sort_expressions = self._get_sort_expressions(self._sort) + sort_expressions
        return sort_expressions

    def _get_sort_expressions(self, sort):
        if sort in self.SORTS:
            return self.SORTS[sort](self._ht)
        elif sort == CONSEQUENCE_SORT_KEY:
            return self._consequence_sorts()

        sort_expression = None
        if sort in POPULATION_SORTS:
            pop_fields = [pop for pop in POPULATION_SORTS[sort] if pop in self.POPULATIONS]
            af_exprs = [self.population_expression(self._ht, pop).af for pop in pop_fields]
            if af_exprs:
                sort_expression = af_exprs[0]
                for af_expr in af_exprs[1:]:
                    sort_expression = hl.or_else(sort_expression, af_expr)

        elif sort in self.PREDICTION_FIELDS_CONFIG:
            prediction_path = self.PREDICTION_FIELDS_CONFIG[sort]
            sort_expression = -self._ht[prediction_path[0]][prediction_path[1]]

        elif sort == 'in_omim':
            sort_expression = -self._omim_sort(hl.set(set(self._sort_metadata)))

        elif self._sort_metadata:
            sort_expression = self._gene_rank_sort(self._sort_metadata)

        return [sort_expression] if sort_expression is not None else []

    def _consequence_sorts(self):
        return [hl.min(self._ht.sortedTranscriptConsequences.map(self.get_major_consequence_id))]

    def _omim_sort(self, omim_gene_set):
        return self._ht.sortedTranscriptConsequences.filter(lambda t: omim_gene_set.contains(t.gene_id)).size()

    def _gene_rank_sort(self, gene_ranks):
        return hl.min(self._ht.sortedTranscriptConsequences.map(lambda t: hl.dict(gene_ranks).get(t.gene_id)))

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
    POPULATIONS = {
        'callset': {'hom': None, 'hemi': None, 'het': None},
    }
    PREDICTION_FIELDS_CONFIG = {
        'fathmm': ('dbnsfp', 'FATHMM_pred_id'),
        'mut_taster': ('dbnsfp', 'MutationTaster_pred_id'),
        'polyphen': ('dbnsfp', 'Polyphen2_HVAR_pred_id'),
        'revel': ('dbnsfp', 'REVEL_score'),
        'sift': ('dbnsfp', 'SIFT_pred_id'),
    }
    TRANSCRIPT_FIELDS = BaseHailTableQuery.TRANSCRIPT_FIELDS + [
        'amino_acids', 'biotype', 'canonical', 'codons', 'hgvsc', 'hgvsp', 'lof', 'lof_filter', 'lof_flags', 'lof_info',
        'transcript_id', 'transcript_rank',
    ]
    ANNOTATION_OVERRIDE_FIELDS = [CLINVAR_KEY]

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid']
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'clinvar': lambda r: r.clinvar.select(
            'alleleId', 'goldStars',
            clinicalSignificance=hl.array(CLINVAR_SIGNIFICANCES)[r.clinvar.clinical_significance_id],
        ),
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),  # In production - format in main HT?
        'mainTranscriptId': lambda r: r.sortedTranscriptConsequences[0].transcript_id,
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)

    SORTS = {
        PATHOGENICTY_SORT_KEY: lambda r: [hl.or_else(
            # sort variants absent from clinvar between uncertain and benign
            r.clinvar.clinical_significance_id, CLINVAR_SIG_BENIGN_OFFSET,
        )],
    }
    SORTS.update(BaseHailTableQuery.SORTS)
    SORTS[PATHOGENICTY_HGMD_SORT_KEY] = SORTS[PATHOGENICTY_SORT_KEY]

    def _selected_main_transcript_expr(self, results):
        get_matching_transcripts = lambda allowed_values, get_field: results.sortedTranscriptConsequences.filter(
            lambda t: hl.set(allowed_values).contains(get_field(t)))

        gene_transcripts = None
        if self._filtered_genes:
            gene_transcripts = get_matching_transcripts(self._filtered_genes, lambda t: t.gene_id)

        consequence_transcripts = None
        if self._allowed_consequences:
            consequence_transcripts = get_matching_transcripts(self._allowed_consequences, self.get_major_consequence)
            if self._allowed_consequences_secondary:
                consequence_transcripts = hl.if_else(
                    consequence_transcripts.size() > 0, consequence_transcripts,
                    get_matching_transcripts(self._allowed_consequences_secondary, self.get_major_consequence))

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
            matched_transcripts = results.sortedTranscriptConsequences

        return matched_transcripts[0]

    def _selected_main_transcript_id_expr(self, results):
        selected_transcript = self._selected_main_transcript_expr(results)
        return hl.or_missing(
            selected_transcript != results.sortedTranscriptConsequences[0], selected_transcript.transcript_id,
        )

    COMPUTED_ANNOTATION_FIELDS = {
        'selectedMainTranscriptId': _selected_main_transcript_id_expr,
    }

    @classmethod
    def import_filtered_table(cls, data_type, sample_data, intervals=None, exclude_intervals=False, **kwargs):
        ht, family_guid = super(BaseVariantHailTableQuery, cls).import_filtered_table(
            data_type, sample_data, intervals=None if exclude_intervals else intervals,
            excluded_intervals=intervals if exclude_intervals else None, **kwargs)
        ht = ht.key_by(VARIANT_KEY_FIELD)
        return ht, family_guid

    @classmethod
    def _filter_entries_table(cls, ht, excluded_intervals=None, variant_ids=None, genome_version=None, **kwargs):
        if excluded_intervals or variant_ids:
            logger.info(f'Unfiltered count: {ht.count()}')

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
            ht = ht.filter(hl.set(rs_ids).contains(ht.rsid))
        return super(BaseVariantHailTableQuery, cls)._filter_annotated_table(ht, **kwargs)

    @staticmethod
    def get_major_consequence_id(transcript):
        return transcript.sorted_consequence_ids[0]

    @staticmethod
    def get_major_consequence(transcript):
        return hl.array(CONSEQUENCE_RANKS)[transcript.sorted_consequence_ids[0]]

    @staticmethod
    def _get_allowed_consequence_ids(allowed_consequences):
        return {
            CONSEQUENCE_RANK_MAP[c] for c in (allowed_consequences or []) if CONSEQUENCE_RANK_MAP.get(c)
        }

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequence_ids):
        return hl.set(allowed_consequence_ids).intersection(hl.set(tc.sorted_consequence_ids)).size() > 0

    def _consequence_sorts(self):
        return super(BaseVariantHailTableQuery, self)._consequence_sorts() + [
            self._selected_main_transcript_expr(self._ht).sorted_consequence_ids[0],
        ]

    def _omim_sort(self, omim_gene_set):
        main_transcript = self._selected_main_transcript_expr(self._ht)
        return super(BaseVariantHailTableQuery, self)._omim_sort(omim_gene_set) + hl.if_else(
            hl.is_missing(main_transcript.sorted_consequence_ids) | omim_gene_set.contains(main_transcript.gene_id),
            10, 0)


class VariantHailTableQuery(BaseVariantHailTableQuery):

    GENOTYPE_FIELDS = {f.lower(): f for f in ['AB', 'AD', 'PL']}
    GENOTYPE_FIELDS.update(BaseVariantHailTableQuery.GENOTYPE_FIELDS)
    POPULATIONS = {
        'topmed': {'hemi': None, 'het': None},
        'exac': {
            'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi', 'het': None,
        },
        'gnomad_exomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
        GNOMAD_GENOMES_FIELD: {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
    }
    POPULATIONS.update(BaseVariantHailTableQuery.POPULATIONS)
    PREDICTION_FIELDS_CONFIG = {
        'cadd': ('cadd', 'PHRED'),
        'eigen': ('eigen', 'Eigen_phred'),
        'gnomad_noncoding': ('gnomad_non_coding_constraint', 'z_score'),
        'mpc': ('mpc', 'MPC'),
        'primate_ai': ('primate_ai', 'score'),
        'splice_ai': ('splice_ai', 'delta_score'),
        'splice_ai_consequence': ('splice_ai', 'splice_consequence'),
    }
    PREDICTION_FIELDS_CONFIG.update(BaseVariantHailTableQuery.PREDICTION_FIELDS_CONFIG)
    ANNOTATION_OVERRIDE_FIELDS = [HGMD_KEY, SPLICE_AI_FIELD, SCREEN_KEY] + BaseVariantHailTableQuery.ANNOTATION_OVERRIDE_FIELDS

    BASE_ANNOTATION_FIELDS = {
        'hgmd': lambda r: r.hgmd.select('accession', **{'class': hl.array(HGMD_SIGNIFICANCES)[r.hgmd.class_id]}),
        'originalAltAlleles': lambda r: r.originalAltAlleles.map(lambda a: a.split('-')[-1]), # In production - format in main HT
        'screenRegionType': lambda r: hl.or_missing(
            r.screen.region_type_id.size() > 0,
            hl.array(SCREEN_CONSEQUENCES)[r.screen.region_type_id[0]]),
    }
    BASE_ANNOTATION_FIELDS.update(BaseVariantHailTableQuery.BASE_ANNOTATION_FIELDS)

    SORTS = deepcopy(BaseVariantHailTableQuery.SORTS)
    SORTS[PATHOGENICTY_HGMD_SORT_KEY] = lambda r: BaseVariantHailTableQuery.SORTS[PATHOGENICTY_SORT_KEY](r) + [r.hgmd.class_id]

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
            logger.info(f'No AF filter count: {ht.count()}')
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
    POPULATIONS.update(BaseVariantHailTableQuery.POPULATIONS)
    PREDICTION_FIELDS_CONFIG = {
        'apogee': ('mitimpact', 'score'),
        'hmtvar': ('hmtvar', 'score'),
        'mitotip': ('mitotip', 'trna_prediction_id'),
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
    return genotypes.values().any(lambda g: (g.numAlt > 0) & hl.is_missing(g[field]))


def _get_genotype_override_field(genotypes, default, field, agg):
    return hl.if_else(
        _no_genotype_override(genotypes, field), default, agg(genotypes.values().map(lambda g: g[field]))
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
    ANNOTATION_OVERRIDE_FIELDS = [STRUCTURAL_ANNOTATION_FIELD, NEW_SV_FIELD]

    SORTS = {
        'size': lambda r: [hl.if_else(
            r.interval.start.contig == r.interval.end.contig, r.interval.start.position - r.interval.end.position, -50,
        )],
    }
    SORTS.update(BaseHailTableQuery.SORTS)

    @classmethod
    def import_filtered_table(cls, data_type, sample_data, intervals=None, exclude_intervals=False, **kwargs):
        ht, family_guid = super(BaseSvHailTableQuery, cls).import_filtered_table(data_type, sample_data, **kwargs)
        if intervals:
            interval_filter = hl.array(intervals).all(lambda interval: not interval.overlaps(ht.interval)) \
                if exclude_intervals else hl.array(intervals).any(lambda interval: interval.overlaps(ht.interval))
            ht = ht.filter(interval_filter)
        return ht, family_guid

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return ht.interval.overlaps(x_interval)

    @staticmethod
    def get_major_consequence_id(transcript):
        return transcript.major_consequence_id

    @staticmethod
    def get_major_consequence(transcript):
        return hl.array(SV_CONSEQUENCE_RANKS)[transcript.major_consequence_id]

    @classmethod
    def _filter_inheritance(cls, ht, *args, consequence_overrides=None):
        ht = super(BaseSvHailTableQuery, cls)._filter_inheritance(ht, *args)
        if consequence_overrides[NEW_SV_FIELD]:
            ht = ht.annotate(families=ht.families.intersection(hl.set(
                ht.entries.filter(lambda x: x.newCall).map(lambda x: x.familyGuid)
            )))
            ht = ht.filter(ht.families.size() > 0)
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
    COMPUTED_ANNOTATION_FIELDS = {
        'transcripts': lambda self, r: hl.if_else(
            _no_genotype_override(r.genotypes, 'geneIds'), r.transcripts, hl.bind(
                lambda gene_ids: hl.dict(r.transcripts.items().filter(lambda t: gene_ids.contains(t[0]))),
                r.genotypes.values().flatmap(lambda g: g.geneIds)
            ),
        )
    }

    @classmethod
    def _missing_entry(cls, entry):
        #  gCNV data has no ref/ref calls so a missing entry indicates that call
        return super(GcnvHailTableQuery, cls)._missing_entry(entry).annotate(GT=hl.Call([0, 0]))

    @classmethod
    def _filter_vcf_filters(cls, ht):
        return ht

    @classmethod
    def _filter_annotated_table(cls, ht, **kwargs):
        # Remove once data is reloaded
        ht = ht.annotate(
            xpos=hl.dict(CHROM_TO_XPOS_OFFSET).get(ht.interval.start.contig.replace('^chr', '')) + ht.interval.start.position,
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

    SV_MERGE_FIELDS = {'interval', 'svType_id', 'rg37_locus_end', 'strvctvre', 'sv_callset',}
    VARIANT_MERGE_FIELDS = {'alleles', 'callset', 'clinvar', 'dbnsfp', 'filters', 'locus', 'rsid',}
    MERGE_FIELDS = {
        GCNV_KEY: SV_MERGE_FIELDS, SV_KEY: SV_MERGE_FIELDS,
        VARIANT_DATASET: VARIANT_MERGE_FIELDS, MITO_DATASET: VARIANT_MERGE_FIELDS,
    }

    def __init__(self, data_type, *args, **kwargs):
        self._data_types = data_type
        self.POPULATIONS = {}
        self.PREDICTION_FIELDS_CONFIG = {}
        self.BASE_ANNOTATION_FIELDS = {}
        self.COMPUTED_ANNOTATION_FIELDS = {}
        self.SORTS = {}

        self.CORE_FIELDS = set()
        for cls in [QUERY_CLASS_MAP[dt] for dt in self._data_types]:
            self.POPULATIONS.update(cls.POPULATIONS)
            self.PREDICTION_FIELDS_CONFIG.update(cls.PREDICTION_FIELDS_CONFIG)
            self.BASE_ANNOTATION_FIELDS.update(cls.BASE_ANNOTATION_FIELDS)
            self.COMPUTED_ANNOTATION_FIELDS.update(cls.COMPUTED_ANNOTATION_FIELDS)
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
        return hl.or_missing(
            hl.dict(DATA_TYPE_POPULATIONS_MAP)[r.dataType].contains(population),
            super(MultiDataTypeHailTableQuery, self).population_expression(r, population),
        )

    @classmethod
    def import_filtered_table(cls, data_type, sample_data, **kwargs):
        data_type_0 = data_type[0]

        ht, family_guid = QUERY_CLASS_MAP[data_type_0].import_filtered_table(data_type_0, sample_data[data_type_0], **kwargs)
        ht = ht.annotate(dataType=data_type_0)

        all_type_merge_fields = {'dataType', 'familyGuids', 'override_consequences', 'rg37_locus', 'xpos'}
        family_set_fields, family_dict_fields = cls._get_families_annotation_fields(kwargs['inheritance_mode'])
        all_type_merge_fields.update(family_set_fields)
        all_type_merge_fields.update(family_dict_fields)

        merge_fields = deepcopy(cls.MERGE_FIELDS[data_type_0])
        for dt in data_type[1:]:
            data_type_cls = QUERY_CLASS_MAP[dt]
            sub_ht, new_family_guid = data_type_cls.import_filtered_table(dt, sample_data[dt], **kwargs)
            if new_family_guid != family_guid:
                family_guid = None
            sub_ht = sub_ht.annotate(dataType=dt)
            ht = ht.join(sub_ht, how='outer')

            new_merge_fields = cls.MERGE_FIELDS[dt]
            to_merge = merge_fields.intersection(new_merge_fields)
            to_merge.update(all_type_merge_fields)
            merge_fields.update(new_merge_fields)

            transmute_expressions = {k: hl.or_else(ht[k], ht[f'{k}_1']) for k in to_merge}
            transmute_expressions.update(cls._merge_nested_structs(ht, 'sortedTranscriptConsequences', 'element_type'))
            transmute_expressions.update(cls._merge_nested_structs(ht, 'genotypes', 'value_type', map_func='map_values'))
            ht = ht.transmute(**transmute_expressions)

        return ht, family_guid

    @staticmethod
    def _merge_nested_structs(ht, field, sub_type, map_func='map'):
        struct_type = dict(**getattr(ht[field].dtype, sub_type))
        new_struct_type = dict(**getattr(ht[f'{field}_1'].dtype, sub_type))
        is_same_type = struct_type == new_struct_type
        struct_type.update(new_struct_type)

        def format_merged(merge_field):
            table_field = ht[merge_field]
            if is_same_type:
                return table_field
            return getattr(table_field, map_func)(
                lambda x: x.select(**{k: x.get(k, hl.missing(v)) for k, v in struct_type.items()})
            )

        return {field: hl.or_else(format_merged(field), format_merged(f'{field}_1'))}


class AllSvHailTableQuery(MultiDataTypeHailTableQuery, BaseSvHailTableQuery):

    DATA_TYPE_ANNOTATION_FIELDS = ['end', 'pos']

    def __init__(self, *args, **kwargs):
        super(AllSvHailTableQuery, self).__init__(*args, **kwargs)
        self.COMPUTED_ANNOTATION_FIELDS = {
            k: lambda _self, r: hl.or_else(v(_self, r), r[k])
            for k, v in self.COMPUTED_ANNOTATION_FIELDS.items()
        }


class AllVariantHailTableQuery(MultiDataTypeHailTableQuery, VariantHailTableQuery):
    pass


class AllDataTypeHailTableQuery(AllVariantHailTableQuery):

    DATA_TYPE_ANNOTATION_FIELDS = ['chrom', 'pos', 'end']

    @staticmethod
    def get_major_consequence_id(transcript):
        return hl.if_else(
            hl.is_defined(transcript.sorted_consequence_ids),
            BaseVariantHailTableQuery.get_major_consequence_id(transcript),
            BaseSvHailTableQuery.get_major_consequence_id(transcript),
        )

    @staticmethod
    def get_major_consequence(transcript):
        return hl.if_else(
            hl.is_defined(transcript.sorted_consequence_ids),
            BaseVariantHailTableQuery.get_major_consequence(transcript),
            BaseSvHailTableQuery.get_major_consequence(transcript),
        )

    def _valid_comp_het_families_expr(self, ch_ht):
        valid_families = super(AllDataTypeHailTableQuery, self)._valid_comp_het_families_expr(ch_ht)
        invalid_families = self._invalid_hom_alt_individual_families(ch_ht.v1, ch_ht.v2).union(
            self._invalid_hom_alt_individual_families(ch_ht.v2, ch_ht.v1)
        )
        return valid_families.difference(invalid_families)

    @staticmethod
    def _invalid_hom_alt_individual_families(v1, v2):
        # SNPs overlapped by trans deletions may be incorrectly called as hom alt, and should be
        # considered comp hets with said deletions. Any other hom alt variants are not valid comp hets
        return hl.if_else(
            hl.is_defined(v1.locus) & hl.set(SV_DEL_INDICES).contains(v2.svType_id) &
            (v2.interval.start.position <= v1.locus.position) & (v1.locus.position <= v2.interval.end.position),
            hl.empty_set(hl.tstr),
            hl.set(v1.genotypes.values().filter(lambda g: g.numAlt == 2).map(lambda g: g.familyGuid)),
        )

    def _consequence_sorts(self):
        rank_sort, variant_sort = super(AllDataTypeHailTableQuery, self)._consequence_sorts()
        is_sv = hl.is_defined(self._ht.svType_id)
        return [
            hl.if_else(is_sv, SV_CONSEQUENCE_RANK_OFFSET, rank_sort),
            hl.if_else(is_sv, rank_sort, variant_sort),
        ]
