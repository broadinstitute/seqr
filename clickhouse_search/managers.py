from clickhouse_backend import models
from collections import OrderedDict, defaultdict

from django.db.models import F, Manager, QuerySet, Q, Value
from django.db.models.expressions import Col
from django.db.models.functions import Cast
from django.db.models.sql.constants import INNER

from clickhouse_search.backend.fields import NestedField, NamedTupleField
from clickhouse_search.backend.functions import Array, ArrayConcat, ArrayDistinct, ArrayFilter, ArrayFold, \
    ArrayIntersect, ArrayJoin, ArrayMap, ArraySort, ArraySymmetricDifference, CrossJoin, GroupArray, GroupArrayArray, \
    GroupArrayIntersect, DictGet, If, MapLookup, NullIf, Plus, SubqueryJoin, SubqueryTable, Tuple, TupleConcat
from seqr.models import Sample
from seqr.utils.search.constants import INHERITANCE_FILTERS, ANY_AFFECTED, AFFECTED, UNAFFECTED, MALE_SEXES, \
    X_LINKED_RECESSIVE, REF_REF, REF_ALT, ALT_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, SCREEN_KEY, UTR_ANNOTATOR_KEY, \
    EXTENDED_SPLICE_KEY, MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY, CLINVAR_KEY, HGMD_KEY, SV_ANNOTATION_TYPES, \
    EXTENDED_SPLICE_REGION_CONSEQUENCE, CLINVAR_PATH_RANGES, CLINVAR_PATH_SIGNIFICANCES, PATH_FREQ_OVERRIDE_CUTOFF, \
    HGMD_CLASS_FILTERS
from seqr.utils.xpos_utils import get_xpos


class AnnotationsQuerySet(QuerySet):

    TRANSCRIPT_CONSEQUENCE_FIELD = 'sorted_transcript_consequences'
    GENE_CONSEQUENCE_FIELD = 'gene_consequences'
    FILTERED_CONSEQUENCE_FIELD = 'filtered_transcript_consequences'

    ENTRY_FIELDS = ['familyGuids', 'genotypes', 'clinvar']

    SELECTED_GENE_FIELD = 'selectedGeneId'

    @property
    def annotation_values(self):
        seqr_pops = []
        population_fields = [*self.model.POPULATION_FIELDS]
        for i, (name, subfields) in enumerate(self.model.SEQR_POPULATIONS):
            exprs = [Plus(f'seqrPop__{i*2}', f'seqrPop__{i*2+1}')]
            sub_output_fields = [('ac', models.UInt32Field())]
            if 'hom' in subfields:
                exprs.append(Plus(f'seqrPop__{i*2+2}', f'seqrPop__{i*2+3}'))
                sub_output_fields.append(('hom', models.UInt32Field()))
            seqr_pops.append(Tuple(*exprs))
            population_fields.append((name, NamedTupleField(sub_output_fields)))

        annotations = {
            **{key: Value(value) for key, value in self.model.ANNOTATION_CONSTANTS.items()},
            **{field.db_column: F(field.name) for field in self.model._meta.local_fields if field.db_column and field.name != field.db_column},
            'populations': TupleConcat(F('populations'), Tuple(*seqr_pops), output_field=NamedTupleField(population_fields)),
        }

        if self.model.sorted_transcript_consequences.field.group_by_key:
            annotations.update({
                'mainTranscriptId': F('sorted_transcript_consequences__0__transcriptId'),
                'selectedMainTranscriptId': Value(None, output_field=models.StringField(null=True)),
                'transcripts': annotations.pop('sortedTranscriptConsequences'),
            })

        return annotations

    @property
    def annotation_fields(self):
        return [
            field.name for field in self.model._meta.local_fields
            if (field.db_column or field.name) not in self.annotation_values and field.name != self.TRANSCRIPT_CONSEQUENCE_FIELD
        ] + self.ENTRY_FIELDS

    @property
    def prediction_fields(self):
        return set(dict(self.model.PREDICTION_FIELDS).keys())

    @property
    def transcript_fields(self):
        transcript_field_configs = getattr(self.model, 'SORTED_TRANSCRIPT_CONSQUENCES_FIELDS', self.model.TRANSCRIPTS_FIELDS)
        return set(dict(transcript_field_configs).keys())


    def subquery_join(self, subquery, join_key='key'):
        #  Add key to intermediate select if not already present
        join_field = next(field for field in subquery.model._meta.fields if field.name == join_key)
        if join_key not in subquery.query.values_select:
            subquery.query.values_select = tuple([join_key, *subquery.query.values_select])
            subquery.query.select = tuple([Col(subquery.model._meta.db_table, join_field), *subquery.query.select])

        # Add the join operation to the query
        table = SubqueryTable(subquery)
        parent_alias = self.query.get_initial_alias()
        self.query.join(SubqueryJoin(
            table_name=table.table_alias,
            parent_alias=parent_alias,
            table_alias=None,
            join_type=INNER,
            join_field=join_field,
            nullable=False,
        ))
        self.query.alias_map[parent_alias] = table

        return self.annotate(**self._get_subquery_annotations(subquery, table.table_alias, join_key=join_key))

    def _get_subquery_annotations(self, subquery, alias, join_key=None):
        annotations = {
            col.target.name: Col(alias, col.target) for col in subquery.query.select
            if col.target.name != join_key
        }
        for name, field in subquery.query.annotation_select.items():
            target = field.output_field.clone()
            target.column = name
            annotations[name] = Col(alias, target)

        return annotations

    def cross_join(self, query, alias, join_query, join_alias, select_fields=None, select_values=None, conditional_selects=None):
        query = self._get_join_query_values(query, alias, select_fields, select_values, conditional_selects)
        join_query = self._get_join_query_values(join_query, join_alias, select_fields, select_values, conditional_selects)
        self.query.join(CrossJoin(query, alias, join_query, join_alias))

        annotations = self._get_subquery_annotations(query, alias)
        annotations.update(self._get_subquery_annotations(join_query, join_alias))

        return self.annotate(**annotations)

    def _get_join_query_values(self, query, alias, select_fields, select_values, conditional_selects):
        query_select = {**(select_values or {})}
        for select_func in (conditional_selects or []):
            query_select.update(select_func(query, prefix=f'{alias}_'))
        return query.values(
            **{f'{alias}_{field}': F(field) for field in select_fields or []},
            **{f'{alias}_{field}': value for field, value in query_select.items()},
        )

    def search(self, parsed_locus=None, **kwargs):
        parsed_locus = parsed_locus or {}
        results = self
        results = self._filter_variant_ids(results, **parsed_locus)
        results = self._filter_frequency(results, **kwargs)
        results = self._filter_in_silico(results, **kwargs)
        results = self._filter_annotations(results, **parsed_locus, **kwargs)
        return results

    def result_values(self):
        values = {k: v for k, v in self.annotation_values.items() if k != 'populations'}

        values.update(self._conditional_selected_transcript_values(self))

        return self.values(*self.annotation_fields, **values).annotate(
            populations=self.annotation_values['populations']
        )


    def _conditional_selected_transcript_values(self, query, prefix=''):
        consequence_field = next((
            field for field in [self.FILTERED_CONSEQUENCE_FIELD, self.GENE_CONSEQUENCE_FIELD] if query.has_annotation(field)
        ), None)
        if not consequence_field:
            return {}
        if not hasattr(self.model, 'SORTED_TRANSCRIPT_CONSQUENCES_FIELDS'):
            return {'selectedMainTranscriptId': NullIf(
                NullIf(F(f'{consequence_field}__0__transcriptId'), Value('')), f'{prefix}mainTranscriptId',
                output_field=models.StringField(null=True),
            )}
        if consequence_field == self.FILTERED_CONSEQUENCE_FIELD:
            return {'selectedTranscript':  F(f'{self.FILTERED_CONSEQUENCE_FIELD}__0')}
        return {self.SELECTED_GENE_FIELD: F(f'{self.GENE_CONSEQUENCE_FIELD}__0__geneId')}

    def search_compound_hets(self, primary_q, secondary_q, carrier_field):
        primary_gene_field = f'primary_{self.SELECTED_GENE_FIELD}'
        secondary_gene_field = f'secondary_{self.SELECTED_GENE_FIELD}'
        primary_q = primary_q.explode_gene_id(primary_gene_field)
        secondary_q = secondary_q.explode_gene_id(secondary_gene_field)

        select_fields = [*self.annotation_fields, self.SELECTED_GENE_FIELD]
        if carrier_field:
            select_fields.append(carrier_field)

        results = self.cross_join(
            query=primary_q, alias='primary', join_query=secondary_q, join_alias='secondary',
            select_fields=select_fields, select_values={
                **self.annotation_values,
            }, conditional_selects=[self._conditional_selected_transcript_values],
        )
        return results.filter(
            **{primary_gene_field: F(secondary_gene_field)}
        ).exclude(primary_variantId=F('secondary_variantId'))

    @classmethod
    def _filter_variant_ids(cls, results, variant_ids=None, rs_ids=None, **kwargs):
        if variant_ids:
            results = results.filter(
                variant_id__in=[f'{chrom}-{pos}-{ref}-{alt}' for chrom, pos, ref, alt in variant_ids]
            )

        if rs_ids:
            results = results.filter(rsid__in=rs_ids)

        return results

    @property
    def populations(self):
        return {
            population: {subfield for subfield, _ in field.base_fields}
            for population, field in self.model.POPULATION_FIELDS
        }

    def _filter_frequency(self, results, freqs=None, pathogenicity=None, **kwargs):
        frequencies =  freqs or {}
        clinvar_override_q = self._clinvar_path_q(pathogenicity)

        for population, pop_filter in frequencies.items():
            pop_subfields = self.populations.get(population)
            if not pop_subfields:
                continue

            if pop_filter.get('af') is not None and pop_filter['af'] < 1:
                af_field = next(field for field in ['filter_af', 'af'] if field in pop_subfields)
                if af_field:
                    af_q = Q(**{
                        f'populations__{population}__{af_field}__lte': pop_filter['af'],
                    })
                    if clinvar_override_q and pop_filter['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                        af_q |= (clinvar_override_q & Q(**{
                            f'populations__{population}__{af_field}__lte': PATH_FREQ_OVERRIDE_CUTOFF,
                        }))
                    results = results.filter(af_q)
            elif pop_filter.get('ac') is not None:
                results = results.filter(**{f'populations__{population}__ac__lte': pop_filter['ac']})

            if pop_filter.get('hh') is not None:
                for subfield in ['hom', 'hemi']:
                    if subfield not in pop_subfields:
                        continue
                    hh_q = Q(**{
                        f'populations__{population}__{subfield}__lte': pop_filter['hh'],
                    })
                    if clinvar_override_q:
                        hh_q |= clinvar_override_q
                    results = results.filter(hh_q)

        return results

    def _filter_in_silico(self, results, in_silico=None, **kwargs):
        in_silico_q = None
        for score, value in (in_silico or {}).items():
            score_q = self._get_in_silico_score_q(score, value)
            if in_silico_q is None:
                in_silico_q = score_q
            elif score_q:
                in_silico_q |= score_q

        if in_silico_q and not in_silico.get('requireScore', False):
            in_silico_q |= Q(**{f'predictions__{score}__isnull': True for score in in_silico.keys() if score in self.prediction_fields})

        if in_silico_q:
            results = results.filter(in_silico_q)
        elif any(val for val in (in_silico or {}).values()) and in_silico.get('requireScore'):
            #  In silico filters restrict search to other dataset types
            results = results.none()

        return results

    def _get_in_silico_score_q(self, score, value):
        if not (score in self.prediction_fields and value):
            return None
        score_column = f'predictions__{score}'
        try:
            return Q(**{f'{score_column}__gte': float(value)})
        except ValueError:
            return Q(**{score_column: value})

    def _filter_annotations(self, results, annotations=None, pathogenicity=None, exclude=None, gene_ids=None, **kwargs):
        if gene_ids:
            results = results.annotate(**{
                self.GENE_CONSEQUENCE_FIELD: ArrayFilter(self.TRANSCRIPT_CONSEQUENCE_FIELD, conditions=[{
                    'geneId': (gene_ids, 'has({value}, {field})'),
                }]),
            })
            results = results.filter(gene_consequences__not_empty=True)

        filter_qs, transcript_filters = self._parse_annotation_filters(annotations) if annotations else ([], [])

        hgmd = (pathogenicity or {}).get(HGMD_KEY)
        if hgmd and hasattr(self.model, 'hgmd'):
            filter_qs.append(self._hgmd_filter_q(hgmd))

        clinvar = (pathogenicity or {}).get(CLINVAR_KEY)
        if clinvar:
            filter_qs.append(self._clinvar_filter_q(clinvar))

        exclude_clinvar = (exclude or {}).get('clinvar')
        if exclude_clinvar:
            results = results.exclude(self._clinvar_filter_q(exclude_clinvar))

        if not (filter_qs or transcript_filters):
            if any(val for val in (annotations or {}).values()) or any(val for val in (pathogenicity or {}).values()):
                #  Annotation filters restrict search to other dataset types
                results = results.none()
            return results

        filter_q = filter_qs[0] if filter_qs else None
        for q in filter_qs[1:]:
            filter_q |= q
        if filter_q:
            results = results.annotate(passes_annotation=filter_q)
            filter_q = Q(passes_annotation=True)

        if transcript_filters:
            consequence_field = self.GENE_CONSEQUENCE_FIELD if gene_ids else self.TRANSCRIPT_CONSEQUENCE_FIELD
            results = results.annotate(**{
                self.FILTERED_CONSEQUENCE_FIELD: ArrayFilter(consequence_field, conditions=transcript_filters),
            })
            transcript_q = Q(filtered_transcript_consequences__not_empty=True)
            if filter_q:
                filter_q |= transcript_q
            else:
                filter_q = transcript_q

        return results.filter(filter_q)

    def _parse_annotation_filters(self, annotations):
        filter_qs = []
        filters_by_field = {}
        allowed_consequences = []
        transcript_field_filters = {}
        for field, value in annotations.items():
            if field == UTR_ANNOTATOR_KEY:
                transcript_field_filters['fiveutrConsequence'] = (value, 'hasAny({value}, [{field}])')
            elif field == EXTENDED_SPLICE_KEY:
                if EXTENDED_SPLICE_REGION_CONSEQUENCE in value:
                    transcript_field_filters['extendedIntronicSpliceRegionVariant'] = (1, '{field} = {value}')
            elif field in [MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY]:
                filters_by_field[f'sorted_{field}_consequences'] = ('{field}__array_exists', {
                    'consequenceTerms': (value, 'hasAny({value}, {field})'),
                })
            elif field == SPLICE_AI_FIELD:
                splice_ai_q = self._get_in_silico_score_q(SPLICE_AI_FIELD, value)
                if splice_ai_q:
                    filter_qs.append(splice_ai_q)
            elif field == SCREEN_KEY:
                filters_by_field['screen_region_type'] = ('{field}__in', value)
            elif field not in SV_ANNOTATION_TYPES:
                allowed_consequences += value

        filter_qs += [
            Q(**{lookup_template.format(field=field): value})
            for field, (lookup_template, value) in filters_by_field.items() if hasattr(self.model, field)
        ]
        transcript_filters = [
            {field: value} for field, value in transcript_field_filters.items() if field in self.transcript_fields
        ]

        non_canonical_consequences = [c for c in allowed_consequences if not c.endswith('__canonical')]
        if non_canonical_consequences:
            transcript_filters.append(self._consequence_term_filter(non_canonical_consequences))

        canonical_consequences = [
            c.replace('__canonical', '') for c in allowed_consequences if c.endswith('__canonical')
        ]
        if canonical_consequences and 'canonical' in self.transcript_fields:
            transcript_filters.append(
                self._consequence_term_filter(canonical_consequences, canonical=(0, '{field} > {value}')),
            )

        return filter_qs, transcript_filters

    @staticmethod
    def _consequence_term_filter(consequences, **kwargs):
        return {'consequenceTerms': (consequences, 'hasAny({value}, {field})'), **kwargs}

    @staticmethod
    def _hgmd_filter_q(hgmd):
        min_class = next((class_name for value, class_name in HGMD_CLASS_FILTERS if value in hgmd), None)
        max_class = next((class_name for value, class_name in reversed(HGMD_CLASS_FILTERS) if value in hgmd), None)
        if 'hgmd_other' in hgmd:
            min_class = min_class or 'DP'
            max_class = None
        if min_class == max_class:
            return Q(hgmd__classification=min_class)
        elif min_class and max_class:
            return Q(hgmd__classification__range=(min_class, max_class))
        return Q(hgmd__classification__gt=min_class)

    @classmethod
    def _clinvar_filter_q(cls, clinvar_filters, _get_range_q=None):
        ranges = [[None, None]]
        for path_filter, start, end in CLINVAR_PATH_RANGES:
            if path_filter in clinvar_filters:
                ranges[-1][1] = end
                if ranges[-1][0] is None:
                    ranges[-1][0] = start
            elif ranges[-1] != [None, None]:
                ranges.append([None, None])
        ranges = [r for r in ranges if r[0] is not None]

        clinvar_qs = [(_get_range_q or cls._clinvar_range_q)(path_range) for path_range in ranges]
        clinvar_q = clinvar_qs[0]
        for q in clinvar_qs[1:]:
            clinvar_q |= q
        return clinvar_q

    @classmethod
    def _clinvar_range_q(cls, path_range):
        return Q(clinvar__0__range=path_range, clinvar_key__isnull=False)

    @classmethod
    def _clinvar_path_q(cls, pathogenicity, _get_range_q=None):
        clinvar_path_filters = [
            f for f in (pathogenicity or {}).get(CLINVAR_KEY) or [] if f in CLINVAR_PATH_SIGNIFICANCES
        ]
        return cls._clinvar_filter_q(clinvar_path_filters, _get_range_q=_get_range_q) if clinvar_path_filters else None

    def explode_gene_id(self, gene_id_key):
        consequence_field = self.GENE_CONSEQUENCE_FIELD if self.has_annotation(self.GENE_CONSEQUENCE_FIELD) else self.TRANSCRIPT_CONSEQUENCE_FIELD
        results = self.annotate(
            selectedGeneId=ArrayJoin(ArrayDistinct(ArrayMap(consequence_field, mapped_expression='x.geneId')), output_field=models.StringField())
        )
        if self.has_annotation(self.FILTERED_CONSEQUENCE_FIELD):
            results = results.annotate(**{self.FILTERED_CONSEQUENCE_FIELD: ArrayFilter(
                self.FILTERED_CONSEQUENCE_FIELD, conditions=[{'geneId': (gene_id_key, '{field} = {value}')}],
            )})
            filter_q = Q(filtered_transcript_consequences__not_empty=True)
            if self.has_annotation('passes_annotation'):
                filter_q |= Q(passes_annotation=True)
            results = results.filter(filter_q)
        return results

    def has_annotation(self, field):
        return field in self.query.annotations


class EntriesManager(Manager):
    GENOTYPE_LOOKUP = {
        REF_REF: (0,),
        REF_ALT: (1,),
        ALT_ALT: (2,),
        HAS_ALT: (0, '{field} > {value}'),
        HAS_REF: (2, '{field} < {value}'),
    }
    INVALID_NUM_ALT_LOOKUP = {
        (0,): [1, 2],
        (1,): [0, 2],
        (2,): [0, 1],
        (0, '{field} > {value}'): [0],
        (2, '{field} < {value}'): [2],
    }

    INHERITANCE_FILTERS = {
        **INHERITANCE_FILTERS,
        ANY_AFFECTED: {AFFECTED: HAS_ALT},
    }

    @property
    def quality_filters(self):
        call_fields = {field[0] for field in self.model.CALL_FIELDS}
        return [config for config in [('gq', 1), ('ab', 100, 'x.gt != 1'), ('hl', 100)] if config[0] in call_fields]

    @property
    def genotype_fields(self):
        return OrderedDict({
            'family_guid': ('familyGuid', models.StringField()),
            'sample_type': ('sampleType', models.StringField()),
            'filters': ('filters', models.ArrayField(models.StringField())),
            'x.gt::Nullable(Int8)': ('numAlt', models.Int8Field(null=True, blank=True)),
            **{f'x.{column[0]}': column for column in self.model.CALL_FIELDS if column[0] != 'gt'}
        })

    @property
    def clinvar_fields(self):
        clinvar_model = self.model.clinvar_join.rel.related_model
        return OrderedDict({
            f'clinvar_join__{field.name}': (field.db_column or field.name, field)
            for field in reversed(clinvar_model._meta.local_fields) if field.name != 'key'
        })

    def search(self, sample_data, parsed_locus=None, freqs=None,  **kwargs):
        entries = self.annotate(seqrPop=self._seqr_pop_expression())
        entries = self._filter_intervals(entries, **(parsed_locus or {}))

        if (freqs or {}).get('callset'):
            entries = self._filter_seqr_frequency(entries, **freqs['callset'])

        gnomad_filter = (freqs or {}).get('gnomad_genomes') or {}
        if hasattr(self.model, 'is_gnomad_gt_5_percent') and ((gnomad_filter.get('af') or 1) <= 0.05 or any(gnomad_filter.get(field) is not None for field in ['ac', 'hh'])):
            entries = entries.filter(is_gnomad_gt_5_percent=False)

        return self._search_call_data(entries, sample_data, **kwargs)

    def _seqr_pop_expression(self):
        seqr_pop_fields = []
        for _, sub_fields in self.model.key.field.related_model.SEQR_POPULATIONS:
            seqr_pop_fields += [f"'{sub_fields['ac']}_wes'", f"'{sub_fields['ac']}_wgs'"]
            if sub_fields.get('hom'):
                seqr_pop_fields += [f"'{sub_fields['hom']}_wes'", f"'{sub_fields['hom']}_wgs'"]
        return DictGet(
            'key',
            dict_name=f"{self.model._meta.db_table.rsplit('/', 1)[0]}/gt_stats_dict",
            fields=', '.join(seqr_pop_fields),
            output_field=models.TupleField([models.UInt32Field() for _ in seqr_pop_fields])
        )

    def _search_call_data(self, entries, sample_data, inheritance_mode=None, inheritance_filter=None, qualityFilter=None, pathogenicity=None, annotate_carriers=False, **kwargs):
       project_guids = {s['project_guid'] for s in sample_data}
       project_filter = Q(project_guid__in=project_guids) if len(project_guids) > 1 else Q(project_guid=sample_data[0]['project_guid'])
       entries = entries.filter(project_filter)

       sample_type_families, multi_sample_type_families = self._get_family_sample_types(sample_data)
       family_q = None
       if multi_sample_type_families:
           family_q = Q(family_guid__in=multi_sample_type_families.keys())
       for sample_type, families in sample_type_families.items():
           sample_family_q = Q(sample_type=sample_type, family_guid__in=families)
           if family_q:
               family_q |= sample_family_q
           else:
               family_q = sample_family_q

       entries = entries.filter(family_q)

       entries = entries.annotate(
           clinvar_key=F('clinvar_join__key'),
           clinvar=Tuple(*self.clinvar_fields.keys(), output_field=NamedTupleField(list(self.clinvar_fields.values()), null_if_empty=True, null_empty_arrays=True))
       )

       quality_filter = qualityFilter or {}
       individual_genotype_filter = (inheritance_filter or {}).get('genotype')
       custom_affected = (inheritance_filter or {}).get('affected') or {}
       if inheritance_mode or individual_genotype_filter or quality_filter:
            clinvar_override_q = AnnotationsQuerySet._clinvar_path_q(
               pathogenicity, _get_range_q=lambda path_range: Q(clinvar_join__pathogenicity__range=path_range),
            )
            call_q = None
            multi_sample_type_quality_q = None
            for s in sample_data:
                sample_filters = self._family_sample_filters(s, inheritance_mode, individual_genotype_filter, quality_filter, custom_affected)
                if not sample_filters:
                    continue
                if s['family_guid'] in multi_sample_type_families:
                    multi_sample_type_quality_q = self._multi_sample_type_family_calls_q(
                        multi_sample_type_quality_q, s, sample_filters, clinvar_override_q, multi_sample_type_families
                    )
                else:
                    sample_type = s['sample_types'][0]
                    call_q = self._family_calls_q(call_q, s, sample_filters, sample_type, clinvar_override_q)

            #  With families with multiple sample types, can only filter rows after aggregating
            filtered_multi_sample_type_families = {
                family_guid: filters for family_guid, filters in multi_sample_type_families.items() if filters
            }
            if filtered_multi_sample_type_families:
                multi_type_q = Q(family_guid__in=filtered_multi_sample_type_families.keys())
                call_q = (call_q | multi_type_q) if call_q else multi_type_q
                entries = entries.annotate(passes_quality=~multi_type_q | (multi_sample_type_quality_q or Value(True)))
                entries = self._annotate_failed_family_samples(entries, filtered_multi_sample_type_families)

            if call_q:
                entries = entries.filter(call_q)

            if quality_filter.get('vcf_filter'):
                q = Q(filters__len=0)
                if clinvar_override_q:
                    q |= clinvar_override_q
                entries = entries.filter(q)

       return self._annotate_calls(entries, sample_data, annotate_carriers, multi_sample_type_families)

    @staticmethod
    def _get_family_sample_types(sample_data):
        sample_type_families = defaultdict(list)
        multi_sample_type_families = {}
        for s in sample_data:
            if len(s['sample_types']) == 1:
                sample_type_families[s['sample_types'][0]].append(s['family_guid'])
            else:
                multi_sample_type_families[s['family_guid']] = []
        return sample_type_families, multi_sample_type_families

    def _family_sample_filters(self, family_sample_data, inheritance_mode, individual_genotype_filter, quality_filter, custom_affected):
        sample_filters = []
        for sample in family_sample_data['samples']:
            affected = custom_affected.get(sample['individual_guid']) or sample['affected']
            sample_inheritance_filter = self._sample_genotype_filter(sample, affected, inheritance_mode, individual_genotype_filter)
            sample_quality_filter = self._sample_quality_filter(affected, quality_filter)
            if sample_inheritance_filter or sample_quality_filter:
                sample_filters.append((sample['sample_ids_by_type'], sample_inheritance_filter, sample_quality_filter))
        return sample_filters

    @classmethod
    def _family_calls_q(cls, call_q, family_sample_data, sample_filters, sample_type, clinvar_override_q):
       family_sample_q = None
       for sample_ids_by_type, sample_inheritance_filter, sample_quality_filter in sample_filters:
           sample_inheritance_filter['sampleId'] = (f"'{sample_ids_by_type[sample_type]}'",)
           sample_q = Q(
               calls__array_exists={**sample_inheritance_filter, **sample_quality_filter},
               family_guid=family_sample_data['family_guid'],
               sample_type=sample_type,
           )
           if clinvar_override_q and sample_quality_filter:
               sample_q |= clinvar_override_q & Q(calls__array_exists=sample_inheritance_filter)

           if family_sample_q is None:
               family_sample_q = sample_q
           else:
               family_sample_q &= sample_q

       if family_sample_q and call_q:
           call_q |= family_sample_q
       return call_q or family_sample_q

    @classmethod
    def _multi_sample_type_family_calls_q(cls, call_q, family_sample_data, sample_filters, clinvar_override_q, multi_sample_type_families):
        sample_quality_filters = []
        for sample_ids_by_type, sample_inheritance_filter, sample_quality_filter in sample_filters:
            if sample_inheritance_filter.get('gt'):
                multi_sample_type_families[family_sample_data['family_guid']].append(
                    (sample_ids_by_type, sample_inheritance_filter['gt'])
                )
            if sample_quality_filter:
                sample_quality_filters.append((sample_ids_by_type, {}, sample_quality_filter))
        if sample_quality_filters:
            for sample_type in family_sample_data['sample_types']:
                call_q = cls._family_calls_q(
                    call_q, family_sample_data, sample_quality_filters, sample_type, clinvar_override_q,
                )
        return call_q

    @classmethod
    def _sample_genotype_filter(cls, sample, affected, inheritance_mode, individual_genotype_filter):
        sample_filter = {}
        genotype = None
        if individual_genotype_filter:
            genotype = individual_genotype_filter.get(sample['individual_guid'])
        elif inheritance_mode:
            genotype = cls.INHERITANCE_FILTERS[inheritance_mode].get(affected)
            if (inheritance_mode == X_LINKED_RECESSIVE and affected == UNAFFECTED and sample['sex'] in MALE_SEXES):
                genotype = REF_REF
        if genotype:
            sample_filter['gt'] = cls.GENOTYPE_LOOKUP[genotype]
        return sample_filter

    def _sample_quality_filter(self, affected, quality_filter):
        sample_filter = {}
        if quality_filter.get('affected_only') and affected != AFFECTED:
            return sample_filter

        for field, scale, *filters in self.quality_filters:
            value = quality_filter.get(f'min_{field}')
            if value:
                or_filters = ['isNull({field})', '{field} >= {value}'] + filters
                sample_filter[field] = (value / scale, f'or({", ".join(or_filters)})')

        return sample_filter

    @classmethod
    def _annotate_failed_family_samples(cls, entries, family_sample_gt_filters):
        gt_map = []
        missing_sample_map = []
        for family_guid, sample_filters in family_sample_gt_filters.items():
            sample_type_filters = defaultdict(list)
            missing_type_samples = defaultdict(list)
            for sample_ids_by_type, gt_filter in sample_filters:
                for sample_type, sample_id in sample_ids_by_type.items():
                    sample_type_filters[sample_type].append(f"'{sample_id}', {cls.INVALID_NUM_ALT_LOOKUP[gt_filter]}")
                    if len(sample_ids_by_type) == 1:
                        missing_type = Sample.SAMPLE_TYPE_WES if sample_type == Sample.SAMPLE_TYPE_WGS else Sample.SAMPLE_TYPE_WGS
                        missing_type_samples[missing_type].append(sample_id)
            sample_type_map = [
                f"'{sample_type}', map({', '.join(type_filters)})"
                for sample_type, type_filters in sample_type_filters.items()
            ]
            gt_map.append(f"'{family_guid}', map({', '.join(sample_type_map)})")
            if missing_type_samples:
                missing_type_map = [f"'{sample_type}', {samples}" for sample_type, samples in missing_type_samples.items()]
                missing_sample_map.append(f"'{family_guid}', map({', '.join(missing_type_map)})")

        entries = entries.annotate(failed_family_samples= ArrayMap(
            ArrayFilter('calls', conditions=[{
                'gt': (', '.join(gt_map), 'has(map({value})[family_guid][sample_type::String][x.sampleId], {field})'),
            }]),
            mapped_expression='tuple(family_guid, x.sampleId)',
        ))
        if missing_sample_map:
            entries = entries.annotate(
                missing_family_samples=ArrayMap(
                    MapLookup('family_guid', Cast('sample_type', models.StringField()), map_values=', '.join(missing_sample_map)),
                    mapped_expression='tuple(family_guid, x)',
                )
            )
        return entries

    def _annotate_calls(self, entries, sample_data, annotate_carriers, multi_sample_type_families):
        carriers_expression = self._carriers_expression(sample_data) if annotate_carriers else None
        if carriers_expression:
            entries = entries.annotate(carriers=carriers_expression)

        fields = ['key', 'clinvar', 'clinvar_key', 'seqrPop']
        if multi_sample_type_families or len(sample_data) > 1:
            entries = entries.values(*fields).annotate(
                familyGuids=ArraySort(ArrayDistinct(GroupArray('family_guid'))),
                genotypes=GroupArrayArray(self._genotype_expression(sample_data)),
            )
            if carriers_expression:
                map_field = models.MapField(models.StringField(), models.ArrayField(models.StringField()))
                if multi_sample_type_families:
                    family_carriers = ArrayFold(
                        GroupArray(Tuple('family_guid', 'carriers')),
                        fold_function='mapUpdate(acc, map(x.1, arrayIntersect(acc[x.1], x.2)))',
                        acc='map()::Map(String, Array(String))',
                        output_field=map_field,
                    )
                else:
                    family_carriers = Cast(Tuple('familyGuids', GroupArray('carriers')), map_field)
                entries = entries.annotate(family_carriers=family_carriers)
            if any(multi_sample_type_families.values()):
                entries = self._multi_sample_type_filtered_entries(entries)
        else:
            if carriers_expression:
                fields.append('carriers')
            entries = entries.values(
                *fields,
                familyGuids=Array('family_guid'),
                genotypes=self._genotype_expression(sample_data),
            )
        return entries

    def _genotype_expression(self, sample_data):
        sample_map = []
        for data in sample_data:
            family_samples = []
            for s in data['samples']:
                family_samples += [
                    f"'{sample_id}', '{s['individual_guid']}'" for sample_id in set(s['sample_ids_by_type'].values())
                ]
            sample_map.append(f"'{data['family_guid']}', map({', '.join(family_samples)})")
        return ArrayFilter(
            ArrayMap(
                'calls',
                mapped_expression=f"tuple(map({', '.join(sample_map)})[family_guid][x.sampleId], {', '.join(self.genotype_fields.keys())})",
                output_field=NestedField([('individualGuid', models.StringField()), *self.genotype_fields.values()], group_by_key='individualGuid', flatten_groups=True)
            ),
            conditions=[{1: (None, 'notEmpty({field})')}]
        )

    def _carriers_expression(self, sample_data):
        family_carriers = {}
        for family_sample_data in sample_data:
            family_carriers[family_sample_data['family_guid']] = set()
            for s in family_sample_data['samples']:
                if s['affected'] == UNAFFECTED:
                    family_carriers[family_sample_data['family_guid']].update([
                        f"'{sample_id}'" for sample_id in s['sample_ids_by_type'].values()
                    ])
        if not any(family_carriers.values()):
            return None

        carrier_map = [
            f"'{family_guid}', [{', '.join(samples)}]" for family_guid, samples in family_carriers.items()
        ]
        return ArrayMap(
            ArrayFilter('calls', conditions=[{
                'sampleId': (", ".join(carrier_map), 'has(map({value})[family_guid], {field})'),
                'gt': (0, '{field} > {value}'),
            }]),
            mapped_expression='x.sampleId',
        )

    @staticmethod
    def _multi_sample_type_filtered_entries(entries):
        failed_samples_expression = GroupArrayIntersect('failed_family_samples')
        if 'missing_family_samples' in entries.query.annotations:
            # If variant is present in all sample types, it must pass inheritance for all samples in at least one type
            # If variant is present in only one sample type, it only needs to pass for samples present in that type
            failed_samples_expression = If(
                failed_samples_expression,
                GroupArrayIntersect(ArrayConcat('failed_family_samples', 'missing_family_samples')),
                condition='count() = 1',
            )

        entries = entries.annotate(
            pass_inheritance_families=ArraySymmetricDifference(
                'familyGuids',
                ArrayMap(failed_samples_expression, mapped_expression='x.1'),
                output_field=models.ArrayField(models.StringField()),
            ),
            pass_quality_families=ArrayMap(
                ArrayFilter(
                    GroupArray(Tuple('family_guid', 'passes_quality')),
                    conditions=[{2: (None, '{field}')}],
                ),
                mapped_expression='x.1', output_field=models.ArrayField(models.StringField()),
            ),
        )
        entries = entries.annotate(
            familyGuids=ArraySort(ArrayDistinct(ArrayIntersect('pass_inheritance_families', 'pass_quality_families')))
        )
        return entries.filter(familyGuids__not_empty=True)

    @classmethod
    def _filter_intervals(cls, entries, exclude_intervals=False, intervals=None, variant_ids=None,  **kwargs):
        if variant_ids:
            # although technically redundant, the interval query is applied to the entries table before join and reduces the join size,
            # while the full variant_id filter is applied to the annotation table after the join
            intervals = [(chrom, pos, pos) for chrom, pos, _, _ in variant_ids]

        if intervals:
            interval_q = cls._interval_query(*intervals[0])
            for interval in intervals[1:]:
                interval_q |= cls._interval_query(*interval)
            filter_func = entries.exclude if exclude_intervals else entries.filter
            entries = filter_func(interval_q)

        return entries

    @staticmethod
    def _interval_query(chrom, start, end):
        return Q(xpos__range=(get_xpos(chrom, start), get_xpos(chrom, end)))

    def _filter_seqr_frequency(self, entries, ac=None, hh=None, **kwargs):
        if ac is not None:
            entries = entries.annotate(ac=Plus('seqrPop__0', 'seqrPop__1'))
            entries = entries.filter(ac__lte=ac)
        if hh is not None and 'hom' in self.model.key.field.related_model.SEQR_POPULATIONS[0][1]:
            entries = entries.annotate(hom=Plus('seqrPop__2', 'seqrPop__3'))
            entries = entries.filter(hom__lte=hh)
        return entries
