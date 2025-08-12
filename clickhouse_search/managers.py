from clickhouse_backend import models
from collections import OrderedDict, defaultdict

from django.db.models import F, QuerySet, Q, Value
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
    EXTENDED_SPLICE_KEY, MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY, CLINVAR_KEY, HGMD_KEY, NEW_SV_FIELD, \
    EXTENDED_SPLICE_REGION_CONSEQUENCE, CLINVAR_PATH_RANGES, CLINVAR_PATH_SIGNIFICANCES, PATH_FREQ_OVERRIDE_CUTOFF, \
    HGMD_CLASS_FILTERS, SV_TYPE_FILTER_FIELD, SV_CONSEQUENCES_FIELD, COMPOUND_HET, COMPOUND_HET_ALLOW_HOM_ALTS
from seqr.utils.xpos_utils import get_xpos, MIN_POS, MAX_POS


class SearchQuerySet(QuerySet):

    @property
    def table_basename(self):
        return self.model._meta.db_table.rsplit('/', 1)[0]

    @property
    def clinvar_field_prefix(self):
        return 'clinvar_join'

    @property
    def clinvar_fields(self):
        return OrderedDict({
            f'{self.clinvar_field_prefix}__{field.name}': (field.db_column or field.name, field)
            for field in reversed(self.clinvar_model._meta.local_fields) if field.name != 'key'
        })

    def _clinvar_tuple(self):
        return Tuple(
            *self.clinvar_fields.keys(),
            output_field=NamedTupleField(list(self.clinvar_fields.values()), null_if_empty=True, null_empty_arrays=True),
        )

    def _seqr_pop_fields(self, seqr_populations):
        sample_types = [
            sample_type.lower() for sample_type in
            ([self.single_sample_type] if self.single_sample_type else list(Sample.SAMPLE_TYPE_LOOKUP.keys()))
        ]
        seqr_pop_fields = []
        for _, sub_fields in seqr_populations:
            seqr_pop_fields += [f"'{sub_fields['ac']}_{sample_type}'" for sample_type in sample_types]
            if sub_fields.get('hom'):
                seqr_pop_fields += [f"'{sub_fields['hom']}_{sample_type}'" for sample_type in sample_types]
        return seqr_pop_fields


class AnnotationsQuerySet(SearchQuerySet):

    TRANSCRIPT_CONSEQUENCE_FIELD = 'sorted_transcript_consequences'
    SORTED_GENE_CONSEQUENCE_FIELD = 'sorted_gene_consequences'
    GENOTYPE_GENE_CONSEQUENCE_FIELD = 'genotype_gene_consequences'
    GENE_CONSEQUENCE_FIELD = 'gene_consequences'
    FILTERED_CONSEQUENCE_FIELD = 'filtered_transcript_consequences'
    TRANSCRIPT_FIELDS = [TRANSCRIPT_CONSEQUENCE_FIELD, SORTED_GENE_CONSEQUENCE_FIELD]

    ENTRY_FIELDS = ['familyGuids', 'genotypes']

    SELECTED_GENE_FIELD = 'selectedGeneId'

    @property
    def transcript_field(self):
        return next(field for field in self.TRANSCRIPT_FIELDS if hasattr(self.model, field))

    @property
    def annotation_values(self):
        seqr_pops = []
        population_fields = [*self.model.POPULATION_FIELDS]
        single_sample_type = hasattr(self.model, 'SV_TYPES')
        for i, (name, subfields) in enumerate(self.model.SEQR_POPULATIONS):
            exprs = [F(f'seqrPop__{i*2}') if single_sample_type else Plus(f'seqrPop__{i*2}', f'seqrPop__{i*2+1}')]
            sub_output_fields = [('ac', models.UInt32Field())]
            if 'hom' in subfields:
                exprs.append(F(f'seqrPop__{i*2+1}') if single_sample_type else Plus(f'seqrPop__{i*2+2}', f'seqrPop__{i*2+3}'))
                sub_output_fields.append(('hom', models.UInt32Field()))
            seqr_pops.append(Tuple(*exprs))
            population_fields.append((name, NamedTupleField(sub_output_fields)))

        annotations = {
            **{key: Value(value) for key, value in self.model.ANNOTATION_CONSTANTS.items()},
            **{field.db_column: F(field.name) for field in self.model._meta.local_fields if field.db_column and field.name != field.db_column},
            'populations': TupleConcat(F('populations'), Tuple(*seqr_pops), output_field=NamedTupleField(population_fields)),
        }

        if not hasattr(self.model, 'SORTED_TRANSCRIPT_CONSQUENCES_FIELDS'):
            annotations['transcripts'] = annotations.pop(getattr(self.model, self.transcript_field).field.db_column)
            if self.transcript_field == self.TRANSCRIPT_CONSEQUENCE_FIELD:
                annotations.update({
                    'mainTranscriptId': F('sorted_transcript_consequences__0__transcriptId'),
                    'selectedMainTranscriptId': Value(None, output_field=models.StringField(null=True)),
                })

        return annotations

    @staticmethod
    def _genotype_override_expression(index, col, cn_index):
        expressions = [f'x.{index}', f'sample_{col}']
        is_gene_ids = col == 'geneIds'
        if is_gene_ids:
            expressions = [f'arraySort({expr})::String' for expr in expressions]
        expression = f'nullIf({", ".join(expressions)})'
        if is_gene_ids:
            # If entire genotype is missing, geneIds should be null instead of empty
            expression = f'if(isNull(x.{cn_index}), null, {expression})'
        return expression

    @property
    def annotation_fields(self):
        return [
            field.name for field in self.model._meta.local_fields
            if (field.db_column or field.name) not in self.annotation_values and field.name not in self.TRANSCRIPT_FIELDS
        ]

    @property
    def prediction_fields(self):
        return set(dict(self.model.PREDICTION_FIELDS).keys())

    @property
    def transcript_fields(self):
        transcript_field_configs = next(getattr(self.model, field) for field in [
            'SORTED_TRANSCRIPT_CONSQUENCES_FIELDS', 'TRANSCRIPTS_FIELDS', 'SORTED_GENE_CONSQUENCES_FIELDS',
        ] if hasattr(self.model, field))
        return set(dict(transcript_field_configs).keys())

    @property
    def single_sample_type(self):
        return getattr(self.model, 'SV_TYPES', None)

    @property
    def entry_field(self):
        return next(obj.name for obj in self.model._meta.related_objects if obj.name.startswith('entries'))

    @property
    def entry_model(self):
         return getattr(self.model, f'{self.entry_field}_set').rel.related_model

    @property
    def clinvar_model(self):
        if not hasattr(self.entry_model, 'clinvar_join'):
            return None
        return self.entry_model.clinvar_join.rel.related_model

    @property
    def clinvar_field_prefix(self):
        return f'{self.entry_field}__clinvar_join'


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

    def cross_join(self, query, alias, join_query, join_alias, conditional_selects=None):
        query = self._get_join_query_values(query, alias, conditional_selects)
        join_query = self._get_join_query_values(join_query, join_alias, conditional_selects)
        self.query.join(CrossJoin(query, alias, join_query, join_alias))

        annotations = self._get_subquery_annotations(query, alias)
        annotations.update(self._get_subquery_annotations(join_query, join_alias))

        return self.annotate(**annotations)

    def _get_join_query_values(self, query, alias, conditional_selects):
        query_select = query.annotation_values
        for select_func in (conditional_selects or []):
            query_select.update(select_func(query, prefix=f'{alias}_'))
        annotation_fields = query.annotation_fields
        return query.values(
            **{f'{alias}_{field}': F(field) for field in annotation_fields if field not in query_select},
            **{f'{alias}_{field}': value for field, value in query_select.items()},
        )

    def search(self, parsed_locus=None, **kwargs):
        parsed_locus = parsed_locus or {}
        results = self.filter_variant_ids(**parsed_locus)
        results = self._filter_frequency(results, **kwargs)
        results = self._filter_in_silico(results, **kwargs)
        results = self.filter_annotations(results, **parsed_locus, **kwargs)
        return results

    def result_values(self, skip_entry_fields=False):
        override_model_annotations = {'populations', 'pos', 'end'}
        values = {**self.annotation_values}
        values.update(self._conditional_selected_transcript_values(self))
        if not skip_entry_fields:
            values.update(self._genotype_override_values(self))
        initial_values = {k: v for k, v in  values.items() if k not in override_model_annotations}

        fields = [*self.annotation_fields]
        if self.has_annotation('familyGenotypes'):
            fields.append('familyGenotypes')
        elif not skip_entry_fields:
            fields += self.ENTRY_FIELDS

        if self.has_annotation('clinvar'):
            fields.append('clinvar')

        fields = [field for field in fields if field not in values]
        return self.values(*fields, **initial_values).annotate(
            **{k: values[k] for k in override_model_annotations if k in values},
        )

    def join_seqr_pop(self):
        results = self
        seqr_populations = self.model.SEQR_POPULATIONS
        if seqr_populations:
            seqr_pop_fields = self._seqr_pop_fields(seqr_populations)
            results = results.annotate(seqrPop=Tuple(
                *[
                    DictGet(
                        'key',
                        dict_name=f"{self.table_basename}/gt_stats_dict",
                        fields=seqr_pop_field,
                    ) for seqr_pop_field in seqr_pop_fields],
                output_field=models.TupleField([models.UInt32Field() for _ in seqr_pop_fields])
            ))

        return results

    def join_clinvar(self, keys):
        results = self
        if self.clinvar_model:
            results = results.annotate(clinvar=self._clinvar_tuple())
            # Due to django modeling, adding a clinvar annotation will add a join to the entries table and then to clinvar
            # Manipulating the underlying join removes the entry join entirely
            entry_table = f'{self.table_basename}/entries'
            results.query.alias_map[f'{self.table_basename}/clinvar'].parent_alias = results.query.alias_map[entry_table].parent_alias
            results.query.alias_refcount[entry_table] = 0
        return results

    def _conditional_selected_transcript_values(self, query, prefix=''):
        if not hasattr(self.model, self.TRANSCRIPT_CONSEQUENCE_FIELD):
            return {}
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

    def _genotype_override_values(self, query, prefix=''):
        genotype_override_fields = query.model.GENOTYPE_OVERRIDE_FIELDS
        if not genotype_override_fields:
            return {}

        index_map = {
            field: i+1 for i, (field, _) in enumerate(query.query.annotations['genotypes'].output_field.base_fields)
        }
        override_field_map = {field: col for col, (field, _) in genotype_override_fields.items()}
        genotype_fields = [
            self._genotype_override_expression(index_map[field], override_field_map[field], index_map['cn'])
            if field in override_field_map else (f'ifNull(x.{index_map[field]}, 0)' if field == 'numAlt' else f'x.{index_map[field]}')
            for (field, _) in query.query.annotations['genotypes'].output_field.base_fields
        ]

        return {
            'genotypes': ArrayMap('genotypes', mapped_expression=f"tuple({', '.join(genotype_fields)})"),
            'transcripts': F(query.GENOTYPE_GENE_CONSEQUENCE_FIELD),
            **{col: F(f'sample_{col}') for col in genotype_override_fields if col != 'geneIds'},
        }

    def search_compound_hets(self, primary_q, secondary_q):
        primary_gene_field = f'primary_{self.SELECTED_GENE_FIELD}'
        secondary_gene_field = f'secondary_{self.SELECTED_GENE_FIELD}'
        primary_q = primary_q.explode_gene_id(primary_gene_field)
        secondary_q = secondary_q.explode_gene_id(secondary_gene_field)

        conditional_fields = lambda query, **kwargs: {
            field: F(field) for field in [self.SELECTED_GENE_FIELD, 'clinvar', 'family_carriers', 'carriers', 'has_hom_alt', 'no_hom_alt_families', 'familyGenotypes'] + self.ENTRY_FIELDS
            if field in query.query.annotations
        }

        results = self.cross_join(
            query=primary_q, alias='primary', join_query=secondary_q, join_alias='secondary',
            conditional_selects=[
                conditional_fields, self._conditional_selected_transcript_values, self._genotype_override_values,
            ],
        )
        return results.filter(
            **{primary_gene_field: F(secondary_gene_field)}
        ).exclude(primary_variantId=F('secondary_variantId'))

    def filter_variant_ids(self, variant_ids=None, rs_ids=None, **kwargs):
        results = self
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
        clinvar_override_q = self._clinvar_path_q(pathogenicity) if self.has_annotation(CLINVAR_KEY) else None

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

    def filter_annotations(self, results, annotations=None, pathogenicity=None, exclude=None, gene_ids=None, intervals=None, exclude_intervals=False, padded_interval=None,  **kwargs):
        transcript_field = self.transcript_field
        if self.model.GENOTYPE_OVERRIDE_FIELDS:
            results = results.annotate(**{
                self.GENOTYPE_GENE_CONSEQUENCE_FIELD: ArrayFilter(self.SORTED_GENE_CONSEQUENCE_FIELD, conditions=[{
                    'geneId': (None, 'has(sample_geneIds, {field})'),
                }]),
            })
            transcript_field = self.GENOTYPE_GENE_CONSEQUENCE_FIELD
        interval_qs = [self._interval_query(*interval) for interval in intervals or []]
        if gene_ids:
            results = results.annotate(**{
                self.GENE_CONSEQUENCE_FIELD: ArrayFilter(transcript_field, conditions=[{
                    'geneId': (gene_ids, 'has({value}, {field})'),
                }]),
            })
            gene_q = Q(gene_consequences__not_empty=True)
            for interval_q in interval_qs:
                gene_q |= interval_q
            results = results.filter(gene_q)
        elif (interval_qs or padded_interval) and hasattr(self.model, 'end'):
            if padded_interval:
                padding = int((padded_interval['end'] - padded_interval['start']) * padded_interval['padding'])
                interval_qs = [Q(end__range=(padded_interval['end'] - padding, padded_interval['end'] + padding))]
            interval_q = interval_qs[0]
            for q in interval_qs[1:]:
                interval_q |= q
            filter_func = results.exclude if exclude_intervals else results.filter
            results = filter_func(interval_q)

        filter_qs, transcript_filters = self._parse_annotation_filters(annotations, pathogenicity) if (annotations or pathogenicity) else ([], [])

        exclude_clinvar = (exclude or {}).get(CLINVAR_KEY)
        if exclude_clinvar and self.has_annotation(CLINVAR_KEY):
            results = results.exclude(self._clinvar_filter_q(exclude_clinvar))

        if not (filter_qs or transcript_filters):
            if any(val for key, val in (annotations or {}).items() if key != NEW_SV_FIELD) or any(val for val in (pathogenicity or {}).values()):
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
            consequence_field = self.GENE_CONSEQUENCE_FIELD if gene_ids else transcript_field
            results = results.annotate(**{
                self.FILTERED_CONSEQUENCE_FIELD: ArrayFilter(consequence_field, conditions=transcript_filters),
            })
            transcript_q = Q(filtered_transcript_consequences__not_empty=True)
            if filter_q:
                filter_q |= transcript_q
            else:
                filter_q = transcript_q

        return results.filter(filter_q)

    def _interval_query(self, chrom, start, end):
        q = Q(xpos__range=(get_xpos(chrom, start), get_xpos(chrom, end)))
        if hasattr(self.model, 'endChrom'):
            q |= Q(endChrom__isnull=True, chrom=chrom, end__range=(start, end))
            q |= Q(endChrom=chrom, end__range=(start, end))
        elif hasattr(self.model, 'end'):
            q |= Q(chrom=chrom, end__range=(start, end))
            q |= Q(chrom=chrom, pos__lte=start, end__gte=end)
        return q

    TRANSCRIPT_FIELD_FILTERS = {
        UTR_ANNOTATOR_KEY: ('fiveutrConsequence', 'hasAny({value}, [{field}])'),
        EXTENDED_SPLICE_KEY: ('extendedIntronicSpliceRegionVariant', '{field} = {value}', lambda value: 1 if EXTENDED_SPLICE_REGION_CONSEQUENCE in value else 0),
        SV_CONSEQUENCES_FIELD: ('majorConsequence', 'hasAny({value}, [{field}])'),
    }
    ANNOTATION_FIELD_FILTERS = {
        SCREEN_KEY: ('screen_region_type',),
        SV_TYPE_FILTER_FIELD: ('sv_type', lambda value, model: ('{field}__in', [
            sv_type.replace(model.SV_TYPE_FILTER_PREFIX, '') for sv_type in value
            if sv_type.startswith(model.SV_TYPE_FILTER_PREFIX)
        ])),
        **{field: (f'sorted_{field}_consequences', lambda value, _: ('{field}__array_exists', {
            'consequenceTerms': (value, 'hasAny({value}, {field})'),
        })) for field in [MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY]},
    }

    def _parse_annotation_filters(self, annotations, pathogenicity):
        filter_qs = []
        filters_by_field = {}
        allowed_consequences = []
        transcript_field_filters = {}
        for field, value in (annotations or {}).items():
            if field in self.TRANSCRIPT_FIELD_FILTERS:
                filter_field, template, *format_value = self.TRANSCRIPT_FIELD_FILTERS[field]
                if format_value:
                    value = format_value[0](value)
                if value:
                    transcript_field_filters[filter_field] = (value, template)
            elif field in self.ANNOTATION_FIELD_FILTERS:
                filter_field, *format_filter = self.ANNOTATION_FIELD_FILTERS[field]
                filters_by_field[filter_field] = format_filter[0](value, self.model) if format_filter else ('{field}__in', value)
            elif field == SPLICE_AI_FIELD:
                splice_ai_q = self._get_in_silico_score_q(SPLICE_AI_FIELD, value)
                if splice_ai_q:
                    filter_qs.append(splice_ai_q)
            elif field != NEW_SV_FIELD:
                allowed_consequences += value

        for field, value in (pathogenicity or {}).items():
            if not value:
                continue
            elif field == HGMD_KEY:
                filters_by_field[HGMD_KEY] = self._hgmd_filter(value)
            elif field == CLINVAR_KEY and self.has_annotation(CLINVAR_KEY):
                filter_qs.append(self._clinvar_filter_q(value))

        filter_qs += [
            Q(**{lookup_template.format(field=field): value})
            for field, (lookup_template, value) in filters_by_field.items() if hasattr(self.model, field)
        ]
        transcript_filters = [
            {field: value} for field, value in transcript_field_filters.items() if field in self.transcript_fields
        ]

        if allowed_consequences and 'consequenceTerms' in self.transcript_fields:
            transcript_filters += self._allowed_consequences_filters(allowed_consequences)

        return filter_qs, transcript_filters

    def _allowed_consequences_filters(self, allowed_consequences):
        csq_filters = []
        non_canonical_consequences = [c for c in allowed_consequences if not c.endswith('__canonical')]
        if non_canonical_consequences:
            csq_filters.append(self._consequence_term_filter(non_canonical_consequences))

        canonical_consequences = [
            c.replace('__canonical', '') for c in allowed_consequences if c.endswith('__canonical')
        ]
        if canonical_consequences and 'canonical' in self.transcript_fields:
            csq_filters.append(
                self._consequence_term_filter(canonical_consequences, canonical=(0, '{field} > {value}')),
            )
        return csq_filters

    @staticmethod
    def _consequence_term_filter(consequences, **kwargs):
        return {'consequenceTerms': (consequences, 'hasAny({value}, {field})'), **kwargs}

    @staticmethod
    def _hgmd_filter(hgmd):
        min_class = next((class_name for value, class_name in HGMD_CLASS_FILTERS if value in hgmd), None)
        max_class = next((class_name for value, class_name in reversed(HGMD_CLASS_FILTERS) if value in hgmd), None)
        if 'hgmd_other' in hgmd:
            min_class = min_class or 'DP'
            max_class = None
        if min_class == max_class:
            return ('{field}__classification', min_class)
        elif min_class and max_class:
            return ('{field}__classification__range', (min_class, max_class))
        return ('{field}__classification__gt', min_class)

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
        consequence_field = self.GENE_CONSEQUENCE_FIELD if self.has_annotation(self.GENE_CONSEQUENCE_FIELD) else self.transcript_field
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


class EntriesManager(SearchQuerySet):
    # # TODO used for something else?
    # GENOTYPE_LOOKUP = {
    #     REF_REF: (0,),
    #     REF_ALT: (1,),
    #     ALT_ALT: (2,),
    #     HAS_ALT: (0, '{field} > {value}'),
    #     HAS_REF: (2, '{field} < {value}'),
    # }
    GENOTYPE_LOOKUP = {
        REF_REF: [0],
        REF_ALT: [1],
        ALT_ALT: [2],
        HAS_ALT: [1, 2],
        HAS_REF: [0, 1],
    }
    COMP_HET_ALT = 'COMP_HET_ALT'
    GENOTYPE_LOOKUP[COMP_HET_ALT] = GENOTYPE_LOOKUP[REF_ALT]
    NULLABLE_GENOTYPE_LOOKUP = {
        **GENOTYPE_LOOKUP,
        # REF_REF: (0, 'or(isNull({field}), {field} = {value})'),
        # HAS_REF: (2, 'or(isNull({field}), {field} < {value})'),
        # HAS_ALT: (0, 'and(isNotNull({field}), {field} > {value})'),
    }
    NULLABLE_GENOTYPE_LOOKUP[COMP_HET_ALT] = NULLABLE_GENOTYPE_LOOKUP[HAS_ALT]
    NULLABLE_GENOTYPES = {REF_REF, HAS_REF}
    INVALID_NUM_ALT_LOOKUP = {
        (0,): [1, 2],
        (1,): [0, 2],
        (2,): [0, 1],
        (0, '{field} > {value}'): [0],
        (2, '{field} < {value}'): [2],
    }

    INHERITANCE_FILTERS = {
        **INHERITANCE_FILTERS,
        COMPOUND_HET: {**INHERITANCE_FILTERS[COMPOUND_HET], AFFECTED: COMP_HET_ALT},
        COMPOUND_HET_ALLOW_HOM_ALTS: {**INHERITANCE_FILTERS[COMPOUND_HET], AFFECTED: HAS_ALT},
    }

    @property
    def annotations_model(self):
        return self.model.key.field.related_model

    @property
    def call_fields(self):
        return dict(self.model.CALL_FIELDS)


    @property
    def genotype_lookup(self):
        return self.NULLABLE_GENOTYPE_LOOKUP if self.annotations_model.GENOTYPE_OVERRIDE_FIELDS else self.GENOTYPE_LOOKUP

    @property
    def nullable_genotypes(self):
        return self.NULLABLE_GENOTYPES if self.annotations_model.GENOTYPE_OVERRIDE_FIELDS else []

    @property
    def quality_filters(self):
        return [config for config in [('gq', 1), ('ab', 100, 'x.gt != 1'), ('qs', 1), ('hl', 100)] if config[0] in self.call_fields]

    @property
    def single_sample_type(self):
        return getattr(self.model, 'SAMPLE_TYPE', None)

    @property
    def genotype_fields(self):
        sample_type = f"'{self.single_sample_type}'" if self.single_sample_type else 'sample_type'
        return OrderedDict({
            'family_guid': ('familyGuid', models.StringField()),
            sample_type: ('sampleType', models.StringField()),
            'filters': ('filters', models.ArrayField(models.StringField())),
            'x.gt::Nullable(Int8)': ('numAlt', models.Int8Field(null=True, blank=True)),
            **{f'x.{name}': (name, output_field) for name, output_field in self.call_fields.items() if name != 'gt'}
        })

    @property
    def clinvar_model(self):
        return self.model.clinvar_join.rel.related_model

    def search(self, sample_data, parsed_locus=None, freqs=None, annotations=None, **kwargs):
        entries = self.filter_intervals(**(parsed_locus or {}))

        entries = self._join_annotations(entries)

        is_sv_class = 'cn' in self.call_fields
        callset_filter_field = 'sv_callset' if is_sv_class else 'callset'
        if (freqs or {}).get(callset_filter_field) and self.annotations_model.SEQR_POPULATIONS:
            entries = self._filter_seqr_frequency(entries, **freqs[callset_filter_field])

        gnomad_filter = (freqs or {}).get('gnomad_genomes') or {}
        if hasattr(self.model, 'is_gnomad_gt_5_percent') and ((gnomad_filter.get('af') or 1) <= 0.05 or any(gnomad_filter.get(field) is not None for field in ['ac', 'hh'])):
            entries = entries.filter(is_gnomad_gt_5_percent=False)

        if (annotations or {}).get(NEW_SV_FIELD) and 'newCall' in self.call_fields:
            entries = entries.filter(calls__array_exists={'newCall': (None, '{field}')})

        return self._search_call_data(entries, sample_data, **kwargs)

    def _join_annotations(self, entries):
        if self._has_clinvar():
           entries = entries.annotate(
               clinvar_key=F('clinvar_join__key'),
               clinvar=self._clinvar_tuple(),
           )

        seqr_populations = self.annotations_model.SEQR_POPULATIONS
        if seqr_populations:
            seqr_pop_fields = self._seqr_pop_fields(seqr_populations)
            entries = entries.annotate(seqrPop=DictGet(
                'key',
                dict_name=f"{self.table_basename}/gt_stats_dict",
                fields=', '.join(seqr_pop_fields),
                output_field=models.TupleField([models.UInt32Field() for _ in seqr_pop_fields])
            ))

        return entries

    def result_values(self, sample_data):
        entries = self._join_annotations(self)
        if sample_data:
            return self._search_call_data(entries, sample_data)
        return self._annotate_calls(entries)

    def _has_clinvar(self):
        return hasattr(self.model, 'clinvar_join')

    def _search_call_data(self, entries, sample_data, inheritance_mode=None, inheritance_filter=None, qualityFilter=None, pathogenicity=None, annotate_carriers=False, annotate_hom_alts=False, skip_individual_guid=False, **kwargs):
       project_guids = {s['project_guid'] for s in sample_data}
       project_filter = Q(project_guid__in=project_guids) if len(project_guids) > 1 else Q(project_guid=sample_data[0]['project_guid'])
       entries = entries.filter(project_filter)

       sample_type_families, multi_sample_type_families = self._get_family_sample_types(sample_data)
       family_q = None
       if multi_sample_type_families:
           family_q = Q(family_guid__in=multi_sample_type_families.keys())
       for sample_type, families in sample_type_families.items():
           sample_family_q = Q(family_guid__in=families)
           if not self.single_sample_type:
               sample_family_q &= Q(sample_type=sample_type)
           if family_q:
               family_q |= sample_family_q
           else:
               family_q = sample_family_q

       entries = entries.filter(family_q)

       quality_filter = qualityFilter or {}
       individual_genotype_filter = (inheritance_filter or {}).get('genotype')
       custom_affected = (inheritance_filter or {}).get('affected') or {}
       if inheritance_mode or individual_genotype_filter or quality_filter:
            clinvar_override_q = AnnotationsQuerySet._clinvar_path_q(
               pathogenicity, _get_range_q=lambda path_range: Q(clinvar_join__pathogenicity__range=path_range),
            ) if self._has_clinvar() else None

            gt_map = []
            null_gt_map = []
            affected_sample_map = []
            no_quality_map = []
            quality_filter_conditions = self._sample_quality_filter(AFFECTED, quality_filter) # TODO clean up helper
            for s in sample_data:
                sample_gt_map = []
                null_gt_samples = []
                any_affected_samples = []
                no_quality_samples = []
                for sample in s['samples']:
                    affected = custom_affected.get(sample['individual_guid']) or sample['affected']
                    genotype = self._sample_genotype(sample, affected, inheritance_mode,individual_genotype_filter)
                    sample_id = next(iter(sample['sample_ids_by_type'].values()))
                    if genotype is not None:
                        sample_gt_map.append(f"'{sample_id}', {self.genotype_lookup[genotype]}")
                        if genotype in self.nullable_genotypes:
                            null_gt_samples.append(sample_id)
                    elif inheritance_mode == ANY_AFFECTED and affected == AFFECTED:
                       any_affected_samples.append(sample_id)
                    if quality_filter_conditions and quality_filter.get('affected_only') and affected != AFFECTED:
                        no_quality_samples.append(sample_id)

                if sample_gt_map:
                    gt_map.append(f"'{s['family_guid']}', map({', '.join(sample_gt_map)})")
                if null_gt_samples:
                    null_gt_map.append(f"'{s['family_guid']}', {null_gt_samples}")
                if any_affected_samples:
                    affected_sample_map.append(f"'{s['family_guid']}', {any_affected_samples}")
                if no_quality_samples:
                    no_quality_map.append(f"'{s['family_guid']}', {no_quality_samples}")

            if gt_map:
                gt_map = ', '.join(gt_map)
                gt_conditions = [
                    (gt_map, 'has(map({value})[family_guid][x.sampleId], {field})'),
                    (gt_map, 'not mapContains(map({value})[family_guid], x.sampleId)'),
                ]
                if null_gt_map:
                    gt_conditions.append((', '.join(null_gt_map), 'and(isNull({field}), has(map({value})[family_guid], x.sampleId))'))
                entries = entries.filter(calls__array_all={'OR': [{'gt': condition} for condition in gt_conditions]})
            elif affected_sample_map:
                entries = entries.filter(calls__array_exists={
                    'gt': (self.genotype_lookup[HAS_ALT], 'has({value}, {field})'),
                    'sampleId': (', '.join(affected_sample_map), 'has(map({value})[family_guid], {field})'),
                })

            if no_quality_map:
                quality_filter_conditions = {'OR': [
                    quality_filter_conditions,
                    {'sampleId': (', '.join(no_quality_map), 'has(map({value})[family_guid], {field})')},
                ]}
            if quality_filter_conditions:
                quality_q = Q(calls__array_all=quality_filter_conditions)
                if clinvar_override_q:
                    quality_q |= clinvar_override_q
                entries = entries.filter(quality_q)

            # call_q = None
            # multi_sample_type_quality_q = None
            # multi_sample_type_any_affected_q = None
            # for s in sample_data:
            #     sample_filters, any_affected_samples = self._family_sample_filters(s, inheritance_mode, individual_genotype_filter, quality_filter, custom_affected)
            #     if not (sample_filters or any_affected_samples):
            #         continue
            #     if s['family_guid'] in multi_sample_type_families:
            #         multi_sample_type_quality_q, multi_sample_type_any_affected_q = self._multi_sample_type_family_calls_q(
            #             multi_sample_type_quality_q, multi_sample_type_any_affected_q, s, sample_filters, any_affected_samples,
            #             clinvar_override_q, multi_sample_type_families,
            #         )
            #     else:
            #         sample_type = s['sample_types'][0]
            #         call_q = self._family_calls_q(
            #             call_q, s, sample_filters, sample_type, clinvar_override_q,
            #             any_affected_samples=any_affected_samples, filter_sample_type=not self.single_sample_type
            #         )

            #  With families with multiple sample types, can only filter rows after aggregating
            filtered_multi_sample_type_families = {
                family_guid: filters for family_guid, filters in multi_sample_type_families.items() if filters
            }
            #  TODO multi sample type
            if filtered_multi_sample_type_families:
                multi_type_q = Q(family_guid__in=filtered_multi_sample_type_families.keys())
                call_q = (call_q | multi_type_q) if call_q else multi_type_q
                entries = entries.annotate(passes_quality=~multi_type_q | (multi_sample_type_quality_q or Value(True)))
                if multi_sample_type_any_affected_q:
                    entries = entries.annotate(passes_inheritance=~multi_type_q | multi_sample_type_any_affected_q)
                else:
                    entries = self._annotate_failed_family_samples(entries, filtered_multi_sample_type_families)

            if quality_filter.get('vcf_filter'):
                q = Q(filters__len=0)
                if clinvar_override_q:
                    q |= clinvar_override_q
                entries = entries.filter(q)

       return self._annotate_calls(entries, sample_data, annotate_carriers, annotate_hom_alts, skip_individual_guid, multi_sample_type_families)

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
        any_affected_samples = []
        for sample in family_sample_data['samples']:
            affected = custom_affected.get(sample['individual_guid']) or sample['affected']
            sample_inheritance_filter = self._sample_genotype_filter(sample, affected, inheritance_mode, individual_genotype_filter)
            sample_quality_filter = self._sample_quality_filter(affected, quality_filter)
            if sample_inheritance_filter or sample_quality_filter:
                sample_filters.append((sample['sample_ids_by_type'], sample_inheritance_filter, sample_quality_filter))
            if inheritance_mode == ANY_AFFECTED and affected == AFFECTED:
                any_affected_samples.append(sample['sample_ids_by_type'])
        return sample_filters, any_affected_samples

    def _family_calls_q(self, call_q, family_sample_data, sample_filters, sample_type, clinvar_override_q, any_affected_samples=None, filter_sample_type=True):
       family_sample_q = None
       if any_affected_samples:
           affected_sample_ids = [f"'{sample_ids_by_type[sample_type]}'" for sample_ids_by_type in any_affected_samples]
           family_sample_q = Q(calls__array_exists={
               'gt': self.genotype_lookup[HAS_ALT],
               'sampleId': (', '.join(affected_sample_ids), 'has([{value}], {field})'),
           })

       for sample_ids_by_type, sample_inheritance_filter, sample_quality_filter in sample_filters:
           sample_inheritance_filter['sampleId'] = (f"'{sample_ids_by_type[sample_type]}'",)
           sample_q = Q(
               calls__array_exists={**sample_inheritance_filter, **sample_quality_filter},
               family_guid=family_sample_data['family_guid'],
               project_guid= family_sample_data['project_guid'],
           )
           if filter_sample_type:
               sample_q &= Q(sample_type=sample_type)
           if clinvar_override_q and sample_quality_filter:
               sample_q |= clinvar_override_q & Q(calls__array_exists=sample_inheritance_filter)

           if family_sample_q is None:
               family_sample_q = sample_q
           else:
               family_sample_q &= sample_q

       if family_sample_q and call_q:
           call_q |= family_sample_q
       return call_q or family_sample_q

    def _multi_sample_type_family_calls_q(self, call_q, any_affected_q, family_sample_data, sample_filters, any_affected_samples, clinvar_override_q, multi_sample_type_families):
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
                call_q = self._family_calls_q(
                    call_q, family_sample_data, sample_quality_filters, sample_type, clinvar_override_q,
                )
        if any_affected_samples:
            multi_sample_type_families[family_sample_data['family_guid']] = True
            for sample_type in family_sample_data['sample_types']:
                any_affected_q = self._family_calls_q(
                    any_affected_q, family_sample_data, [], sample_type, clinvar_override_q,
                    any_affected_samples= any_affected_samples
                )

        return call_q, any_affected_q

    def _sample_genotype(self, sample, affected, inheritance_mode, individual_genotype_filter):
        genotype = None
        if individual_genotype_filter:
            genotype = individual_genotype_filter.get(sample['individual_guid'])
        elif inheritance_mode:
            genotype = self.INHERITANCE_FILTERS.get(inheritance_mode, {}).get(affected)
            if (inheritance_mode == X_LINKED_RECESSIVE and affected == UNAFFECTED and sample['sex'] in MALE_SEXES):
                genotype = REF_REF
        return genotype

    def _sample_genotype_filter(self, sample, affected, inheritance_mode, individual_genotype_filter):
        sample_filter = {}
        genotype = self._sample_genotype(sample, affected, inheritance_mode, individual_genotype_filter)
        if genotype:
            sample_filter['gt'] = self.genotype_lookup[genotype]
        return sample_filter

    def _sample_quality_filter(self, affected, quality_filter):
        sample_filter = {}
        if quality_filter.get('affected_only') and affected != AFFECTED:
            return sample_filter

        for field, scale, *filters in self.quality_filters:
            filter_key = f'min_{field}'
            if field == 'gq' and 'cn' in self.call_fields:
                filter_key += '_sv'
            value = quality_filter.get(filter_key)
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

    def _annotate_calls(self, entries, sample_data=None, annotate_carriers=False, annotate_hom_alts=False, skip_individual_guid=False, multi_sample_type_families=None):
        carriers_expression = self._carriers_expression(sample_data) if annotate_carriers else None
        if carriers_expression:
            entries = entries.annotate(carriers=carriers_expression)
        if annotate_hom_alts:
            entries = entries.annotate(has_hom_alt=Q(calls__array_exists={'gt': (2,)}))

        genotype_override_annotations = {
            f'sample_{col}': ArrayMap(
                ArrayFilter('calls', conditions=[{'cn': (None, 'isNotNull({field})')}]),
                mapped_expression=f'x.{field}',
            ) for col, (field, _) in self.annotations_model.GENOTYPE_OVERRIDE_FIELDS.items()
        }
        if genotype_override_annotations:
            entries = entries.annotate(**genotype_override_annotations)

        fields = ['key']
        if 'seqrPop' in entries.query.annotations:
            fields.append('seqrPop')
        if self._has_clinvar():
             fields += ['clinvar', 'clinvar_key']
        if multi_sample_type_families or sample_data is None or len(sample_data) > 1:
            genotype_sample_data = None if skip_individual_guid else sample_data
            entries = entries.values(*fields).annotate(
                familyGuids=ArraySort(ArrayDistinct(GroupArray('family_guid'))),
                **{'genotypes' if genotype_sample_data else 'familyGenotypes': GroupArrayArray(self.genotype_expression(genotype_sample_data))},
                **{col: GroupArrayArray(col) for col in genotype_override_annotations}
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
            if annotate_hom_alts:
                entries = entries.annotate(no_hom_alt_families=ArrayMap(
                    ArrayFilter(GroupArray(Tuple('family_guid', 'has_hom_alt')), conditions=[{2: (None, 'NOT {field}')}]),
                    mapped_expression='x.1',
                    output_field=models.ArrayField(models.StringField()),
                ))
            if any((multi_sample_type_families or {}).values()):
                entries = self._multi_sample_type_filtered_entries(entries)
        else:
            if carriers_expression:
                fields.append('carriers')
            if annotate_hom_alts:
                fields.append('has_hom_alt')
            entries = entries.values(
                *fields,
                familyGuids=Array('family_guid'),
                genotypes=self.genotype_expression(sample_data),
            )

        if genotype_override_annotations:
            entries = entries.annotate(**{
                f'sample_{col}': agg(f'sample_{col}', output_field=self.call_fields[field])
                for col, (field, agg) in self.annotations_model.GENOTYPE_OVERRIDE_FIELDS.items()
            })

        return entries

    def genotype_expression(self, sample_data=None):
        sample_map = []
        for data in sample_data or []:
            family_samples = []
            for s in data['samples']:
                family_samples += [
                    f"'{sample_id}', '{s['individual_guid']}'" for sample_id in set(s['sample_ids_by_type'].values())
                ]
            sample_map.append(f"'{data['family_guid']}', map({', '.join(family_samples)})")
        genotype_expressions = list(self.genotype_fields.keys())
        output_base_fields = list(self.genotype_fields.values())
        output_field_kwargs = {'group_by_key': 'familyGuid'}
        if sample_data:
            genotype_expressions.insert(0, f"map({', '.join(sample_map)})[family_guid][x.sampleId]")
            output_base_fields.insert(0, ('individualGuid', models.StringField()))
            output_field_kwargs = {'group_by_key': 'individualGuid', 'flatten_groups': True}
        return ArrayFilter(
            ArrayMap(
                'calls',
                mapped_expression=f"tuple({', '.join(genotype_expressions)})",
                output_field=NestedField(output_base_fields, **output_field_kwargs)
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

    @classmethod
    def _multi_sample_type_filtered_entries(cls, entries):
        if 'passes_inheritance' in entries.query.annotations:
            passes_inheritance_expression = cls._family_passes_expression('passes_inheritance')
        else:
            failed_samples_expression = GroupArrayIntersect('failed_family_samples')
            if 'missing_family_samples' in entries.query.annotations:
                # If variant is present in all sample types, it must pass inheritance for all samples in at least one type
                # If variant is present in only one sample type, it only needs to pass for samples present in that type
                failed_samples_expression = If(
                    failed_samples_expression,
                    GroupArrayIntersect(ArrayConcat('failed_family_samples', 'missing_family_samples')),
                    condition='count() = 1, ',
                )
            passes_inheritance_expression = ArraySymmetricDifference(
                'familyGuids',
                ArrayMap(failed_samples_expression, mapped_expression='x.1'),
                output_field=models.ArrayField(models.StringField()),
            )

        entries = entries.annotate(
            pass_inheritance_families=passes_inheritance_expression,
            pass_quality_families=cls._family_passes_expression('passes_quality'),
        )
        entries = entries.annotate(
            familyGuids=ArraySort(ArrayDistinct(ArrayIntersect('pass_inheritance_families', 'pass_quality_families')))
        )
        return entries.filter(familyGuids__not_empty=True)

    @staticmethod
    def _family_passes_expression(pass_field):
        return ArrayMap(
            ArrayFilter(
                GroupArray(Tuple('family_guid', pass_field)),
                conditions=[{2: (None, '{field}')}],
            ),
            mapped_expression='x.1', output_field=models.ArrayField(models.StringField()),
        )

    def filter_intervals(self, exclude_intervals=False, intervals=None, gene_intervals=None, variant_ids=None, padded_interval=None, **kwargs):
        entries = self
        if variant_ids:
            # although technically redundant, the interval query is applied to the entries table before join and reduces the join size,
            # while the full variant_id filter is applied to the annotation table after the join
            intervals = [(chrom, pos, pos) for chrom, pos, _, _ in variant_ids]

        if not (gene_intervals or intervals):
            return entries

        if padded_interval:
            pos = padded_interval['start']
            padding = int((padded_interval['end'] - pos) * padded_interval['padding'])
            intervals = [(padded_interval['chrom'], max(pos - padding, MIN_POS), min(pos + padding, MAX_POS))]
        elif 'cn' in self.call_fields:
            # SV interval filtering occurs after joining on annotations to correctly incorporate end position
            if exclude_intervals:
                intervals = None
            else:
                chromosomes = {chrom for chrom, _, _ in (gene_intervals or []) + (intervals or [])}
                intervals = [(chrom, MIN_POS, MAX_POS) for chrom in chromosomes]
        elif gene_intervals:
            intervals = (intervals or []) + gene_intervals

        if intervals:
            interval_q = self._interval_query(*intervals[0])
            for interval in intervals[1:]:
                interval_q |= self._interval_query(*interval)
            filter_func = entries.exclude if exclude_intervals else entries.filter
            entries = filter_func(interval_q)

        return entries

    @staticmethod
    def _interval_query(chrom, start, end):
        return Q(xpos__range=(get_xpos(chrom, start), get_xpos(chrom, end)))

    def _filter_seqr_frequency(self, entries, ac=None, hh=None, **kwargs):
        if ac is not None:
            entries = entries.annotate(ac=F('seqrPop__0') if self.single_sample_type else Plus('seqrPop__0', 'seqrPop__1'))
            entries = entries.filter(ac__lte=ac)
        if hh is not None and 'hom' in self.annotations_model.SEQR_POPULATIONS[0][1]:
            entries = entries.annotate(hom=F('seqrPop__1') if self.single_sample_type else Plus('seqrPop__2', 'seqrPop__3'))
            entries = entries.filter(hom__lte=hh)
        return entries
