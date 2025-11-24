from collections import defaultdict
from datetime import datetime
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, F
from django.db.models.functions import JSONObject

from clickhouse_backend.models import ArrayField, StringField

from clickhouse_search.backend.fields import NamedTupleField
from clickhouse_search.backend.functions import ArrayFilter, ArrayMap
from clickhouse_search.search import get_search_queryset, get_transcripts_queryset, clickhouse_genotypes_json, \
    get_data_type_comp_het_results_queryset, get_multi_data_type_comp_het_results_queryset, SAMPLE_DATA_FIELDS, SELECTED_GENE_FIELD
from panelapp.models import PaLocusListGene
from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Project, Family, Individual, Sample, LocusList
from seqr.utils.communication_utils import send_project_notification
from seqr.utils.gene_utils import get_genes
from seqr.utils.search.utils import clickhouse_only, get_search_samples, COMPOUND_HET
from seqr.views.utils.orm_to_json_utils import SEQR_TAG_TYPE
from seqr.views.utils.variant_utils import bulk_create_tagged_variants, gene_ids_annotated_queryset
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

import logging
logger = logging.getLogger(__name__)


GENE_LISTS = [
    {'name': 'Mendeliome', 'confidences': ['AMBER', 'GREEN']},
    {'name': 'Incidentalome', 'confidences': ['GREEN']}
]

EXCLUDE_GENE_IDS = [
    'ENSG00000143631', 'ENSG00000165474', 'ENSG00000180210', 'ENSG00000198734', 'ENSG00000010704', 'ENSG00000132470',
]

ALL_SEARCHES_CRITERIA = {
    'exclude': {'clinvar': ['likely_benign', 'benign']}
}

SEARCHES = {
    'SNV_INDEL': {
        'Clinvar Pathogenic': {
            'gene_list_moi': 'D',
            'inheritance_mode': 'any_affected',
            'pathogenicity': {
                'clinvar': ['pathogenic', 'likely_pathogenic', 'conflicting_p_lp'],
                'clinvarMinStars': 1,
            },
            'freqs': {
                'callset': {'ac': 100},
                'gnomad_exomes': {'ac': 100},
                'gnomad_genomes': {'ac': 100},
            }
        },
        'Clinvar Pathogenic -  Compound Heterozygous': {
            'gene_list_moi': 'R',
            'inheritance_mode': 'compound_het',
            'no_secondary_annotations': True,
            'pathogenicity': {
                'clinvar': ['pathogenic', 'likely_pathogenic', 'conflicting_p_lp'],
                'clinvarMinStars': 1,
            },
            'annotations': {
                'vep_consequences': [
                    'splice_donor_variant',
                    'splice_acceptor_variant',
                    'stop_gained',
                    'frameshift_variant',
                    'stop_lost',
                    'start_lost',
                    'inframe_insertion',
                    'inframe_deletion',
                    'protein_altering_variant',
                    'missense_variant',
                    'splice_donor_5th_base_variant',
                    'splice_region_variant',
                    'splice_donor_region_variant',
                    'splice_polypyrimidine_tract_variant',
                    'extended_intronic_splice_region_variant',
                    'non_coding_transcript_exon_variant',
                ]
            },
            'freqs': {
                'callset': {'ac': 2000},
                'gnomad_exomes': {'af': 0.03},
                'gnomad_genomes': {'af': 0.03}
            },
            'qualityFilter': {
                'min_gq': 30,
                'min_ab': 20
            },
        },
        'Clinvar Pathogenic - Recessive': {
            'gene_list_moi': 'R',
            'inheritance_mode': 'homozygous_recessive',
            'pathogenicity': {
                'clinvar': ['pathogenic', 'likely_pathogenic', 'conflicting_p_lp'],
                'clinvarMinStars': 1,
            },
            'freqs': {
                'callset': {'ac': 2000},
                'gnomad_exomes': {'af': 0.03},
                'gnomad_genomes': {'af': 0.03}
            },
        },
        'Compound Heterozygous': {
            'gene_list_moi': 'R',
            'inheritance_mode': 'compound_het',
            'annotations': {
                'vep_consequences': [
                    'splice_donor_variant',
                    'splice_acceptor_variant',
                    'stop_gained',
                    'frameshift_variant',
                    'non_coding_transcript_exon_variant',
                ],
            },
            'annotations_secondary': {
                'vep_consequences': [
                    'splice_donor_variant',
                    'splice_acceptor_variant',
                    'stop_gained',
                    'frameshift_variant',
                    'stop_lost',
                    'start_lost',
                    'inframe_insertion',
                    'inframe_deletion',
                    'protein_altering_variant',
                    'missense_variant',
                    'splice_donor_5th_base_variant',
                    'splice_region_variant',
                    'splice_donor_region_variant',
                    'splice_polypyrimidine_tract_variant',
                    'extended_intronic_splice_region_variant',
                    'non_coding_transcript_exon_variant',
                ],
            },
            'in_silico': {
                'cadd': 25,
                'revel': 0.6
            },
            'freqs': {
                'callset': {'ac': 1000},
                'gnomad_exomes': {'af': 0.01, 'hh': 2},
                'gnomad_genomes': {'af': 0.01, 'hh': 2},
            },
            'qualityFilter': {
                'min_gq': 30,
                'min_ab': 20,
            },
        },
        'Compound Heterozygous - Confirmed': {
            'family_filter': {
                'max_affected': 1,
                'confirmed_inheritance': True
            },
            'gene_list_moi': 'R',
            'inheritance_mode': 'compound_het',
            'annotations': {
                'vep_consequences': [
                    'stop_lost',
                    'start_lost',
                    'inframe_insertion',
                    'inframe_deletion',
                    'protein_altering_variant',
                    'missense_variant',
                    'splice_donor_5th_base_variant',
                    'splice_region_variant',
                    'splice_donor_region_variant',
                    'splice_polypyrimidine_tract_variant',
                    'extended_intronic_splice_region_variant',
                ]
            },
            'in_silico': {
                'cadd': 25,
                'revel': 0.6,
            },
            'freqs': {
                'callset': {'ac': 1000},
                'gnomad_exomes': {'af': 0.01, 'hh': 2},
                'gnomad_genomes': {'af': 0.01, 'hh': 2},
            },
            'qualityFilter': {
                'min_gq': 30,
                'min_ab': 20,
            }
        },
        'De Novo': {
            'family_filter': {
              'max_affected': 1,
              'confirmed_inheritance': True
            },
            'inheritance_mode': 'de_novo',
            'annotations': {
                'vep_consequences': [
                    'splice_donor_variant',
                    'splice_acceptor_variant',
                    'stop_gained',
                    'frameshift_variant',
                    'stop_lost',
                    'start_lost',
                    'inframe_insertion',
                    'inframe_deletion',
                    'protein_altering_variant',
                    'missense_variant',
                    'splice_donor_5th_base_variant',
                    'splice_region_variant',
                    'splice_donor_region_variant',
                    'splice_polypyrimidine_tract_variant',
                    'extended_intronic_splice_region_variant',
                    'non_coding_transcript_exon_variant',
                ]
            },
            'require_any_gene': True,
            'in_silico': {
                'cadd': 25,
                'revel': 0.6,
            },
            'freqs': {
                'callset': {'ac': 100},
                'gnomad_exomes': {'ac': 100},
                'gnomad_genomes': {'ac': 100}
            },
            'qualityFilter': {
              'vcf_filter': 'PASS',
              'min_gq': 30,
              'min_ab': 20
            }
        },
        'De Novo/ Dominant': {
            'family_filter': {
                'max_affected': 1,
                'confirmed_inheritance': False
            },
            'gene_list_moi': 'D',
            'inheritance_mode': 'de_novo',
            'annotations': {
                'vep_consequences': [
                    'splice_donor_variant',
                    'splice_acceptor_variant',
                    'stop_gained',
                    'frameshift_variant',
                ],
            },
            'in_silico': {
                'cadd': 25,
                'revel': 0.6
            },
            'freqs': {
                'callset': {'ac': 100},
                'gnomad_exomes': {'ac': 100},
                'gnomad_genomes': {'ac': 100},
            },
            'qualityFilter': {
                'vcf_filter': 'PASS',
                'min_gq': 30,
                'min_ab': 20,
            }
        },
        'Dominant': {
            'family_filter': {
                'min_affected': 2
            },
            'gene_list_moi': 'D',
            'inheritance_mode': 'de_novo',
            'annotations': {
                'vep_consequences': [
                    'splice_donor_variant',
                    'splice_acceptor_variant',
                    'stop_gained',
                    'frameshift_variant',
                    'stop_lost',
                    'start_lost',
                    'inframe_insertion',
                    'inframe_deletion',
                    'protein_altering_variant',
                    'missense_variant',
                    'splice_donor_5th_base_variant',
                    'splice_region_variant',
                    'splice_donor_region_variant',
                    'splice_polypyrimidine_tract_variant',
                    'extended_intronic_splice_region_variant',
                    'non_coding_transcript_exon_variant',
                ],
            },
            'require_any_gene': True,
            'in_silico': {
                'cadd': 25,
                'revel': 0.6,
                'splice_ai': 0.5
            },
            'freqs': {
                'callset': {'ac': 100},
                'gnomad_exomes': {'ac': 100},
                'gnomad_genomes': {'ac': 100},
            },
            'qualityFilter': {
                'vcf_filter': 'PASS',
                'min_gq': 30,
                'min_ab': 20,
            }
        },
        'High Splice AI': {
            'gene_list_moi': 'D',
            'inheritance_mode': 'de_novo',
            'in_silico': {
                'splice_ai': 0.5,
                'requireScore': True
            },
            'freqs': {
                'callset': {'ac': 100},
                'gnomad_exomes': {'ac': 100},
                'gnomad_genomes': {'ac': 100}
            },
            'qualityFilter': {
                'vcf_filter': 'PASS',
                'min_gq': 30,
                'min_ab': 20,
            },
        },
        'Recessive': {
            'gene_list_moi': 'R',
            'inheritance_mode': 'homozygous_recessive',
            'annotations': {
                'vep_consequences': [
                    'splice_donor_variant',
                    'splice_acceptor_variant',
                    'stop_gained',
                    'frameshift_variant',
                    'stop_lost',
                    'start_lost',
                    'inframe_insertion',
                    'inframe_deletion',
                    'protein_altering_variant',
                    'missense_variant',
                    'splice_donor_5th_base_variant',
                    'splice_region_variant',
                    'splice_donor_region_variant',
                    'splice_polypyrimidine_tract_variant',
                    'extended_intronic_splice_region_variant',
                    'non_coding_transcript_exon_variant',
                ],
            },
            'in_silico': {
                'cadd': 25,
                'revel': 0.6
            },
            'freqs': {
                'callset': {'ac': 1000},
                'gnomad_exomes': {'af': 0.01, 'hh': 5},
                'gnomad_genomes': {'af': 0.01,'hh': 5},
            },
            'qualityFilter': {
                'min_gq': 30,
                'min_ab': 20,
            },
        },
    },
    'SV': {
        'SV - Compound Heterozygous': {
            'family_filter': {
                'confirmed_inheritance': True
            },
            'gene_list_moi': 'R',
            'inheritance_mode': 'compound_het',
            'annotations': {
                'structural_consequence': ['LOF', 'INTRAGENIC_EXON_DUP'],
            },
            'freqs': {
                'sv_callset': {'ac': 500},
                'gnomad_svs': {'ac': 0.01},
            },
            'qualityFilter': {
                'min_gq_sv': 90,
                'vcf_filter': 'PASS',
            },
        },
        'SV - De Novo/ Dominant': {
            'family_filter': {
                'confirmed_inheritance': True
            },
            'gene_list_moi': 'D',
            'inheritance_mode': 'de_novo',
            'annotations': {
                'structural_consequence': ['LOF', 'INTRAGENIC_EXON_DUP'],
            },
            'freqs': {
                'sv_callset': {'ac': 100},
                'gnomad_svs': {'ac': 0.001},
            },
            'qualityFilter': {
                'vcf_filter': 'PASS',
                'min_gq_sv': 90,
            }
        },
        'SV - Recessive': {
            'gene_list_moi': 'R',
            'inheritance_mode': 'homozygous_recessive',
            'annotations': {
              'structural_consequence': ['LOF', 'INTRAGENIC_EXON_DUP'],
            },
            'freqs': {
                'sv_callset': {'ac': 500},
                'gnomad_svs': {'ac': 0.01},
            },
            'qualityFilter': {
                'min_gq_sv': 90,
            }
        },
    },
}

MULTI_DATA_TYPE_SEARCHES = {
    'Compound Heterozygous - One SV': {
        'annotations': {
            'structural_consequence': [
                'LOF',
                'INTRAGENIC_EXON_DUP',
            ],
            'vep_consequences': [
                'stop_lost',
                'start_lost',
                'inframe_insertion',
                'inframe_deletion',
                'protein_altering_variant',
                'missense_variant',
                'splice_donor_5th_base_variant',
                'splice_region_variant',
                'splice_donor_region_variant',
                'splice_polypyrimidine_tract_variant',
                'extended_intronic_splice_region_variant',
            ],
        },
        'in_silico': {
            'cadd': 25,
            'revel': 0.6
        },
        'freqs': {
            'callset': {'ac': 1000},
            'sv_callset': {'ac': 500},
            'gnomad_exomes': {'af': 0.01, 'hh': 2},
            'gnomad_genomes': {'af': 0.01, 'hh': 2},
            'gnomad_svs': {'ac': 0.01}
        },
        'qualityFilter': {
            'min_gq_sv': 90,
            'min_gq': 30,
            'min_ab': 20,
            'vcf_filter': 'PASS',
        },
    },
}

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('project')

    @clickhouse_only
    def handle(self, *args, **options):
        family_guid_map = {}
        family_name_map = {}
        project = Project.objects.get(guid=options['project'])
        for db_id, guid, family_id in Family.objects.filter(project=project).values_list('id', 'guid', 'family_id'):
            family_guid_map[guid] = db_id
            family_name_map[db_id] = family_id

        exclude_genes = get_genes(EXCLUDE_GENE_IDS, genome_version=GENOME_VERSION_GRCh38)
        gene_by_moi = defaultdict(dict)
        for gene_list in GENE_LISTS:
            self._get_gene_list_genes(gene_list['name'], gene_list['confidences'], gene_by_moi, exclude_genes.keys())

        family_variant_data = defaultdict(lambda: {'matched_searches': set(), 'matched_comp_het_searches': set(), 'support_vars': set()})
        search_counts = {}
        samples_by_dataset_type = {}
        for dataset_type, searches in SEARCHES.items():
            self._run_dataset_type_searches(
                dataset_type, searches, family_variant_data, search_counts, samples_by_dataset_type, family_guid_map,
                project, exclude_genes, gene_by_moi,
            )

        self._run_multi_data_type_comp_het_search(
            family_variant_data, search_counts, samples_by_dataset_type, family_guid_map, project, genes=gene_by_moi['R'],
        )

        today = datetime.now().strftime('%Y-%m-%d')
        new_tag_keys, num_updated, num_skipped = bulk_create_tagged_variants(
            family_variant_data, tag_name=SEQR_TAG_TYPE, get_metadata=self._get_metadata(today, 'matched_searches'),
            get_comp_het_metadata=self._get_metadata(today, 'matched_comp_het_searches'), user=None, remove_missing_metadata=False,
        )

        family_variants = defaultdict(list)
        for family_id, variant_id in family_variant_data.keys():
            family_variants[family_id].append(variant_id)
        logger.info(f'Tagged {len(new_tag_keys)} new and {num_updated} previously tagged variants in {len(family_variants)} families, found {num_skipped} unchanged tags:')
        for search_name, count in search_counts.items():
            logger.info(f'  {search_name}: {count} variants')
        if not new_tag_keys:
            return

        family_new_counts = defaultdict(int)
        for family_id, variant_id in new_tag_keys:
            family_new_counts[family_id] += 1

        send_project_notification(
            project,
            notification=f'{len(new_tag_keys)} new seqr prioritized variants',
            subject='New prioritized variants tagged in seqr',
            email_template='This is to notify you that {notification} have been tagged in seqr project {project_link}',
            slack_channel=SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            slack_detail='\n'.join(sorted([
                f'{family_name_map[family_id]}: {count} new tags' for family_id, count in family_new_counts.items()
            ])),
        )

    @classmethod
    def _run_dataset_type_searches(cls, dataset_type, searches, family_variant_data, search_counts, samples_by_dataset_type, family_guid_map, project, exclude_genes, gene_by_moi):
        is_sv = dataset_type == Sample.DATASET_TYPE_SV_CALLS
        sample_qs = get_search_samples([project]).filter(dataset_type=dataset_type)
        if is_sv:
            sample_qs = sample_qs.exclude(individual__sv_flags__contains=['outlier_num._calls'])
        sample_types = list(sample_qs.values_list('sample_type', flat=True).distinct())
        if len(sample_types) > 1:
            raise CommandError('Variant prioritization not supported for projects with multiple sample types')
        sample_type = sample_types[0]
        if is_sv:
            dataset_type = f'{dataset_type}_{sample_type}'
        samples_by_family = {
            family_guid: samples for family_guid, samples in sample_qs.values('individual__family__guid').annotate(
                samples=ArrayAgg(JSONObject(**SAMPLE_DATA_FIELDS, maternal_guid='individual__mother__guid', paternal_guid='individual__father__guid'))
            ).values_list('individual__family__guid', 'samples')
            if any(s['affected'] == Individual.AFFECTED_STATUS_AFFECTED for s in samples)
        }
        samples_by_dataset_type[dataset_type] = samples_by_family

        logger.info(f'Searching for prioritized {dataset_type} variants in {len(samples_by_family)} families in project {project.name}')
        for search_name, config_search in searches.items():
            exclude_locations = not config_search.get('gene_list_moi')
            search_genes = exclude_genes if exclude_locations else gene_by_moi[config_search['gene_list_moi']]
            sample_data = cls._get_valid_family_sample_data(
                project, sample_type, samples_by_family, config_search.get('family_filter'),
            )
            run_search_func = cls._run_comp_het_search if config_search['inheritance_mode'] == COMPOUND_HET else cls._run_search
            num_results = run_search_func(
                search_name, config_search, family_variant_data, family_guid_map, dataset_type, sample_data,
                exclude_locations=exclude_locations, genes=search_genes, **config_search, **ALL_SEARCHES_CRITERIA,
            )
            logger.info(f'Found {num_results} variants for criteria: {search_name}')
            search_counts[search_name] = num_results

    @classmethod
    def _get_valid_family_sample_data(cls, project, sample_type, samples_by_family, family_filter=None):
        if family_filter:
            samples_by_family = {
                family_guid: samples for family_guid, samples in samples_by_family.items()
                if cls._family_passes_filter(samples, family_filter)
            }
        return {
            'project_guids': [project.guid],
            'family_guids': samples_by_family.keys(),
            'sample_type_families': {sample_type: samples_by_family.keys()},
            'samples': [s for family_samples in samples_by_family.values() for s in family_samples],
        }

    @staticmethod
    def _family_passes_filter(samples, family_filter):
        affected = [s for s in samples if s['affected'] == Individual.AFFECTED_STATUS_AFFECTED]
        if family_filter.get('min_affected') and len(affected) < family_filter['min_affected']:
            return False
        if family_filter.get('max_affected') and len(affected) > family_filter['max_affected']:
            return False
        if 'confirmed_inheritance' in family_filter:
            proband = next((s for s in affected if s['maternal_guid'] and s['paternal_guid']), None)
            if not proband:
                return False
            loaded_unaffected_guids = {s['individual_guid'] for s in samples if s['affected'] == Individual.AFFECTED_STATUS_UNAFFECTED}
            is_confirmed = proband['maternal_guid'] in loaded_unaffected_guids and proband['paternal_guid'] in loaded_unaffected_guids
            return (not is_confirmed) if family_filter['confirmed_inheritance'] == False else is_confirmed
        return True

    @staticmethod
    def _get_metadata(today, metadata_key):
        def wrapped(v):
            return {name: today for name in v[metadata_key]} if v[metadata_key] else None
        return wrapped

    @classmethod
    def _run_search(cls, search_name, config_search, family_variant_data, family_guid_map, dataset_type, sample_data, **kwargs):
        variant_fields = ['pos', 'end'] if dataset_type.startswith('SV') else ['ref', 'alt']
        variant_values = {'endChrom': F('end_chrom')} if dataset_type == 'SV_WGS' else {}

        results_qs = get_search_queryset(GENOME_VERSION_GRCh38, dataset_type, sample_data, **kwargs)
        genotype_overrides_expressions = results_qs.genotype_override_values(results_qs)
        if genotype_overrides_expressions:
            variant_values.update({k: genotype_overrides_expressions[k] for k in ['genotypes', 'transcripts']})
        else:
            results_qs = gene_ids_annotated_queryset(results_qs)
            variant_fields += ['genotypes', 'gene_ids']

        results = [
            {**variant, 'genotypes': clickhouse_genotypes_json(variant['genotypes'])}
            for variant in results_qs.values(
                *variant_fields, 'key', 'xpos', 'variant_id', 'familyGuids', **variant_values,
            )
        ]
        require_mane_consequences = config_search.get('annotations', {}).get('vep_consequences')
        if results and require_mane_consequences:
            allowed_key_genes = cls._valid_mane_keys([v['key'] for v in results], require_mane_consequences)
            results = [r for r in results if r['key'] in allowed_key_genes]

        for variant in results:
            for family_guid in variant.pop('familyGuids'):
                variant_data = family_variant_data[(family_guid_map[family_guid], variant['variant_id'])]
                variant_data.update(variant)
                variant_data['matched_searches'].add(search_name)

        return len(results)

    @classmethod
    def _run_comp_het_search(cls, search_name, config_search, family_variant_data, family_guid_map, dataset_type, sample_data, **kwargs):
        queryset = get_data_type_comp_het_results_queryset(
            GENOME_VERSION_GRCh38, dataset_type, sample_data, **kwargs,
        )
        return cls._execute_comp_het_search(
            queryset, search_name, config_search, family_variant_data, family_guid_map, config_search.get('no_secondary_annotations'),
        )

    @classmethod
    def _run_multi_data_type_comp_het_search(cls, family_variant_data, search_counts, samples_by_dataset_type, family_guid_map, project, genes):
        sv_dataset_type = next(dt for dt in samples_by_dataset_type.keys() if dt.startswith('SV'))
        sample_type = sv_dataset_type.split('_')[-1]
        families = set(samples_by_dataset_type[sv_dataset_type].keys()).intersection(samples_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS].keys())
        sv_sample_data = cls._get_valid_family_sample_data(project, sample_type, {
            guid: samples for guid, samples in samples_by_dataset_type[sv_dataset_type].items() if guid in families
        })
        snv_indel_sample_data = cls._get_valid_family_sample_data(project, sample_type, {
            guid: samples for guid, samples in samples_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS].items() if guid in families
        })
        logger.info(f'Searching for prioritized multi data type variants in {len(families)} families in project {project.name}')
        for search_name, config_search in MULTI_DATA_TYPE_SEARCHES.items():
            queryset = get_multi_data_type_comp_het_results_queryset(
                GENOME_VERSION_GRCh38, sv_dataset_type, sv_sample_data, snv_indel_sample_data, num_families=len(families),
                genes=genes, **config_search, **ALL_SEARCHES_CRITERIA,
            )
            num_results = cls._execute_comp_het_search(queryset, search_name, config_search, family_variant_data, family_guid_map)
            logger.info(f'Found {num_results} variants for criteria: {search_name}')
            search_counts[search_name] = num_results

    @classmethod
    def _execute_comp_het_search(cls, queryset, search_name, config_search, family_variant_data, family_guid_map, no_secondary_annotations=True):
        results = [v[1:] for v in queryset]

        primary_consequences = config_search.get('annotations', {}).get('vep_consequences')
        secondary_consequences = config_search.get('annotations_secondary', {}).get('vep_consequences')
        if results and (primary_consequences or secondary_consequences):
            keys = [v['key'] for pair in results for v in pair]
            allowed_key_genes = cls._valid_mane_keys(keys, primary_consequences)
            if secondary_consequences:
                allowed_secondary_key_genes = cls._valid_mane_keys(keys, secondary_consequences)
            else:
                allowed_secondary_key_genes = None if no_secondary_annotations else allowed_key_genes
            results = [
                pair for pair in results
                if pair[0][SELECTED_GENE_FIELD] in allowed_key_genes.get(pair[0]['key'], []) and (
                    allowed_secondary_key_genes is None or
                    pair[1][SELECTED_GENE_FIELD] in allowed_secondary_key_genes.get(pair[1]['key'], [])
                )
            ]

        for pair in results:
            for family_guid in pair[0]['familyGuids']:
                for variant, support_id in [(pair[0], pair[1]['variantId']), (pair[1], pair[0]['variantId'])]:
                    variant_data = family_variant_data[(family_guid_map[family_guid], variant['variantId'])]
                    variant_data.update(variant)
                    variant_data['genotypes'] = clickhouse_genotypes_json(variant['genotypes'])
                    if 'transcripts' not in variant_data:
                        variant_data['gene_ids'] = list(dict.fromkeys([csq['geneId'] for csq in variant['sortedTranscriptConsequences']]))
                    variant_data['support_vars'].add(support_id)
                    variant_data['matched_comp_het_searches'].add(search_name)

        return len(results)

    @staticmethod
    def _valid_mane_keys(keys, allowed_consequences):
        mane_transcripts_by_key = get_transcripts_queryset(GENOME_VERSION_GRCh38, keys).values_list(
            'key', ArrayMap(
                ArrayFilter('transcripts', conditions=[{'maneSelect': (None, 'isNotNull({field})')}]),
                mapped_expression='tuple(x.consequenceTerms, x.geneId)',
                output_field=ArrayField(NamedTupleField([('consequenceTerms', ArrayField(StringField())), ('geneId', StringField())])),
            )
        )
        mane_transcript_genes = {
            key: {t['geneId'] for t in mane_transcripts if set(allowed_consequences).intersection(t['consequenceTerms'])}
            for key, mane_transcripts in mane_transcripts_by_key
        }
        return {key: genes for key, genes in mane_transcript_genes.items() if genes}

    @staticmethod
    def _get_gene_list_genes(name, confidences, gene_by_moi, exclude_gene_ids):
        ll = LocusList.objects.get(name=name, palocuslist__isnull=False)
        moi_gene_ids = ll.locuslistgene_set.exclude(gene_id__in=exclude_gene_ids).annotate(
            is_dominant=Q(
                palocuslistgene__mode_of_inheritance__startswith='BOTH'
            ) | Q(
                palocuslistgene__mode_of_inheritance__startswith='X-LINKED',
                palocuslistgene__mode_of_inheritance__contains='monoallelic mutations',
            ) | Q(
                Q(palocuslistgene__mode_of_inheritance__startswith='MONOALLELIC') &
                ~Q(palocuslistgene__mode_of_inheritance__contains=' paternally imprinted') &
                ~Q(palocuslistgene__mode_of_inheritance__contains=' maternally imprinted')
            ),
            is_recessive=Q(
                palocuslistgene__mode_of_inheritance__startswith='BOTH'
            ) | Q(
                palocuslistgene__mode_of_inheritance__startswith='BIALLELIC'
            ) | Q(
                palocuslistgene__mode_of_inheritance__startswith='X-LINKED'
            ),
        ).filter(Q(is_dominant=True) | Q(is_recessive=True)).filter(palocuslistgene__confidence_level__in=[
            level for level, name in PaLocusListGene.CONFIDENCE_LEVEL_CHOICES if name in confidences
        ]).values('gene_id', 'is_dominant', 'is_recessive')

        dominant_gene_ids = [g['gene_id'] for g in moi_gene_ids if g['is_dominant']]
        recessive_gene_ids = [g['gene_id'] for g in moi_gene_ids if g['is_recessive']]
        genes_by_id = get_genes(dominant_gene_ids + recessive_gene_ids, genome_version=GENOME_VERSION_GRCh38, additional_model_fields=['id'])
        gene_by_moi['D'].update({gene_id: gene for gene_id, gene in genes_by_id.items() if gene_id in set(dominant_gene_ids)})
        gene_by_moi['R'].update({gene_id: gene for gene_id, gene in genes_by_id.items() if gene_id in set(recessive_gene_ids)})
