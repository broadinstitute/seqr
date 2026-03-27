from clickhouse_backend import models
from collections import OrderedDict, defaultdict

from django.db.models import Count, F, QuerySet, Q, Value
from django.db.models.expressions import Col
from django.db.models.functions import Cast
from django.db.models.sql.constants import INNER

from clickhouse_search.backend.fields import NestedField, NamedTupleField
from clickhouse_search.backend.functions import Array, ArrayConcat, ArrayDistinct, ArrayFilter, ArrayFold, \
    ArrayIntersect, ArrayJoin, ArrayMap, ArraySort, ArraySymmetricDifference, CrossJoin, GroupArray, GroupArrayArray, \
    GroupArrayIntersect, If, MapLookup, NullIf, Plus, SubqueryJoin, SubqueryTable, Tuple, TupleConcat, Untuple, \
    IntDiv, Modulo, SplitByString, ArrayIndex, Multiply, IndexOf
from clickhouse_search.models.postgres_dicts import AffectedDict, SexDict
from clickhouse_search.constants import INHERITANCE_FILTERS, ANY_AFFECTED, AFFECTED, UNAFFECTED, MALE_SEXES, \
    X_LINKED_RECESSIVE, REF_REF, REF_ALT, ALT_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, SCREEN_KEY, UTR_ANNOTATOR_KEY, \
    EXTENDED_SPLICE_KEY, MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY, CLINVAR_KEY, HGMD_KEY, NEW_SV_FIELD, \
    EXTENDED_SPLICE_REGION_CONSEQUENCE, CLINVAR_PATH_RANGES, CLINVAR_PATH_SIGNIFICANCES, CLINVAR_LIKELY_PATH_FILTER, \
    CLINVAR_CONFLICTING_P_LP, CLINVAR_CONFLICTING_NO_P, CLINVAR_CONFLICTING, PATH_FREQ_OVERRIDE_CUTOFF, \
    HGMD_CLASS_FILTERS, SV_TYPE_FILTER_FIELD, SV_CONSEQUENCES_FIELD, COMPOUND_HET, COMPOUND_HET_ALLOW_HOM_ALTS, \
    X_LINKED_RECESSIVE_MALE_AFFECTED, FEMALE_SEXES, SV_ANNOTATION_TYPES
from seqr.utils.xpos_utils import get_xpos, parse_variant_id, MIN_POS, MAX_POS, CHROMOSOME_CHOICES


class InvalidSearchException(Exception):
    pass

class InvalidDatasetTypeException(Exception):
    pass


class SearchQuerySet(QuerySet):

    @property
    def table_basename(self):
        return self.model._meta.db_table.rsplit('/', 1)[0]

    @staticmethod
    def _pathogenicity_tuple(model, field_prefix, **kwargs):
        fields = OrderedDict({
            f'{field_prefix}__{field.name}': (field.db_column or field.name, field)
            for field in reversed(model.rel.related_model._meta.local_fields) if field.name != 'key'
        })
        return Tuple(
            *fields.keys(),
            output_field=NamedTupleField(list(fields.values()), null_if_empty=True, null_empty_arrays=True, **kwargs),
        )

    @classmethod
    def _clinvar_filter_q(cls, pathogenicity, allowed_filters=None):
        clinvar_filters = (pathogenicity or {}).get(CLINVAR_KEY)
        if allowed_filters:
            clinvar_filters = [f for f in (clinvar_filters or []) if f in allowed_filters]
        if not clinvar_filters:
            return None

        ranges = [[None, None]]
        include_conflicting_p = CLINVAR_CONFLICTING_P_LP in clinvar_filters
        include_conflicting_no_p = CLINVAR_CONFLICTING_NO_P in clinvar_filters
        for path_filter, start, end in CLINVAR_PATH_RANGES:
            if path_filter in clinvar_filters or (path_filter == CLINVAR_CONFLICTING and include_conflicting_p and include_conflicting_no_p):
                ranges[-1][1] = end
                if ranges[-1][0] is None:
                    ranges[-1][0] = start
            elif ranges[-1] != [None, None]:
                ranges.append([None, None])
        ranges = [r for r in ranges if r[0] is not None]

        clinvar_qs = [cls._clinvar_range_q(path_range) for path_range in ranges]

        conflicting_filter = None
        if include_conflicting_p and not include_conflicting_no_p:
            conflicting_filter = ('array_exists', "{field} <= '{value}'")
        elif include_conflicting_no_p and not include_conflicting_p:
            conflicting_filter = ('array_all', "{field} > '{value}'")
        if conflicting_filter is not  None:
            path_cutoff = next(end for path_filter, _, end in CLINVAR_PATH_RANGES if path_filter == CLINVAR_LIKELY_PATH_FILTER)
            clinvar_qs.append(Q(**cls._clinvar_conflicting_path_filter(
                conflicting_filter[0], {1: (path_cutoff, conflicting_filter[1])},
            )))

        clinvar_q = clinvar_qs[0]
        for q in clinvar_qs[1:]:
            clinvar_q |= q

        if pathogenicity.get('clinvarMinStars'):
            clinvar_q &= cls._clinvar_star_q(pathogenicity['clinvarMinStars'])

        return clinvar_q

    @property
    def gt_stats_dict(self):
        if self.gt_stats_dict_rel is None:
            return None
        return self.gt_stats_dict_rel.rel.related_model

    def _annotate_seqr_pop_expression(self, results):
        if self.gt_stats_dict is None:
            return results
        return results.annotate(seqrPop=self.gt_stats_dict.dict_get_expression('key'))

    def _format_gene_intervals(self, genes):
        return [
            {field: gene[f'{field}Grch{self.genome_version}'] for field in ['chrom', 'start', 'end']} for gene in genes.values()
        ]

    @classmethod
    def _prediction_expression(cls, model):
        pred_expressions = []
        all_pred_fields = []
        for pred_source, field_map in model.PREDICTIONS.items():
            pred_model = getattr(model, pred_source).rel.related_model
            pred_expression = pred_model.dict_get_expression('key', null_missing=True, force_tuple=True)
            pred_expressions.append(pred_expression)
            for field_name, output_field in pred_expression.output_field.base_fields:
                if field_name in field_map:
                    field_name, output_field = field_map[field_name]
                elif field_name == 'score':
                    field_name = pred_source
                all_pred_fields.append((field_name, output_field))

        for pred_name, range_dict in model.RANGE_PREDICTIONS.items():
            pred_expression = cls._xpos_range_dict_get_expression(range_dict, 'score')
            pred_expressions.append(Tuple(pred_expression))
            all_pred_fields.append((pred_name, pred_expression.output_field))

        return TupleConcat(*pred_expressions, output_field=NamedTupleField(all_pred_fields))

    @staticmethod
    def _xpos_range_dict_get_expression(range_dict, field_name):
        return range_dict.dict_get_expression(
            IntDiv('xpos', int(1e9)), Modulo('xpos', int(1e9)), field_names=[field_name], null_missing=True,
        )

    @staticmethod
    def _population_expression(model):
        expressions = []
        output_fields = []
        for pop in model.POPULATIONS:
            expr = getattr(model, pop).rel.related_model.dict_get_expression('key')
            expressions.append(expr)
            output_fields.append((pop, expr.output_field))

        return Tuple(*expressions, output_field=NamedTupleField(output_fields))

    def _filter_in_silico(self, results, in_silico=None, **kwargs):
        in_silico = in_silico or {}
        require_score = in_silico.get('requireScore', False)

        results, has_required_filter, in_silico_q, missing_q = self._parse_in_silico_qs(
            results, in_silico, require_score, [], [],
        )

        if in_silico_q:
            if missing_q:
                in_silico_q |= missing_q
            results = results.filter(in_silico_q)
        elif has_required_filter:
            results = results.none()

        return results

    def _parse_in_silico_qs(self, results, in_silico, require_score, in_silico_qs, in_silico_missing_qs):
        in_silico_q = in_silico_qs[0] if in_silico_qs else None
        for score_q in in_silico_qs[1:]:
            in_silico_q |= score_q

        missing_q = in_silico_missing_qs[0] if in_silico_missing_qs else None
        for score_q in in_silico_missing_qs[1:]:
            missing_q &= score_q

        has_required_filter = require_score and any(val for val in (in_silico or {}).values())

        return results, has_required_filter, in_silico_q, missing_q

    def filter_variant_ids(self, variant_ids):
        keys = self.key_lookup_model.objects.filter(variant_id__in=variant_ids).values_list('key', flat=True)
        return self.filter(key__in=keys)

    @staticmethod
    def split_variant_id_annotations():
        split_id_expression = SplitByString(Value('-'), 'variant_id', output_field=models.ArrayField(models.StringField()))
        annotations = {
            field: ArrayIndex(index, split_id_expression)
            for index, field in  enumerate(['chrom', 'pos', 'ref', 'alt'])
        }
        annotations['pos'] = Cast(annotations['pos'], models.UInt32Field())
        return annotations

    @property
    def skip_annotations(self):
        return []

    @property
    def annotation_fields(self):
        return [field.name for field in self.model._meta.local_fields if (field.db_column or field.name) == field.name]

    @property
    def annotation_values(self):
        return {
            field.db_column: F(field.name) for field in self.model._meta.local_fields
            if field.db_column and field.name != field.db_column and field.db_column
        }

    def result_values(self, additional_fields=None, **kwargs):
        fields = [*self.annotation_fields] + (additional_fields or [])
        values = {**self.annotation_values}
        values.update(self.conditional_selects(self, **kwargs))

        override_model_annotations = set(values).intersection(fields)
        initial_values = {k: v for k, v in  values.items() if k not in override_model_annotations and k not in self.skip_annotations}
        fields = [field for field in fields if field not in values and field not in self.skip_annotations]

        return self.values(*fields, **initial_values).annotate(
            **{k: values[k] for k in override_model_annotations if k in values},
        )

class BaseVariantsQuerySet(SearchQuerySet):

    TRANSCRIPT_FIELD = 'sorted_transcript_consequences'
    GENE_CONSEQUENCE_FIELD = 'gene_consequences'
    FILTERED_CONSEQUENCE_FIELD = 'filtered_transcript_consequences'

    ENTRY_FIELDS = ['familyGuids', 'genotypes']

    SELECTED_GENE_FIELD = 'selectedGeneId'

    @property
    def key_lookup_model(self):
        return next(obj.related_model for obj in self.model._meta.related_objects if obj.name.startswith('keylookup'))

    @property
    def annotation_values(self):
        annotations = super().annotation_values
        pop_field = self._population_annotation_field()
        if not pop_field:
            return annotations

        seqr_pops = []
        population_fields = [*self._population_output_fields()]
        self._get_seqr_pop_expressions(seqr_pops, population_fields)

        return {
            **annotations,
            **{key: Value(value) for key, value in self.model.ANNOTATION_CONSTANTS.items()},
            'populations': TupleConcat(F(pop_field), Tuple(*seqr_pops), output_field=NamedTupleField(population_fields)),
        }

    def _population_annotation_field(self):
        return 'populations'

    def _population_output_fields(self):
        return self.model.POPULATION_FIELDS

    def _get_seqr_pop_expressions(self, seqr_pops, population_fields):
        if self.gt_stats_dict is None:
            return

        seqr_pops_by_name = {}
        for name, ac_field in self.gt_stats_dict.SEQR_POPULATIONS:
            seqr_pops_by_name[name] = (
                self._seqr_subfield_pop_expressions(ac_field, subfield_name='ac') +
                self._seqr_subfield_pop_expressions('hom')
            )
            seqr_pops_by_name[f'{name}_affected'] = (
                self._seqr_subfield_pop_expressions(ac_field, affected=True, subfield_name='ac') +
                self._seqr_subfield_pop_expressions('hom', affected=True)
            )

        for name, pop_subfields in seqr_pops_by_name.items():
            seqr_pops.append(Tuple(*[expr for _, expr in pop_subfields]))
            population_fields.append((name, NamedTupleField([(field, models.UInt32Field()) for field, _ in pop_subfields])))

        return seqr_pops

    def _seqr_subfield_pop_expressions(self, subfield, subfield_name=None, affected=False):
        seqr_pop_fields = [field_name for field_name, _ in self.gt_stats_dict.base_fields()]
        pop_expressions = [
            (field, F(f'seqrPop__{seqr_pop_fields.index(field)}')) for field in seqr_pop_fields
            if field.startswith(subfield) and (field.endswith('affected') == affected)
        ]
        if len(pop_expressions) == 1:
            pop_expressions = [(subfield, pop_expressions[0][1])]
        elif len(pop_expressions) > 1:
            combined = Plus(*[expr for _, expr in pop_expressions])
            pop_expressions.append((subfield, combined))
        if subfield_name and subfield_name != subfield:
            pop_expressions = [(name.replace(subfield, subfield_name), expr) for name, expr in pop_expressions]
        return pop_expressions

    @property
    def annotation_fields(self):
        return [field for field in super().annotation_fields if field != self.TRANSCRIPT_FIELD]

    @property
    def variant_detail_field(self):
        return next((obj.name for obj in self.model._meta.related_objects if obj.name.startswith('variantdetails')), None)

    @property
    def entry_field(self):
        return next(obj.name for obj in self.model._meta.related_objects if obj.name.startswith('entries'))

    @property
    def entry_model(self):
         return getattr(self.model, f'{self.entry_field}_set').rel.related_model

    @property
    def gt_stats_dict_rel(self):
        return getattr(self.entry_model, 'gt_stats', None)

    @property
    def genome_version(self):
        return self.model.ANNOTATION_CONSTANTS['genomeVersion']


    def subquery_join(self, subquery, join_key='key'):
        join_field = next(field for field in subquery.model._meta.fields if field.name == join_key)

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
        for select_func_name in (conditional_selects or []):
            query_select.update(getattr(query, select_func_name)(query, prefix=f'{alias}_'))
        annotation_fields = query.annotation_fields
        return query.values(
            **{f'{alias}_{field}': F(field) for field in annotation_fields if field not in query_select and field not in self.skip_annotations},
            **{f'{alias}_{field}': value for field, value in query_select.items() if field not in self.skip_annotations},
        )

    def search(self, **kwargs):
        results = self._filter_frequency(self, **kwargs)
        results = self._filter_in_silico(results, **kwargs)
        results = self._filter_annotations(results, **kwargs)
        return results

    def join_variant_id(self):
        if hasattr(self.model, 'variant_id'):
            return self
        return self.filter(**{
            f'{self.variant_detail_field}__isnull': False,  # Ensures INNER join
        }).annotate(variant_id=F(f'{self.variant_detail_field}__variant_id'))

    def result_values(self, *args, skip_entry_fields=False, **kwargs):
        additional_fields = [
            field for field in ['clinvar', 'familyGenotypes', 'numFamilies'] if self.has_annotation(field)
        ]
        if 'familyGenotypes' not in additional_fields and not skip_entry_fields:
            additional_fields += self.ENTRY_FIELDS

        return super().result_values(additional_fields=additional_fields, skip_entry_fields=skip_entry_fields, **kwargs)

    def join_annotations(self):
        return self._annotate_seqr_pop_expression(self)

    def conditional_selects(self, query, prefix='', **kwargs):
        raise NotImplementedError

    def search_compound_hets(self, primary_q, secondary_q):
        primary_gene_field = f'primary_{self.SELECTED_GENE_FIELD}'
        secondary_gene_field = f'secondary_{self.SELECTED_GENE_FIELD}'
        primary_q = primary_q.explode_gene_id(primary_gene_field)
        secondary_q = secondary_q.explode_gene_id(secondary_gene_field)

        results = self.cross_join(
            query=primary_q, alias='primary', join_query=secondary_q, join_alias='secondary',
            conditional_selects=['_comp_het_conditional_fields', 'conditional_selects'],
        )
        return results.filter(
            **{primary_gene_field: F(secondary_gene_field)}
        ).exclude(primary_key=F('secondary_key'))

    def _comp_het_conditional_fields(self, query, prefix=''):
        return {
            field: F(field) for field in [self.SELECTED_GENE_FIELD, 'clinvar', 'family_carriers', 'carriers', 'has_hom_alt', 'no_hom_alt_families', 'familyGenotypes'] + self.ENTRY_FIELDS
            if field in query.query.annotations
        }

    @property
    def populations(self):
        return {
            population: {subfield for subfield, _ in field.base_fields}
            for population, field in self.model.POPULATION_FIELDS
        }

    def _filter_frequency(self, results, **kwargs):
        return results

    def _filter_annotations(self, results, annotations_filter_q=None, transcript_filters=None, genes=None, intervals=None, exclude_locations=False, **kwargs):
        if exclude_locations and genes:
            intervals = self._format_gene_intervals(genes)
            genes = None

        results = self._filter_locations(results, genes, intervals, exclude_locations=exclude_locations, **kwargs)

        if not (annotations_filter_q or transcript_filters):
            return results

        if annotations_filter_q:
            results = results.annotate(passes_annotation=annotations_filter_q)
            annotations_filter_q = Q(passes_annotation=True)

        if transcript_filters:
            consequence_field = self.GENE_CONSEQUENCE_FIELD if genes else self.TRANSCRIPT_FIELD
            results = self._annotate_filtered_transcripts(results, consequence_field, transcript_filters, **kwargs)
            transcript_q = Q(filtered_transcript_consequences__not_empty=True)
            if annotations_filter_q:
                annotations_filter_q |= transcript_q
            else:
                annotations_filter_q = transcript_q

        return results.filter(annotations_filter_q)

    def _annotate_filtered_transcripts(self, results, consequence_field, transcript_filters, **kwargs):
        return results.annotate(**{
            self.FILTERED_CONSEQUENCE_FIELD: ArrayFilter(consequence_field, conditions=transcript_filters),
        })

    def _filter_locations(self, results, genes, intervals, **kwargs):
        if genes:
            results = results.annotate(**{
                self.GENE_CONSEQUENCE_FIELD: ArrayFilter(self.TRANSCRIPT_FIELD, conditions=[{
                    'geneId': (sorted(genes.keys()), 'has({value}, {field})'),
                }]),
            })
            gene_q = Q(gene_consequences__not_empty=True)
            for interval in (intervals or []):
                gene_q |= self._interval_query(**interval)
            results = results.filter(gene_q)

        return results

    def _interval_query(self, chrom, start, end, offset=None, **kwargs):
        if offset:
            offset_pos = int((end - start) * offset)
            start = max(start - offset_pos, MIN_POS)
            end = min(end + offset_pos, MAX_POS)
        return Q(xpos__range=(get_xpos(chrom, start), get_xpos(chrom, end)))

    def get_parsed_annotations_filters(self, annotations=None, pathogenicity=None, **kwargs):
        annotations = {k: v for k, v in (annotations or {}).items() if v}
        pathogenicity = {k: v for k, v in (pathogenicity or {}).items() if v}
        filter_qs, transcript_filters = self._parse_annotation_filters(annotations, pathogenicity)
        filter_q = filter_qs[0] if filter_qs else None
        for q in filter_qs[1:]:
            filter_q |= q

        return {'annotations_filter_q': filter_q, 'transcript_filters': transcript_filters}

    def _parse_annotation_filters(self, annotations, pathogenicity):
        raise NotImplementedError

    def explode_gene_id(self, gene_id_key):
        consequence_field = self.GENE_CONSEQUENCE_FIELD if self.has_annotation(self.GENE_CONSEQUENCE_FIELD) else self.TRANSCRIPT_FIELD
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


class VariantsQuerySet(BaseVariantsQuerySet):

    @property
    def hgmd_join_model(self):
        return getattr(self.model, 'hgmd_join', None)

    @property
    def sorted_transcript_consequence_fields(self):
        return set(dict(getattr(self.model, 'SORTED_TRANSCRIPT_CONSQUENCES_FIELDS', [])).keys())

    @property
    def annotation_fields(self):
        return super().annotation_fields + [field for field in ['xpos'] if self.has_annotation(field)]

    @property
    def skip_annotations(self):
        return {
            'sortedMotifFeatureConsequences', 'sortedRegulatoryFeatureConsequences', *self.model.VARIANT_PREDICTIONS,
        }

    @property
    def annotation_values(self):
        annotations = super().annotation_values
        if not self.has_annotation('preds'):
            return annotations

        pred_expr = F('preds')
        if getattr(self.model, 'VARIANT_PREDICTIONS', None):
            preds = [annotations.get(field, F(field)) for field in self.model.VARIANT_PREDICTIONS]
            output_fields = self.query.annotations['preds'].output_field.base_fields + [
                (field.name, field) for field in self.model._meta.local_fields
                if (field.db_column or field.name) in self.model.VARIANT_PREDICTIONS
            ]
            pred_expr = TupleConcat(pred_expr, Tuple(*preds), output_field=NamedTupleField(output_fields))
        annotations['predictions'] = pred_expr

        if self.hgmd_join_model:
            annotations['hgmd'] = self._pathogenicity_tuple(self.hgmd_join_model, 'hgmd_join', rename_fields={'classification': 'class'})

        if not self.sorted_transcript_consequence_fields and hasattr(self.model, 'sorted_transcript_consequences'):
            annotations.update({
                'transcripts':  annotations.pop(self.model.sorted_transcript_consequences.field.db_column),
                'mainTranscriptId': F('sorted_transcript_consequences__0__transcriptId'),
                'selectedMainTranscriptId': Value(None, output_field=models.StringField(null=True)),
                **self.split_variant_id_annotations(),
            })

        screen_expression = self._screen_expression()
        if screen_expression:
            annotations['screenRegionType'] = screen_expression

        if self.has_annotation('mitomapPathogenic'):
            annotations['mitomapPathogenic'] = F('mitomapPathogenic')

        return annotations

    @staticmethod
    def _hgmd_filter_q(hgmd):
        min_class = next((class_name for value, class_name in HGMD_CLASS_FILTERS if value in hgmd), None)
        max_class = next((class_name for value, class_name in reversed(HGMD_CLASS_FILTERS) if value in hgmd), None)
        if 'hgmd_other' in hgmd:
            min_class = min_class or 'DP'
            max_class = None
        if min_class == max_class:
            return Q(hgmd_join__classification=min_class)
        elif min_class and max_class:
            return Q(hgmd_join__classification__range=(min_class, max_class))
        return Q(hgmd_join__classification__gt=min_class)

    @staticmethod
    def _clinvar_range_q(path_range):
        return Q(clinvar__0__range=path_range, clinvar_key__isnull=False)

    @staticmethod
    def _clinvar_star_q(min_stars):
        return Q(clinvar__4__gte=min_stars, clinvar_key__isnull=False)

    @staticmethod
    def _clinvar_conflicting_path_filter(array_func, conflicting_filter):
        return {f'clinvar__5__{array_func}': conflicting_filter, 'clinvar__5__not_empty': True, 'clinvar_key__isnull': False}

    def _population_annotation_field(self):
        return 'pops' if self.has_annotation('pops') else None

    def _population_output_fields(self):
        return self.query.annotations['pops'].output_field.base_fields

    def _screen_expression(self):
        if not getattr(self.model, 'SCREEN_DICT', None):
            return None
        return self._xpos_range_dict_get_expression(self.model.SCREEN_DICT, 'regionType')

    def _parse_in_silico_qs(self, results, in_silico, require_score, in_silico_qs, in_silico_missing_qs):
        in_silico_q = None
        missing_q = None

        if self.has_annotation('pass_in_silico'):
            in_silico_q = Q(pass_in_silico=True) | (Q(sorted_transcript_consequences__array_exists={
                'alphamissensePathogenicity': (in_silico['alphamissense'], '{value} <= {field}'),
            }))
            if not require_score:
                missing_q = Q(missing_in_silico=True, sorted_transcript_consequences__array_all={
                    'alphamissensePathogenicity': (None, 'isNull({field})'),
                })

        return results, False, in_silico_q, missing_q

    def _filter_annotations(self, results, *args, exclude=None, pathogenicity=None, **kwargs):
        screen_expression = self._screen_expression()
        if screen_expression:
            results = results.annotate(screen=self._screen_expression())

        results = super()._filter_annotations(results, *args, **kwargs)

        if (exclude or {}).get(CLINVAR_KEY) and (pathogenicity or {}).get(CLINVAR_KEY):
            duplicates = set(pathogenicity[CLINVAR_KEY]).intersection(exclude[CLINVAR_KEY])
            if duplicates:
                raise InvalidSearchException(f'ClinVar pathogenicity {", ".join(sorted(duplicates))} is both included and excluded')

        exclude_clinvar_q = self._clinvar_filter_q(exclude)
        if exclude_clinvar_q is not None:
            results = results.exclude(exclude_clinvar_q)

        return results

    def _parse_annotation_filters(self, annotations, pathogenicity):
        filter_qs = []
        allowed_consequences = []
        transcript_field_filters = {}
        for field, value in annotations.items():
            if field == UTR_ANNOTATOR_KEY:
                if value:
                    transcript_field_filters['fiveutrConsequence'] = (value,  'hasAny({value}, [{field}])')
            elif field == EXTENDED_SPLICE_KEY:
                if EXTENDED_SPLICE_REGION_CONSEQUENCE in value:
                    transcript_field_filters['extendedIntronicSpliceRegionVariant'] = (1, '{field} = {value}')
                value = [c for c in value if c != EXTENDED_SPLICE_REGION_CONSEQUENCE]
                if value:
                    allowed_consequences += value
            elif field in [MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY]:
                filter_field = f'sorted_{field}_consequences'
                if hasattr(self.model, filter_field):
                    filter_qs.append(Q(**{
                        f'{filter_field}__array_exists': {'consequenceTerms': (value, 'hasAny({value}, {field})')},
                    }))
            elif field == SCREEN_KEY:
                if self.model.SCREEN_DICT:
                    filter_qs.append(Q(screen__in=value))
            elif field == 'mitomap_pathogenic':
                if self.has_annotation('mitomapPathogenic'):
                    filter_qs.append(Q(mitomapPathogenic=value))
            elif field == SPLICE_AI_FIELD:
                if value and SPLICE_AI_FIELD in self.entry_model.PREDICTIONS:
                    filter_qs.append(Q(preds__0__gte=float(value)))
            elif field not in SV_ANNOTATION_TYPES:
                allowed_consequences += value

        hgmd_filter = (pathogenicity or {}).get(HGMD_KEY)
        if hgmd_filter and self.hgmd_join_model:
            filter_qs.append(self._hgmd_filter_q(hgmd_filter))

        clinvar_q = self._clinvar_filter_q(pathogenicity)
        if clinvar_q is not None:
            filter_qs.append(clinvar_q)

        transcript_filters = [
            {field: value} for field, value in transcript_field_filters.items() if field in self.sorted_transcript_consequence_fields
        ]

        if allowed_consequences:
            transcript_filters += self._allowed_consequences_filters(allowed_consequences)

        if (annotations or pathogenicity) and not (filter_qs or transcript_filters):
            raise InvalidDatasetTypeException

        return filter_qs, transcript_filters

    def _allowed_consequences_filters(self, allowed_consequences):
        csq_filters = []
        non_canonical_consequences = [c for c in allowed_consequences if not c.endswith('__canonical')]
        if non_canonical_consequences:
            csq_filters.append(self._consequence_term_filter(non_canonical_consequences))

        canonical_consequences = [
            c.replace('__canonical', '') for c in allowed_consequences if c.endswith('__canonical')
        ]
        if canonical_consequences:
            csq_filters.append(
                self._consequence_term_filter(canonical_consequences, canonical=(0, '{field} > {value}')),
            )
        return csq_filters

    @staticmethod
    def _consequence_term_filter(consequences, **kwargs):
        return {'consequenceTerms': (consequences, 'hasAny({value}, {field})'), **kwargs}

    def _annotate_filtered_transcripts(self, results, consequence_field, transcript_filters, *args, require_mane_canonical=False, **kwargs):
        if require_mane_canonical:
            if 'isManeSelect' in self.sorted_transcript_consequence_fields:
                mane_genes_expression = 'arrayMap(a -> a.geneId, arrayFilter(b -> b.isManeSelect, sortedTranscriptConsequences))'
                conditions=[
                    {'isManeSelect': (True, '{field}')},
                    {'canonical': (mane_genes_expression, 'and({field} > 0, not has({value}, x.geneId))')},
                ]
            else:
                conditions = [{'canonical': (0, '{field} > {value}')}]
            results = results.annotate(**{self.FILTERED_CONSEQUENCE_FIELD: ArrayFilter(consequence_field, conditions=conditions)})
            consequence_field = self.FILTERED_CONSEQUENCE_FIELD
        return super()._annotate_filtered_transcripts(results, consequence_field, transcript_filters, **kwargs)

    def join_populations(self):
        return super().join_annotations().annotate(
            pops=self._population_expression(self.entry_model),
        )

    def join_annotations(self, annotate_xpos=False):
        results = self.join_populations()
        if annotate_xpos:
            results = results.annotate(**self.split_variant_id_annotations())
            results = results.annotate(xpos=Plus(
                Multiply(IndexOf('chrom', array=[chrom for _, chrom in CHROMOSOME_CHOICES]), Value(int(1e9))),
                F('pos'),
                output_field=models.UInt64Field(),
            ))
        results = results.annotate(
            preds=self._prediction_expression(self.entry_model),
            pops=self._population_expression(self.entry_model),
        )
        return results.join_clinvar()

    def join_clinvar(self, field_prefix=''):
        results = self.annotate(
            clinvar=self._pathogenicity_tuple(self.entry_model.clinvar_join, f'{field_prefix}{self.entry_field}__clinvar_join')
        )

        # Due to django modeling, adding a clinvar annotation will add a join to the entries table and then to clinvar
        # Manipulating the underlying join removes the entry join entirely
        entry_table = f'{self.table_basename}/entries'
        results.query.alias_map[f'{self.table_basename}/reference_data/clinvar'].parent_alias = results.query.alias_map[entry_table].parent_alias
        results.query.alias_refcount[entry_table] = 0
        return results

    def conditional_selects(self, query, prefix='', **kwargs):
        consequence_field = next((
            field for field in [self.FILTERED_CONSEQUENCE_FIELD, self.GENE_CONSEQUENCE_FIELD] if query.has_annotation(field)
        ), None)
        if not consequence_field:
            return {}
        if not self.sorted_transcript_consequence_fields:
            return {'selectedMainTranscriptId': NullIf(
                NullIf(F(f'{consequence_field}__0__transcriptId'), Value('')), f'{prefix}mainTranscriptId',
                output_field=models.StringField(null=True),
            )}
        if consequence_field == self.FILTERED_CONSEQUENCE_FIELD:
            return {'selectedTranscript':  F(f'{self.FILTERED_CONSEQUENCE_FIELD}__0')}
        return {self.SELECTED_GENE_FIELD: F(f'{self.GENE_CONSEQUENCE_FIELD}__0__geneId')}


class SvVariantsQuerySet(BaseVariantsQuerySet):
    TRANSCRIPT_FIELD = 'sorted_gene_consequences'
    GENOTYPE_GENE_CONSEQUENCE_FIELD = 'genotype_gene_consequences'

    @property
    def annotation_values(self):
        annotations = super().annotation_values
        annotations['transcripts'] = annotations.pop(self.model.sorted_gene_consequences.field.db_column)
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

    def conditional_selects(self, query, prefix='', skip_entry_fields=False, **kwargs):
        genotype_override_fields = query.model.GENOTYPE_OVERRIDE_FIELDS
        if skip_entry_fields or not genotype_override_fields:
            return {}

        genotype_field = next(field for field in ['genotypes', 'familyGenotypes'] if field in query.query.annotations)
        index_map = {
            field: i + 1 for i, (field, _) in
            enumerate(query.query.annotations[genotype_field].output_field.base_fields)
        }
        override_field_map = {field: col for col, (field, _) in genotype_override_fields.items()}
        genotype_fields = [
            self._genotype_override_expression(index_map[field], override_field_map[field], index_map['cn'])
            if field in override_field_map else (
                f'ifNull(x.{index_map[field]}, 0)' if field == 'numAlt' else f'x.{index_map[field]}')
            for (field, _) in query.query.annotations[genotype_field].output_field.base_fields
        ]

        return {
            genotype_field: ArrayMap(genotype_field, mapped_expression=f"tuple({', '.join(genotype_fields)})"),
            'transcripts': F(query.GENOTYPE_GENE_CONSEQUENCE_FIELD),
            **{col: F(f'sample_{col}') for col in genotype_override_fields if col != 'geneIds'},
        }

    def add_genotype_override_annotations(self, results):
        if self.model.GENOTYPE_OVERRIDE_FIELDS:
            results = results.annotate(**{
                self.GENOTYPE_GENE_CONSEQUENCE_FIELD: ArrayFilter(self.TRANSCRIPT_FIELD, conditions=[{
                    'geneId': (None, 'has(sample_geneIds, {field})'),
                }]),
            })
            self.TRANSCRIPT_FIELD = self.GENOTYPE_GENE_CONSEQUENCE_FIELD
        return results

    def _filter_annotations(self, results, *args, **kwargs):
        results = self.add_genotype_override_annotations(results)
        return super()._filter_annotations(results, *args, **kwargs)

    def _parse_annotation_filters(self, annotations, pathogenicity):
        filter_qs = []
        transcript_filters = []

        if annotations.get(SV_CONSEQUENCES_FIELD):
            transcript_filters.append(
                {'majorConsequence': (annotations[SV_CONSEQUENCES_FIELD], 'hasAny({value}, [{field}])')}
            )

        if annotations.get(SV_TYPE_FILTER_FIELD):
            filter_qs.append(Q(sv_type__in=[
                sv_type.replace(self.model.SV_TYPE_FILTER_PREFIX, '') for sv_type in annotations[SV_TYPE_FILTER_FIELD]
                if sv_type.startswith(self.model.SV_TYPE_FILTER_PREFIX)
            ]))

        if not (filter_qs or transcript_filters) and (pathogenicity or any(key for key in annotations.keys() if key != NEW_SV_FIELD)):
            #  Annotation filters restrict search to other dataset types
            raise InvalidDatasetTypeException

        return filter_qs, transcript_filters

    def _filter_locations(self, results, genes, intervals, exclude_locations=False, padded_interval_end=None, **kwargs):
        results = super()._filter_locations(results, genes, intervals, **kwargs)

        if genes:
            intervals = None
        if padded_interval_end:
            end, padding = padded_interval_end
            interval_qs = [Q(end__range=(end - padding, end + padding))]
        else:
            interval_qs = [self._interval_query(**interval) for interval in (intervals or [])]

        if not interval_qs:
            return results

        interval_q = interval_qs[0]
        for q in interval_qs[1:]:
            interval_q |= q
        filter_func = results.exclude if exclude_locations else results.filter
        return filter_func(interval_q)

    def _interval_query(self, chrom, start, end, *args, **kwargs):
        start_range_q = super()._interval_query(chrom, start, end, *args, **kwargs)
        end_range_q = Q(chrom=chrom, end__range=(start, end))
        contains_q = Q(chrom=chrom, pos__lte=start, end__gte=end)
        if hasattr(self.model, 'end_chrom'):
            end_range_q &= Q(end_chrom__isnull=True)
            contains_q  &= Q(end_chrom__isnull=True)
        return start_range_q | end_range_q | contains_q

    def _parse_in_silico_qs(self, results, in_silico, require_score, in_silico_qs, in_silico_missing_qs):
        for score, _ in self.model.PREDICTION_FIELDS:
            if in_silico.get(score):
                in_silico_qs.append(Q(**{f'predictions__{score}__gte': float(in_silico[score])}))
                if not require_score:
                    in_silico_missing_qs.append(Q(**{f'predictions__{score}__isnull': True}))

        return super()._parse_in_silico_qs(results, in_silico, require_score, in_silico_qs, in_silico_missing_qs)

    def _filter_frequency(self, results, freqs=None, pathogenicity=None, **kwargs):
        for population, pop_filter in (freqs or {}).items():
            pop_subfields = self.populations.get(population)
            if not pop_subfields:
                continue

            if pop_filter.get('af') is not None and pop_filter['af'] < 1:
                results = results.filter(**{f'populations__{population}__af__lte': pop_filter['af']})
            elif pop_filter.get('ac') is not None:
                if 'ac' in pop_subfields:
                    ac_field = f'populations__{population}__ac'
                else:
                    ac_field =  f'ac_{population}'
                    results = results.annotate(**{ac_field: F(f'populations__{population}__het') + (F(f'populations__{population}__hom') * 2)})

                results = results.filter(**{f'{ac_field}__lte': pop_filter['ac']})

            if pop_filter.get('hh') is not None:
                results = results.filter(**{f'populations__{population}__hom__lte': pop_filter['hh']})

        return results


class VariantDetailsQuerySet(VariantsQuerySet):

    @property
    def variant_model(self):
        return self.model.key.field.related_model

    @property
    def entry_field(self):
        return next(obj.name for obj in self.variant_model._meta.related_objects if obj.name.startswith('entries'))

    @property
    def entry_model(self):
        return getattr(self.variant_model, f'{self.entry_field}_set').rel.related_model

    @property
    def skip_annotations(self):
        return []

    @property
    def annotation_values(self):
        annotations = {
            **super().annotation_values,
            **self.split_variant_id_annotations(),
        }
        if self.has_annotation('hgmd_join'):
            annotations.update({
                'mainTranscriptId': F('transcripts__0__transcriptId'),
                'hgmd': F('hgmd_join'),
            })
        return annotations

    @property
    def table_basename(self):
        return self.model._meta.db_table.rsplit('/', 2)[0]

    def result_values(self, *args, skip_entry_fields=True, **kwargs):
        return super().result_values(*args, skip_entry_fields=skip_entry_fields, **kwargs)

    def join_annotations(self):
        results = super().join_annotations(annotate_xpos=bool(self.entry_model.RANGE_PREDICTIONS))
        results = results.annotate(
            hgmd_join=self._pathogenicity_tuple(self.variant_model.hgmd_join, 'key__hgmd_join', rename_fields={'classification': 'class'}),
        )
        self._prune_join(results, 'hgmd')
        return results

    def join_clinvar(self, *args, **kwargs):
        results = super().join_clinvar(field_prefix='key__')
        self._prune_join(results, 'clinvar')
        return results

    def _prune_join(self, results, data_source):
        variants_table = f'{self.table_basename}/variants_memory'
        results.query.alias_map[f'{self.table_basename}/reference_data/{data_source}'].parent_alias = results.query.alias_map[variants_table].parent_alias
        results.query.alias_refcount[variants_table] = 0

class BaseEntriesManager(SearchQuerySet):
    GENOTYPE_LOOKUP = {
        REF_REF: [0],
        REF_ALT: [1],
        ALT_ALT: [2],
        HAS_ALT: [1, 2],
        HAS_REF: [0, 1],
        None: [-1, 0, 1, 2],
    }
    COMP_HET_ALT = 'COMP_HET_ALT'
    GENOTYPE_LOOKUP[COMP_HET_ALT] = GENOTYPE_LOOKUP[REF_ALT]

    INHERITANCE_FILTERS = {
        **INHERITANCE_FILTERS,
        COMPOUND_HET: {**INHERITANCE_FILTERS[COMPOUND_HET], AFFECTED: COMP_HET_ALT},
        COMPOUND_HET_ALLOW_HOM_ALTS: {**INHERITANCE_FILTERS[COMPOUND_HET], AFFECTED: HAS_ALT},
    }

    QUALITY_FILTERS = {
        'gq': {},
        'ab': {'scale': 100, 'filters': ['x.gt != 1']},
        'hl': {'scale': 100},
        'mitoCn': {},
    }

    MAX_XPOS_FILTER_INTERVALS = 500

    @property
    def annotations_model(self):
        return self.model.key.field.related_model

    @property
    def key_lookup_model(self):
        return next(obj.related_model for obj in self.annotations_model._meta.related_objects if obj.name.startswith('keylookup'))

    @property
    def call_fields(self):
        return dict(self.model.CALL_FIELDS)

    @property
    def genotype_lookup(self):
        return self.GENOTYPE_LOOKUP

    @property
    def sample_type_expression(self):
        return 'sample_type'

    @property
    def genotype_fields(self):
        return OrderedDict({
            'family_guid': ('familyGuid', models.StringField()),
            self.sample_type_expression: ('sampleType', models.StringField()),
            'filters': ('filters', models.ArrayField(models.StringField())),
            'x.gt::Nullable(Int8)': ('numAlt', models.Int8Field(null=True, blank=True)),
            **{f'x.{name}': (name, output_field) for name, output_field in self.call_fields.items() if name != 'gt'}
        })

    @property
    def gt_stats_dict_rel(self):
        return getattr(self.model, 'gt_stats', None)

    @property
    def genome_version(self):
        return self.annotations_model.ANNOTATION_CONSTANTS['genomeVersion']

    @property
    def filtered_chrom(self):
        return self.annotations_model.ANNOTATION_CONSTANTS.get('chrom')

    @property
    def callset_filter_field(self):
        return 'callset'

    @classmethod
    def _clinvar_path_q(cls, pathogenicity):
        return cls._clinvar_filter_q(pathogenicity, allowed_filters=CLINVAR_PATH_SIGNIFICANCES)

    def search(self, sample_data, exclude_keys=None, **kwargs):
        entries = self

        if exclude_keys:
            entries = entries.exclude(key__in=exclude_keys)

        entries = self._join_annotations(entries)
        entries = self._prefilter_entries(entries, sample_data=sample_data, **kwargs)

        return self._search_call_data(entries, sample_data, **kwargs)

    def _prefilter_entries(self, entries, freqs=None, **kwargs):
        return self._filter_frequency(entries, freqs or {}, **kwargs)

    def _filter_frequency(self, entries, frequencies, **kwargs):
        if frequencies.get(self.callset_filter_field) and self.gt_stats_dict_rel is not None:
            entries = self._filter_seqr_frequency(entries, **frequencies[self.callset_filter_field])
        return entries

    def _join_annotations(self, entries):
        return self._annotate_seqr_pop_expression(entries)

    def result_values(self, sample_data=None):
        entries = self._join_annotations(self)
        return self._search_call_data(entries, sample_data)

    def _filter_project_families(self, entries, sample_data):
       project_guids = sample_data['project_guids']
       project_filter = Q(project_guid__in=project_guids) if len(project_guids) > 1 else Q(project_guid=project_guids[0])
       entries = entries.filter(project_filter)

       multi_sample_type_families = sample_data['sample_type_families'].get('multi', [])
       family_q = None
       if multi_sample_type_families:
           family_q = Q(family_guid__in=multi_sample_type_families)
       for sample_type, families in sample_data['sample_type_families'].items():
           if sample_type == 'multi':
               continue
           sample_family_q = self._sample_family_q(sample_type, families)
           if family_q:
               family_q |= sample_family_q
           else:
               family_q = sample_family_q

       return entries.filter(family_q), multi_sample_type_families

    @classmethod
    def _sample_family_q(cls, sample_type, families):
        return Q(family_guid__in=families)

    def _search_call_data(self, entries, sample_data, inheritance_mode=None, inheritance_filter=None, qualityFilter=None, pathogenicity=None, exclude_projects=None, annotate_carriers=False, annotate_hom_alts=False, **kwargs):
       multi_sample_type_families = None
       if sample_data:
           entries, multi_sample_type_families = self._filter_project_families(entries, sample_data)
       elif exclude_projects:
           entries = entries.exclude(project_guid__in=exclude_projects)

       inheritance_q = None
       quality_q = None
       gt_filter = None
       quality_filter = qualityFilter or {}
       if not inheritance_mode and list((inheritance_filter or {}).keys()) == ['affected']:
           raise InvalidSearchException('Inheritance must be specified if custom affected status is set')
       if inheritance_mode or (inheritance_filter or {}).get('genotype') or quality_filter:
            clinvar_override_q = self._clinvar_path_q(pathogenicity)
            inheritance_q, quality_q, gt_filter, carriers_expression = self._get_inheritance_quality_qs(
               sample_data, inheritance_mode, quality_filter, clinvar_override_q,
                annotate_carriers, inheritance_filter=inheritance_filter or {},
            )
            if quality_filter.get('vcf_filter'):
                q = Q(filters__len=0)
                if clinvar_override_q:
                    q |= clinvar_override_q
                entries = entries.filter(q)
            if carriers_expression is not None:
                entries = entries.annotate(carriers=carriers_expression)

       if multi_sample_type_families:
           entries, inheritance_q, quality_q = self._get_multi_sample_type_family_call_qs(
               entries, multi_sample_type_families, inheritance_q, quality_q, gt_filter, sample_data['family_missing_type_samples'],
           )

       if inheritance_q is not None:
           entries = entries.filter(inheritance_q)
       if quality_q is not None:
           entries = entries.filter(quality_q)

       return self._annotate_calls(entries, sample_data, annotate_hom_alts, multi_sample_type_families, **kwargs)

    def _single_family_affected_filters(self, sample_data, inheritance_mode, inheritance_filter, genotype_lookup):
        samples_by_genotype = defaultdict(list)
        affected_samples = []
        unaffected_samples = []
        custom_affected = inheritance_filter.get('affected') or {}
        individual_genotype_filter = inheritance_filter.get('genotype')
        for sample in sample_data['samples']:
            affected = custom_affected.get(sample['individual_guid']) or sample['affected']
            if affected == AFFECTED:
                affected_samples.append(sample['sample_id'])
            if affected == UNAFFECTED:
                unaffected_samples.append(sample['sample_id'])

            if individual_genotype_filter:
                genotype = individual_genotype_filter.get(sample['individual_guid'])
                samples_by_genotype[genotype].append(sample['sample_id'])
            elif inheritance_mode and inheritance_mode != ANY_AFFECTED:
                genotype = self.INHERITANCE_FILTERS.get(inheritance_mode, {}).get(affected)
                if inheritance_mode in {X_LINKED_RECESSIVE, X_LINKED_RECESSIVE_MALE_AFFECTED} and sample['sex'] in MALE_SEXES:
                    if affected == UNAFFECTED:
                        genotype = REF_REF
                    elif affected == AFFECTED:
                        genotype = REF_ALT
                samples_by_genotype[genotype].append(sample['sample_id'])

        gt_filter = None
        if samples_by_genotype:
            if all(len(genotype_lookup[genotype]) == 1 for genotype in samples_by_genotype.keys()):
                samples_by_gt = {genotype_lookup[genotype][0]: samples for genotype, samples in samples_by_genotype.items()}
                gt_filter_map = ', '.join([f"{gt}, {samples_by_gt.get(gt, [])}" for gt in [-1, 0, 1, 2]])
                gt_filter = (gt_filter_map, 'has(map({value})[ifNull({field}, -1)], x.sampleId)')
            else:
                genotype_sample_map = ', '.join([f"'{genotype or 'any'}', {samples}" for genotype, samples in samples_by_genotype.items()])
                gt_genotypes = defaultdict(list)
                for genotype in samples_by_genotype.keys():
                    for gt in genotype_lookup[genotype]:
                        gt_genotypes[gt].append(genotype or 'any')
                gt_genotype_map = ', '.join([f"{gt}, {gt_genotypes[gt]}" for gt in [-1, 0, 1, 2]])
                genotype_maps = f'genotype -> map({genotype_sample_map})[genotype], map({gt_genotype_map})'
                gt_filter = (genotype_maps, 'has(arrayFlatten(arrayMap({value}[ifNull({field}, -1)])), x.sampleId)')

        affected_condition = (affected_samples, 'has({value}, {field})')
        unaffected_condition = (unaffected_samples, 'has({value}, {field})') if unaffected_samples else None

        return affected_condition, unaffected_condition, gt_filter

    @staticmethod
    def _affected_dict_get(sample_id_expression):
        return AffectedDict.dict_get_sql(key=f'(family_guid, {sample_id_expression})', fields=['affected'], default='U')

    def _multi_family_affected_filters(self, sample_data, inheritance_mode, inheritance_filter, genotype_lookup):
        sample_data = sample_data or {'num_unaffected': 1}
        any_unaffected = any(sample['affected'] == UNAFFECTED for sample in sample_data['samples']) \
            if sample_data.get('samples') else sample_data['num_unaffected'] > 0
        unaffected_condition = (None, self._affected_dict_get('{field}') + " = 'N'") if any_unaffected else None

        gt_filter = None
        if inheritance_mode and inheritance_mode != ANY_AFFECTED:
            inheritance_mode_filters = self.INHERITANCE_FILTERS.get(inheritance_mode, {})
            affected_gts = genotype_lookup.get(inheritance_mode_filters.get(AFFECTED), [])
            unaffected_gts = genotype_lookup.get(inheritance_mode_filters.get(UNAFFECTED), [])
            gt_map = f"map('A', {affected_gts}, 'N', {unaffected_gts}, 'U', [-1, 0, 1, 2])"
            affected_lookup = self._affected_dict_get('x.sampleId')
            if inheritance_mode == X_LINKED_RECESSIVE_MALE_AFFECTED:
                male_unaffected_gts = [gt for gt in unaffected_gts if gt < 1]
                male_gt_map = f"map('A', {affected_gts}, 'N', {male_unaffected_gts}, 'U', [-1, 0, 1, 2])"
                sex_map = [
                    f"'{sex}', {gt_map}" for sex in FEMALE_SEXES + [UNAFFECTED]
                ] + [f"'{sex}', {male_gt_map}" for sex in MALE_SEXES]
                sex_sql = SexDict.dict_get_sql(key='(family_guid, x.sampleId)', fields=['sex'], default='U')
                gt_map = f"map({', '.join(sex_map)})[{sex_sql}]"
            gt_filter = (gt_map, f'has({{value}}[{affected_lookup}], ifNull({{field}}, -1))')

        return self._affected_condition(), unaffected_condition, gt_filter

    def _affected_condition(self):
        return tuple([None, self._affected_dict_get('{field}') + " = 'A'"])

    def _get_inheritance_quality_qs(self, sample_data, inheritance_mode, quality_filter, clinvar_override_q, annotate_carriers, inheritance_filter):
        allow_no_call = inheritance_filter.get('allowNoCall')
        genotype_lookup = self.genotype_lookup
        if allow_no_call and inheritance_mode:
            unaffected_genotype = self.INHERITANCE_FILTERS.get(inheritance_mode, {}).get(UNAFFECTED)
            if unaffected_genotype and -1 not in genotype_lookup[unaffected_genotype]:
                genotype_lookup = {**genotype_lookup, unaffected_genotype: [-1] + genotype_lookup[unaffected_genotype]}
            if inheritance_mode in {X_LINKED_RECESSIVE, X_LINKED_RECESSIVE_MALE_AFFECTED} and -1 not in genotype_lookup[REF_REF]:
                genotype_lookup = {**genotype_lookup, REF_REF: [-1] + genotype_lookup[REF_REF]}

        is_single_family = (sample_data or {}).get('samples') and (sample_data['num_families'] == 1 or (inheritance_mode in {X_LINKED_RECESSIVE, X_LINKED_RECESSIVE_MALE_AFFECTED}))
        get_conditions = self._single_family_affected_filters if is_single_family else self._multi_family_affected_filters
        affected_condition, unaffected_condition, gt_filter = get_conditions(
            sample_data, inheritance_mode, inheritance_filter, genotype_lookup,
        )

        inheritance_q = None
        if inheritance_mode == ANY_AFFECTED:
            inheritance_q = self.any_affected_q(affected_condition)
        elif gt_filter:
            inheritance_q = Q(calls__array_all={'gt': gt_filter})
            if not sample_data:
                inheritance_q &= Q(calls__array_exists={'sampleId': affected_condition})

        quality_q = self._quality_q(quality_filter, allow_no_call, affected_condition, clinvar_override_q)

        carriers_expression = self._carriers_expression(unaffected_condition) if annotate_carriers and unaffected_condition else None

        return inheritance_q, quality_q, gt_filter, carriers_expression

    def any_affected_q(self, affected_condition=None):
        if affected_condition is None:
            affected_condition = self._affected_condition()
        return Q(calls__array_exists={
            'gt': (self.genotype_lookup[HAS_ALT], 'has({value}, {field})'),
            'sampleId': affected_condition,
        })

    def _quality_q(self, quality_filter, allow_no_call, affected_condition, clinvar_override_q):
        quality_filter_conditions = {}

        for field, config in self.QUALITY_FILTERS.items():
            if field not in self.call_fields:
                continue
            value = quality_filter.get(config.get('filter_key', f'min_{field}'))
            if value:
                or_filters = ['isNull({field})', '{field} >= {value}'] + config.get('filters', [])
                if allow_no_call:
                    or_filters.append('isNull(x.gt)')
                quality_filter_conditions[field] = (value / config.get('scale', 1), f'or({", ".join(or_filters)})')

        if not quality_filter_conditions:
            return None

        affected_only = quality_filter.get('affected_only')
        if affected_only:
            quality_filter_conditions = {'OR': [
                quality_filter_conditions,
                {'sampleId': (affected_condition[0], f'not({affected_condition[1]})')}
            ]}

        quality_q = Q(calls__array_all=quality_filter_conditions)
        if clinvar_override_q:
            quality_q |= clinvar_override_q

        return quality_q

    def _get_multi_sample_type_family_call_qs(self, entries, multi_sample_type_families, inheritance_q, quality_q, gt_filter, family_missing_type_samples):
        multi_sample_type_family_q = Q(family_guid__in=multi_sample_type_families)
        if gt_filter:
            inheritance_q |= multi_sample_type_family_q
            entries = self._annotate_failed_family_samples(entries, gt_filter, family_missing_type_samples)
        elif inheritance_q is not None:
            entries = entries.annotate(passes_inheritance=inheritance_q)
            inheritance_q = Q(passes_inheritance=True) | multi_sample_type_family_q
        else:
            entries = entries.annotate(passes_inheritance=Value(True))

        if quality_q is None:
            entries = entries.annotate(passes_quality=Value(True))
        else:
            entries = entries.annotate(passes_quality=quality_q)
            quality_q = Q(passes_quality=True) | multi_sample_type_family_q

        return entries, inheritance_q, quality_q

    @staticmethod
    def _annotate_failed_family_samples(entries, gt_filter, family_missing_type_samples):
        entries = entries.annotate(failed_family_samples= ArrayMap(
            ArrayFilter('calls', conditions=[{
                'gt': (gt_filter[0], f'not {gt_filter[1]}'),
            }]),
            mapped_expression='tuple(family_guid, x.sampleId)',
        ))
        if family_missing_type_samples:
            missing_sample_map = []
            for family_guid, sample_types in family_missing_type_samples.items():
                samples = [f"'{sample_type}', {samples}" for sample_type, samples in sample_types.items()]
                missing_sample_map.append(f"'{family_guid}', map({', '.join(samples)})")
            entries = entries.annotate(
                missing_family_samples=ArrayMap(
                    MapLookup('family_guid', Cast('sample_type', models.StringField()), map_values=', '.join(missing_sample_map)),
                    mapped_expression='tuple(family_guid, x)',
                )
            )
        return entries

    @classmethod
    def annotation_fields(cls, entries):
        fields = ['key']
        if 'seqrPop' in entries.query.annotations:
            fields.append('seqrPop')
        return fields

    def _annotate_calls(self, entries, sample_data=None, annotate_hom_alts=False, multi_sample_type_families=None, skip_entry_fields=False, override_annotations=None, **kwargs):
        if annotate_hom_alts:
            entries = entries.annotate(has_hom_alt=Q(calls__array_exists={'gt': (2,)}))

        fields = self.annotation_fields(entries)

        if multi_sample_type_families or sample_data is None or sample_data['num_families'] > 1:
            entries = entries.values(*fields)
            if skip_entry_fields:
                entries = entries.annotate(numFamilies=Count('family_guid'))
            else:
                gt_field, gt_expression = self.genotype_expression(sample_data)
                entries = entries.annotate(
                    familyGuids=ArraySort(ArrayDistinct(GroupArray('family_guid'))),
                    **{gt_field: GroupArrayArray(gt_expression)},
                    **{col: GroupArrayArray(col) for col in (override_annotations or [])}
                )
            if 'carriers' in entries.query.annotations:
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
            if multi_sample_type_families:
                entries = self._multi_sample_type_filtered_entries(entries)
        else:
            if 'carriers' in entries.query.annotations:
                fields.append('carriers')
            if annotate_hom_alts:
                fields.append('has_hom_alt')
            gt_field, gt_expression = self.genotype_expression(sample_data)
            entries = entries.values(
                *fields,
                familyGuids=Array('family_guid'),
                **{gt_field: gt_expression},
            )

        return entries

    def genotype_expression(self, sample_data=None):
        family_samples = defaultdict(list)
        samples = (sample_data or {}).get('samples') or []
        for s in samples:
            family_samples[s['family_guid']].append(f"'{s['sample_id']}', '{s['individual_guid']}'")
        sample_map = [
            f"'{family_guid}', map({', '.join(samples)})" for family_guid, samples in family_samples.items()
        ]
        genotype_expressions = list(self.genotype_fields.keys())
        output_base_fields = list(self.genotype_fields.values())
        output_field_kwargs = {'group_by_key': 'familyGuid'}
        if samples:
            genotype_expressions.insert(0, f"map({', '.join(sample_map)})[family_guid][x.sampleId]")
            output_base_fields.insert(0, ('individualGuid', models.StringField()))
            output_field_kwargs = {'group_by_key': 'individualGuid', 'flatten_groups': True}
        return 'genotypes' if samples else 'familyGenotypes', ArrayFilter(
            ArrayMap(
                'calls',
                mapped_expression=f"tuple({', '.join(genotype_expressions)})",
                output_field=NestedField(output_base_fields, **output_field_kwargs)
            ),
            conditions=[{1: (None, 'notEmpty({field})')}]
        )

    def _carriers_expression(self, unaffected_condition):
        return ArrayMap(
            ArrayFilter('calls', conditions=[{
                'sampleId': unaffected_condition,
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

    def filter_locus(self, exclude_locations=False, require_gene_filter=False, intervals=None, genes=None, variant_ids=None, inheritance_mode=None, **kwargs):
        entries = self

        if variant_ids:
            entries = entries.filter_variant_ids(variant_ids)

        if inheritance_mode in {X_LINKED_RECESSIVE, X_LINKED_RECESSIVE_MALE_AFFECTED}:
            if self.filtered_chrom and self.filtered_chrom != 'X':
                raise InvalidDatasetTypeException
            entries = entries.filter(self._interval_query('X', start=MIN_POS, end=MAX_POS))

        if intervals and self.filtered_chrom:
            intervals = [interval for interval in intervals if interval['chrom'] == self.filtered_chrom]
            if not intervals and not exclude_locations:
                raise InvalidDatasetTypeException

        if genes or intervals:
            entries = self._filter_locations(entries, genes, intervals, exclude_locations=exclude_locations, require_gene_filter=require_gene_filter)

        return entries

    @staticmethod
    def _parse_variant_ids(raw_variant_items):
        parsed_variant_ids = {}
        for item in (raw_variant_items or '').replace(',', ' ').split():
            variant_id = item.replace('chr', '')
            parsed_variant_ids[variant_id] = parse_variant_id(variant_id)
        return parsed_variant_ids

    def _filter_locations(self, entries, genes, intervals, exclude_locations=False, require_gene_filter=False):
        locus_q = None
        if genes:
            should_filter_interval = self._can_filter_gene_interval(genes) or exclude_locations
            if should_filter_interval:
                intervals = self._format_gene_intervals(genes) + (intervals or [])
            if require_gene_filter or (not should_filter_interval):
                locus_q = Q(geneId_ids__bitmap_has_any=[gene['id'] for gene in genes.values()])

        if intervals:
            interval_q = self._interval_query(**intervals[0])
            for interval in intervals[1:]:
                interval_q |= self._interval_query(**interval)
            if locus_q is None:
                locus_q = interval_q
            elif require_gene_filter:
                locus_q &= interval_q
            else:
                locus_q |= interval_q

        filter_func = entries.exclude if exclude_locations else entries.filter
        return filter_func(locus_q)

    def _can_filter_gene_interval(self, genes):
        return (not hasattr(self.model, 'geneId_ids')) or len(genes) < self.MAX_XPOS_FILTER_INTERVALS or self.filtered_chrom

    def search_padded_interval(self, chrom, pos, padding):
        interval_q = self._interval_query(chrom, start=max(pos - padding, MIN_POS), end=min(pos + padding, MAX_POS))
        return self.filter(interval_q).result_values()

    @staticmethod
    def _interval_query(chrom, start, end, **kwargs):
        return Q(xpos__range=(get_xpos(chrom, start), get_xpos(chrom, end)))

    def _filter_seqr_frequency(self, entries, ac=None, hh=None, **kwargs):
        entries = self._filter_seqr_freq_field(entries, self.gt_stats_dict.SEQR_POPULATIONS[0][1], ac)
        return entries._filter_seqr_freq_field(entries, 'hom', hh)

    def _filter_seqr_freq_field(self, entries, freq_field, value):
        if value is None:
            return entries
        field_names = [
            field_name for field_name, _ in self.gt_stats_dict.base_fields()
            if field_name.startswith(freq_field) and not field_name.endswith('affected')
        ]
        if not field_names:
            return entries
        expression = self.gt_stats_dict.dict_get_expression('key', field_names=field_names)
        if len(field_names) > 1:
            expression = Plus(Untuple(expression))
        entries = entries.annotate(**{freq_field: expression})
        return entries.filter(**{f'{freq_field}__lte': value})


class EntriesManager(BaseEntriesManager):
    MIN_MULTI_FAMILY_SEQR_AC = 5000

    @staticmethod
    def _clinvar_range_q(path_range):
        return Q(clinvar_join__pathogenicity__range=path_range)

    @staticmethod
    def _clinvar_star_q(min_stars):
        return Q(clinvar_join__gold_stars__gte=min_stars)

    @staticmethod
    def _clinvar_conflicting_path_filter(array_func, conflicting_filter):
        return {
            f'clinvar_join__conflicting_pathogenicities__{array_func}': conflicting_filter,
            'clinvar_join__conflicting_pathogenicities__not_empty': True,
        }

    @classmethod
    def _sample_family_q(cls, sample_type, families):
        sample_family_q = super()._sample_family_q(sample_type, families)
        return sample_family_q & Q(sample_type=sample_type)

    def _prefilter_entries(self, entries, freqs=None, **kwargs):
        entries = super()._prefilter_entries(entries, freqs=freqs, **kwargs)
        entries = self._filter_in_silico(entries, **kwargs)
        return entries

    def _filter_frequency(self, entries, frequencies, pathogenicity=None, sample_data=None, **kwargs):
        callset_filter = frequencies.get(self.callset_filter_field) or {}
        if (not callset_filter.get('ac') or callset_filter['ac'] >= self.MIN_MULTI_FAMILY_SEQR_AC) and (
            len(sample_data['sample_type_families']) > 1 or len(next(iter(sample_data['sample_type_families'].values()))) > 1
        ):
            raise InvalidSearchException(
                f'seqr AC frequency of at least {self.MIN_MULTI_FAMILY_SEQR_AC} must be specified to search across multiple families'
            )

        gnomad_filter = frequencies.get('gnomad_genomes') or {}
        if hasattr(self.model, 'is_gnomad_gt_5_percent') and (
            (gnomad_filter.get('af') or 1) <= 0.05 or any(gnomad_filter.get(field) is not None for field in ['ac', 'hh'])
        ):
            # Passing field=Value(False) to the django filter causes the SQL to evaluate to "field = false",
            # while passing field=False evaluates to "NOT field".
            # For fields used for pruning the table based on the order_by for the table, the former is needed
            entries = entries.filter(is_gnomad_gt_5_percent=Value(False))

        clinvar_override_q = self._clinvar_path_q(pathogenicity)

        for population in self.model.POPULATIONS:
            pop_filter = frequencies.get(population)
            if not pop_filter:
                continue

            pop_dict = getattr(self.model, population).rel.related_model
            pop_subfields = dict(pop_dict.base_fields())
            if pop_filter.get('af') is not None and pop_filter['af'] < 1:
                af_field = next(field for field in ['filter_af', 'af'] if field in pop_subfields)
                entries = entries.annotate(
                    **{f'{population}_af': pop_dict.dict_get_expression('key', field_names=[af_field])}
                )
                af_q = Q(**{f'{population}_af__lte': pop_filter['af']})
                if clinvar_override_q and pop_filter['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    af_q |= (clinvar_override_q & Q(**{f'{population}_af__lte': PATH_FREQ_OVERRIDE_CUTOFF}))
                entries = entries.filter(af_q)
            elif pop_filter.get('ac') is not None:
                entries = entries.annotate(
                    **{f'{population}_ac': pop_dict.dict_get_expression('key', field_names=['ac'])}
                )
                entries = entries.filter(**{f'{population}_ac__lte': pop_filter['ac']})

            if pop_filter.get('hh') is not None:
                for subfield in ['hom', 'hemi']:
                    if subfield not in pop_subfields:
                        continue
                    entries = entries.annotate(
                        **{f'{population}_{subfield}': pop_dict.dict_get_expression('key', field_names=[subfield])}
                    )
                    hh_q = Q(**{f'{population}_{subfield}__lte': pop_filter['hh']})
                    if clinvar_override_q:
                        hh_q |= clinvar_override_q
                    entries = entries.filter(hh_q)

        return super()._filter_frequency(entries, frequencies, **kwargs)

    def _parse_in_silico_qs(self, results, in_silico, require_score, in_silico_qs, in_silico_missing_qs):
        prediction_dicts = {pred: getattr(self.model, pred).rel.related_model for pred in self.model.PREDICTIONS}
        for score, value in in_silico.items():
            if not value:
                continue
            if score in self.model.RANGE_PREDICTIONS:
                score_expr = self._xpos_range_dict_get_expression(self.model.RANGE_PREDICTIONS[score], 'score')
            elif score in prediction_dicts:
                score_expr = prediction_dicts[score].dict_get_expression('key', field_names=['score'], null_missing=True)
            else:
                dict_model = next((dm for dm in prediction_dicts.values() if score in dict(dm.base_fields())), None)
                score_expr = dict_model.dict_get_expression(
                    'key', field_names=[score], null_missing=True,
                ) if dict_model else None
            if not score_expr:
                continue

            results = results.annotate(**{f'{score}_score': score_expr})
            try:
                score_q = Q(**{f'{score}_score__gte': float(value)})
            except ValueError:
                score_q = Q(**{f'{score}_score': value})

            in_silico_qs.append(score_q)
            if not require_score:
                in_silico_missing_qs.append(Q(**{f'{score}_score__isnull': True}))

        results, has_required_filter, in_silico_q, missing_q = super()._parse_in_silico_qs(
            results, in_silico, require_score, in_silico_qs, in_silico_missing_qs,
        )

        has_alphamissense = 'alphamissense' in (in_silico or {}) and 'alphamissensePathogenicity' in set(dict(
            getattr(self.annotations_model, 'SORTED_TRANSCRIPT_CONSQUENCES_FIELDS', [])
        ))
        if has_alphamissense:
            return results.annotate(
                pass_in_silico=in_silico_q or Value(False),
                missing_in_silico=missing_q or Value(True),
            ), False, None, None

        return results, has_required_filter, in_silico_q, missing_q

    def _join_annotations(self, entries):
        entries = entries.annotate(
            clinvar_key=F('clinvar_join__key'),
            clinvar=self._pathogenicity_tuple(self.model.clinvar_join, 'clinvar_join'),
            preds=self._prediction_expression(self.model),
            pops=self._population_expression(self.model),
        )
        if hasattr(self.model, 'mitomap'):
            entries = entries.annotate(
                mitomapPathogenic=self.model.mitomap.rel.related_model.dict_get_expression('key', null_missing=True),
            )
        return super()._join_annotations(entries)

    def filter_locus(self, *args, require_any_gene=False, rawVariantItems=None, intervals=None, genes=None, variant_ids=None, **kwargs):
        if rawVariantItems:
            parsed_variant_ids = self._parse_variant_ids(rawVariantItems)
            invalid_items = [variant_id for variant_id, parsed_id in parsed_variant_ids.items() if not parsed_id]
            if invalid_items:
                if variant_ids:
                    raise InvalidDatasetTypeException
                raise InvalidSearchException('Invalid variants: {}'.format(', '.join(invalid_items)))
            # although technically redundant, the interval query is applied to the entries table to
            # improve performance by using the xpos projection
            intervals = [{'chrom': chrom, 'start': pos, 'end': pos} for chrom, pos, _, _ in parsed_variant_ids.values()]
            variant_ids = parsed_variant_ids.keys()

        entries = super().filter_locus(*args, intervals=intervals, genes=genes, variant_ids=variant_ids, **kwargs)

        if hasattr(self.model, 'is_annotated_in_any_gene') and (require_any_gene or (genes and not intervals)):
            entries = entries.filter(is_annotated_in_any_gene=Value(True))

        return entries

    @classmethod
    def annotation_fields(cls, entries):
        return super().annotation_fields(entries) + ['clinvar', 'clinvar_key', 'preds', 'pops', 'xpos'] + [
            field for field in ['pass_in_silico', 'missing_in_silico','mitomapPathogenic'] if field in entries.query.annotations
        ]

class SvEntriesManager(BaseEntriesManager):
    NULLABLE_GENOTYPE_LOOKUP = {
        **BaseEntriesManager.GENOTYPE_LOOKUP,
        BaseEntriesManager.COMP_HET_ALT: BaseEntriesManager.GENOTYPE_LOOKUP[HAS_ALT],
        REF_REF: [-1] + BaseEntriesManager.GENOTYPE_LOOKUP[REF_REF],
        HAS_REF: [-1] + BaseEntriesManager.GENOTYPE_LOOKUP[HAS_REF],
    }

    QUALITY_FILTERS = {
        'gq': {'filter_key': 'min_gq_sv'},
        'qs': {},
    }

    @property
    def genotype_lookup(self):
        return self.NULLABLE_GENOTYPE_LOOKUP if self.annotations_model.GENOTYPE_OVERRIDE_FIELDS else self.GENOTYPE_LOOKUP

    @property
    def callset_filter_field(self):
        return 'sv_callset'

    @property
    def sample_type_expression(self):
        return f"'{self.model.SAMPLE_TYPE}'"

    @classmethod
    def _clinvar_path_q(cls, pathogenicity):
        return None

    def _prefilter_entries(self, entries, annotations=None, **kwargs):
        entries = super()._prefilter_entries(entries, **kwargs)

        if (annotations or {}).get(NEW_SV_FIELD):
            entries = entries.filter(calls__array_exists={'newCall': (None, '{field}')})

        return entries

    def _annotate_calls(self, entries, *args, **kwargs):
        genotype_override_annotations = {
            f'sample_{col}': ArrayMap(
                ArrayFilter('calls', conditions=[{'cn': (None, 'isNotNull({field})')}]),
                mapped_expression=f'x.{field}',
            ) for col, (field, _) in self.annotations_model.GENOTYPE_OVERRIDE_FIELDS.items()
        }
        if genotype_override_annotations:
            entries = entries.annotate(**genotype_override_annotations)

        entries = super()._annotate_calls(entries, *args, override_annotations=genotype_override_annotations.keys(), **kwargs)

        if genotype_override_annotations:
            entries = entries.annotate(**{
                f'sample_{col}': agg(f'sample_{col}', output_field=self.call_fields[field])
                for col, (field, agg) in self.annotations_model.GENOTYPE_OVERRIDE_FIELDS.items()
            })

        return entries

    def filter_locus(self, *args, exclude_locations=False, intervals=None, genes=None, exclude_svs=False, rawVariantItems=None, **kwargs):
        if exclude_svs or any(self._parse_variant_ids(rawVariantItems).values()):
            raise InvalidDatasetTypeException
        # SV interval filtering occurs after joining on annotations to correctly incorporate end position
        can_filter_gene_interval = self._can_filter_gene_interval(genes)
        if exclude_locations:
            intervals = None
        else:
            chromosomes = {i['chrom'] for i in (intervals or [])}
            if can_filter_gene_interval:
                chromosomes.update({gene[f'chromGrch{self.genome_version}'] for gene in genes.values()})
            intervals = [{'chrom': chrom, 'start': MIN_POS, 'end': MAX_POS} for chrom in chromosomes]

        entries = super().filter_locus(
            *args, exclude_locations=exclude_locations, intervals=intervals, genes=genes, **kwargs,
        )

        if can_filter_gene_interval and not exclude_locations:
            entries = entries.filter(calls__array_all={'OR': [
                {'geneIds': (list(genes.keys()), 'hasAny({value}, {field})')},
                {'gt': (None, 'isNull({field})')},
            ]})

        return entries

    def _can_filter_gene_interval(self, genes):
        return genes and 'geneIds' in self.call_fields
