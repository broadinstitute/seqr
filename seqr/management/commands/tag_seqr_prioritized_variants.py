from collections import defaultdict
from datetime import datetime
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db.models.functions import JSONObject
import json

from clickhouse_search.search import get_clickhouse_variants, ENTRY_CLASS_MAP
from panelapp.models import PaLocusListGene
from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Project, Family, Individual, Dataset, LocusList
from seqr.utils.communication_utils import send_project_notification
from seqr.utils.gene_utils import get_genes
from clickhouse_search.constants import ANY_AFFECTED, HOMOZYGOUS_RECESSIVE, X_LINKED_RECESSIVE_MALE_AFFECTED, DE_NOVO, COMPOUND_HET
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets
from seqr.views.utils.orm_to_json_utils import SEQR_TAG_TYPE
from seqr.views.utils.variant_utils import bulk_create_tagged_variants, get_saved_variant_annotations
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
    'exclude': {'clinvar': ['likely_benign', 'benign']},
    'require_mane_canonical': True,
}

DOMINANT_MOI = 'D'
RECESSIVE_MOI = 'R'
MITO_MOI = 'M'

CONFIRMED_FAMILY_FILTER = 'confirmed_inheritance'
AFFECTED_MALE_FAMILY_FILTER = 'affected_males'

CLINVAR_FILTER = {
    'clinvar': ['pathogenic', 'likely_pathogenic', 'conflicting_p_lp'],
    'clinvarMinStars': 1,
}

NON_CODING_TRANSCRIPT_EXON_VARIANT = 'non_coding_transcript_exon_variant'
HIGH_ANNOTATIONS= {
    'vep_consequences': [
        'splice_donor_variant',
        'splice_acceptor_variant',
        'stop_gained',
        'frameshift_variant',
    ],
}
MODERATE_ANNOTATIONS = {
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
}
MODERATE_ANNOTATIONS_TRANSCRIPT_EXON_VARIANT = {
    'vep_consequences': [
        *MODERATE_ANNOTATIONS['vep_consequences'],
        NON_CODING_TRANSCRIPT_EXON_VARIANT,
    ]
}
HIGH_MODERATE_ANNOTATIONS = {
    'vep_consequences': [
        *HIGH_ANNOTATIONS['vep_consequences'],
        *MODERATE_ANNOTATIONS_TRANSCRIPT_EXON_VARIANT['vep_consequences'],
    ]
}
SV_ANNOTATIONS = {
    'structural_consequence': ['LOF', 'INTRAGENIC_EXON_DUP'],
}

FREQ_FILTER = {
    'callset': {'ac': 1000},
    'gnomad_exomes': {'af': 0.01, 'hh': 5},
    'gnomad_genomes': {'af': 0.01, 'hh': 5},
    'sv_callset': {'ac': 500},
    'gnomad_svs': {'af': 0.01},
}

IN_SILICO_FILTER = {
    'cadd': 22.8,
    'revel': 0.291,
}

QUALITY_FILTER = {
    'min_gq': 30,
    'min_ab': 20
}
SV_QUALITY_FILTER = {
    'min_gq_sv': 90,
}
PASS_QUALITY_FILTER = {
    **QUALITY_FILTER,
    **SV_QUALITY_FILTER,
    'vcf_filter': 'PASS',
}
PERMISSIVE_PASS_QUALITY_FILTER = {
    **PASS_QUALITY_FILTER,
    'min_gq_sv': 50,
}

CONFIRMED_HIGH_SPLICE_AI_SEARCH = {
    'family_filter': {
        CONFIRMED_FAMILY_FILTER: True
    },
    'in_silico': {
        'splice_ai': 0.5,
        'requireScore': True
    },
}
HIGH_SPLICE_AI_SEARCH = {
    'family_filter': {
        CONFIRMED_FAMILY_FILTER: False
    },
    'in_silico': {
        'splice_ai': 0.8,
        'requireScore': True
    },
}

CLINVAR_RECESSIVE_SEARCH = {
    'gene_list_moi': RECESSIVE_MOI,
    'pathogenicity': CLINVAR_FILTER,
    'freqs': {
        'callset': {'ac': 2000},
        'gnomad_exomes': {'af': 0.03},
        'gnomad_genomes': {'af': 0.03}
    },
}

RECESSIVE_SEARCH_NO_IN_SILICO = {
    'gene_list_moi': RECESSIVE_MOI,
    'freqs': FREQ_FILTER,
    'qualityFilter': QUALITY_FILTER,
}
RECESSIVE_SEARCH = {
    **RECESSIVE_SEARCH_NO_IN_SILICO,
    'in_silico': IN_SILICO_FILTER,
}
SV_RECESSIVE_SEARCH = {
    'gene_list_moi': RECESSIVE_MOI,
    'annotations': SV_ANNOTATIONS,
    'freqs': FREQ_FILTER,
    'qualityFilter': SV_QUALITY_FILTER,
}

NO_PANEL_APP_DE_NOVO_SEARCH = {
    'inheritance_mode': DE_NOVO,
    'freqs': {
        'callset': {'ac': 100},
        'gnomad_exomes': {'ac': 100},
        'gnomad_genomes': {'ac': 100},
        'sv_callset': {'ac': 100},
        'gnomad_svs': {'af': 0.001},
    },
    'qualityFilter': PASS_QUALITY_FILTER,
}
DE_NOVO_SEARCH = {
    'gene_list_moi': DOMINANT_MOI,
    **NO_PANEL_APP_DE_NOVO_SEARCH,
}

SEARCHES = {
    'SNV_INDEL': {
        'Clinvar Pathogenic': {
            'gene_list_moi': DOMINANT_MOI,
            'inheritance_mode': ANY_AFFECTED,
            'pathogenicity': CLINVAR_FILTER,
            'freqs': {
                'callset': {'ac': 150},
                'gnomad_exomes': {'ac': 150},
                'gnomad_genomes': {'ac': 150},
            },
        },
        'Clinvar Pathogenic - Compound Heterozygous': {
            'inheritance_mode': COMPOUND_HET,
            'annotations': {},
            'annotations_secondary': HIGH_MODERATE_ANNOTATIONS,
            **CLINVAR_RECESSIVE_SEARCH,
        },
        'Clinvar Both Pathogenic - Compound Heterozygous': {
            'inheritance_mode': COMPOUND_HET,
            **CLINVAR_RECESSIVE_SEARCH,
        },
        'Clinvar Pathogenic - Recessive': {
            'inheritance_mode': HOMOZYGOUS_RECESSIVE,
            **CLINVAR_RECESSIVE_SEARCH,
        },
        'Clinvar Pathogenic - X-Linked Recessive': {
            'inheritance_mode': X_LINKED_RECESSIVE_MALE_AFFECTED,
            'family_filter': {
                AFFECTED_MALE_FAMILY_FILTER: True
            },
            **CLINVAR_RECESSIVE_SEARCH,
        },
        'Compound Heterozygous': {
            'inheritance_mode': COMPOUND_HET,
            'annotations': HIGH_ANNOTATIONS,
            'annotations_secondary': HIGH_MODERATE_ANNOTATIONS,
            **RECESSIVE_SEARCH,
        },
        'Compound Heterozygous - Confirmed': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: True
            },
            'inheritance_mode': COMPOUND_HET,
            'annotations': MODERATE_ANNOTATIONS,
            **RECESSIVE_SEARCH,
        },
        'Compound Heterozygous - Both High Splice AI': {
            'inheritance_mode': COMPOUND_HET,
            **HIGH_SPLICE_AI_SEARCH,
            **RECESSIVE_SEARCH_NO_IN_SILICO,
        },
        'Compound Heterozygous - Both High Splice AI - Confirmed': {
            'inheritance_mode': COMPOUND_HET,
            **CONFIRMED_HIGH_SPLICE_AI_SEARCH,
            **RECESSIVE_SEARCH_NO_IN_SILICO,
        },
        'Compound Heterozygous - Clinvar Pathogenic/ High Splice AI': {
            'inheritance_mode': COMPOUND_HET,
            'annotations': {},
            'annotations_secondary': {
                'splice_ai': 0.5,
            },
            **CLINVAR_RECESSIVE_SEARCH,
        },
        'Compound Heterozygous - High Splice AI': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: False
            },
            'inheritance_mode': COMPOUND_HET,
            'no_secondary_annotations': True,
            'annotations': HIGH_MODERATE_ANNOTATIONS,
            'annotations_secondary':{
                'splice_ai': 0.8,
            },
            'in_silico': {
                **IN_SILICO_FILTER,
                'splice_ai': 0.8,
            },
            **RECESSIVE_SEARCH_NO_IN_SILICO,
        },
        'Compound Heterozygous - High Splice AI - Confirmed': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: True
            },
            'inheritance_mode': COMPOUND_HET,
            'no_secondary_annotations': True,
            'annotations': HIGH_MODERATE_ANNOTATIONS,
            'annotations_secondary':{
                'splice_ai': 0.5,
            },
            'in_silico': {
                **IN_SILICO_FILTER,
                'splice_ai': 0.5,
            },
            **RECESSIVE_SEARCH_NO_IN_SILICO,
        },
        'De Novo/ Dominant - Confirmed': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: True
            },
            'annotations': {
                'vep_consequences': [
                    *HIGH_ANNOTATIONS['vep_consequences'],
                    *MODERATE_ANNOTATIONS['vep_consequences'],
                ]
            },
            'require_any_gene': True,
            'in_silico': IN_SILICO_FILTER,
            **NO_PANEL_APP_DE_NOVO_SEARCH,
        },
        'De Novo/ Dominant - Non-coding Transcript Exon Variant': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: True
            },
            'annotations': {
                'vep_consequences': [NON_CODING_TRANSCRIPT_EXON_VARIANT],
            },
            'in_silico': IN_SILICO_FILTER,
            **DE_NOVO_SEARCH,
        },
        'De Novo/ Dominant': {
            'annotations': HIGH_ANNOTATIONS,
            'in_silico': IN_SILICO_FILTER,
            **DE_NOVO_SEARCH,
        },
        'High Splice AI - De Novo/ Dominant': {
            **HIGH_SPLICE_AI_SEARCH,
            **DE_NOVO_SEARCH,
        },
        'High Splice AI - De Novo/ Dominant Confirmed': {
            **CONFIRMED_HIGH_SPLICE_AI_SEARCH,
            **NO_PANEL_APP_DE_NOVO_SEARCH,
        },
        'High Splice AI - Recessive': {
            'inheritance_mode': HOMOZYGOUS_RECESSIVE,
            **HIGH_SPLICE_AI_SEARCH,
            **RECESSIVE_SEARCH_NO_IN_SILICO,
        },
        'High Splice AI - Recessive Confirmed': {
            'inheritance_mode': HOMOZYGOUS_RECESSIVE,
            **CONFIRMED_HIGH_SPLICE_AI_SEARCH,
            **RECESSIVE_SEARCH_NO_IN_SILICO,
        },
        'High Splice AI - X-Linked Recessive': {
            'inheritance_mode': X_LINKED_RECESSIVE_MALE_AFFECTED,
            **HIGH_SPLICE_AI_SEARCH,
            **RECESSIVE_SEARCH_NO_IN_SILICO,
            'family_filter': {
                AFFECTED_MALE_FAMILY_FILTER: True,
                CONFIRMED_FAMILY_FILTER: False,
            },
        },
        'High Splice AI - X-Linked Recessive Confirmed': {
            'inheritance_mode': X_LINKED_RECESSIVE_MALE_AFFECTED,
            **CONFIRMED_HIGH_SPLICE_AI_SEARCH,
            **RECESSIVE_SEARCH_NO_IN_SILICO,
            'family_filter': {
                AFFECTED_MALE_FAMILY_FILTER: True,
                CONFIRMED_FAMILY_FILTER: True,
            },
        },
        'Recessive': {
            'inheritance_mode': HOMOZYGOUS_RECESSIVE,
            'annotations': HIGH_MODERATE_ANNOTATIONS,
            **RECESSIVE_SEARCH,
        },
        'X-Linked Recessive': {
            'inheritance_mode': X_LINKED_RECESSIVE_MALE_AFFECTED,
            'family_filter': {
                AFFECTED_MALE_FAMILY_FILTER: True
            },
            'annotations': HIGH_MODERATE_ANNOTATIONS,
            **RECESSIVE_SEARCH,
        },
    },
    'SV': {
        'SV - Compound Heterozygous': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: True
            },
            'inheritance_mode': COMPOUND_HET,
            **SV_RECESSIVE_SEARCH,
            'qualityFilter': PASS_QUALITY_FILTER,
        },
        'SV - De Novo/ Dominant': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: True
            },
            'annotations': SV_ANNOTATIONS,
            **DE_NOVO_SEARCH,
        },
        'SV - Recessive': {
            'family_filter': {
                CONFIRMED_FAMILY_FILTER: True
            },
            'inheritance_mode': HOMOZYGOUS_RECESSIVE,
            **SV_RECESSIVE_SEARCH,
        },
        'SV - X-Linked Recessive': {
            'inheritance_mode': X_LINKED_RECESSIVE_MALE_AFFECTED,
            'family_filter': {
                AFFECTED_MALE_FAMILY_FILTER: True,
                CONFIRMED_FAMILY_FILTER: True,
            },
            **SV_RECESSIVE_SEARCH,
        },
    },
    'MITO': {
        'Mitochondrial - Pathogenic': {
            'inheritance_mode': ANY_AFFECTED,
            'pathogenicity': {'clinvar': CLINVAR_FILTER['clinvar']},
            'annotations': {
                'mitomap_pathogenic': True,
            },
            'freqs': {
                'gnomad_mito': {'af': 0.05},
            },
        },
        'Mitochondrial - De Novo/ Dominant': {
            'gene_list_moi': MITO_MOI,
            'inheritance_mode': DE_NOVO,
            'annotations': HIGH_MODERATE_ANNOTATIONS,
            'freqs': {
                'gnomad_mito': {'af': 0.001},
            },
            'in_silico': {
                'apogee': 0.5,
                'hmtvar': 0.35,
                'mlc': 0.75,
            },
            'qualityFilter': {
                'min_hl': 5,
                'min_mitoCn': 150,
            },
        },
    },
}

MULTI_DATA_TYPE_SEARCHES = {
    'Compound Heterozygous - One SV': {
        'annotations': HIGH_ANNOTATIONS,
        'annotations_secondary': SV_ANNOTATIONS,
        'in_silico': IN_SILICO_FILTER,
        'freqs': FREQ_FILTER,
        'qualityFilter': PERMISSIVE_PASS_QUALITY_FILTER,
    },
    'Compound Heterozygous - Clinvar Pathogenic/ SV': {
        'annotations': {},
        'annotations_secondary': SV_ANNOTATIONS,
        'pathogenicity': CLINVAR_FILTER,
        'freqs': FREQ_FILTER,
        'qualityFilter': PERMISSIVE_PASS_QUALITY_FILTER,
    },
    'Compound Heterozygous - High Splice AI/ SV': {
        'annotations': {
            'splice_ai': 0.8,
        },
        'annotations_secondary': SV_ANNOTATIONS,
        'freqs': FREQ_FILTER,
        'qualityFilter': PERMISSIVE_PASS_QUALITY_FILTER,
    },
    'Compound Heterozygous - One SV - Confirmed': {
        'family_filter': {
            CONFIRMED_FAMILY_FILTER: True,
        },
        'annotations': MODERATE_ANNOTATIONS_TRANSCRIPT_EXON_VARIANT,
        'annotations_secondary': SV_ANNOTATIONS,
        'in_silico': IN_SILICO_FILTER,
        'freqs': FREQ_FILTER,
        'qualityFilter': PERMISSIVE_PASS_QUALITY_FILTER,
    },
}

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('project')

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

        updates = {update: set() for update in ['matched_families', 'new_tag_keys', 'update_tag_keys', 'skipped_tag_keys']}
        search_counts = {}
        samples_by_dataset_type = {}
        sample_qs = Individual.objects.filter(family__project=project)
        for dataset_type, searches in SEARCHES.items():
            self._run_dataset_type_searches(
                dataset_type, searches, sample_qs, updates, search_counts, samples_by_dataset_type, family_guid_map,
                project, exclude_genes, gene_by_moi,
            )

        self._run_multi_data_type_comp_het_search(
            updates, search_counts, samples_by_dataset_type, family_guid_map, project, genes=gene_by_moi[RECESSIVE_MOI],
        )

        new_tag_keys = updates['new_tag_keys']
        logger.info(f'Tagged {len(new_tag_keys)} new and {len(updates["update_tag_keys"])} previously tagged variants in {len(updates["matched_families"])} families, found {len(updates["skipped_tag_keys"])} unchanged tags:')
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
    def _run_dataset_type_searches(cls, dataset_type, searches, sample_qs, updates, search_counts, samples_by_dataset_type, family_guid_map, project, exclude_genes, gene_by_moi):
        is_sv = dataset_type == Dataset.DATASET_TYPE_SV_CALLS
        sample_qs = sample_qs.filter(active_datasets__dataset_type=dataset_type)
        if is_sv:
            sample_qs = sample_qs.exclude(
                sv_flags__contains=['outlier_num._calls'], affected=Individual.AFFECTED_STATUS_AFFECTED,
            )
        sample_types = list(sample_qs.values_list('active_datasets__sample_type', flat=True).distinct())
        if len(sample_types) > 1:
            raise CommandError('Variant prioritization not supported for projects with multiple sample types')
        sample_type = sample_types[0]
        if is_sv:
            dataset_type = f'{dataset_type}_{sample_type}'
        samples_by_family = {
            agg['family__guid']: agg for agg in sample_qs.values('family__guid').annotate(
                affecteds=ArrayAgg(
                    JSONObject(maternal_guid='mother__guid', paternal_guid='father__guid', sex='sex'),
                    filter=Q(affected=Individual.AFFECTED_STATUS_AFFECTED),
                ),
                unaffected_guids=ArrayAgg('guid', filter=Q(affected=Individual.AFFECTED_STATUS_UNAFFECTED)),
            ).filter(affecteds__len__gt=0)
        }
        samples_by_dataset_type[dataset_type] = samples_by_family

        family_variant_data = defaultdict(lambda: {'matched_searches': set(), 'matched_comp_het_searches': set(), 'support_vars': set()})
        logger.info(f'Searching for prioritized {dataset_type} variants in {len(samples_by_family)} families in project {project.name}')
        for search_name, config_search in searches.items():
            logger.info(f'Searching for criteria: {search_name}')
            exclude_locations = not config_search.get('gene_list_moi')
            search_genes = exclude_genes if exclude_locations else gene_by_moi[config_search['gene_list_moi']]
            sample_data = cls._get_valid_family_sample_data(
                project, sample_type, samples_by_family, config_search.get('family_filter'),
            )
            num_results = cls._execute_search(
                {dataset_type: sample_data}, search_name, family_variant_data, family_guid_map,
                exclude_locations=exclude_locations, genes=search_genes, **config_search, **ALL_SEARCHES_CRITERIA,
            ) if sample_data['num_families'] else 0
            search_counts[search_name] = num_results

        cls._bulk_tag_variants(family_variant_data, updates, dataset_type)

    @classmethod
    def _get_valid_family_sample_data(cls, project, sample_type, samples_by_family, family_filter):
        if family_filter:
            samples_by_family = {
                family_guid: sample_data for family_guid, sample_data in samples_by_family.items()
                if cls._family_passes_filter(sample_data, family_filter)
            }
        return {
            'project_guids': [project.guid],
            'num_families': len(samples_by_family),
            'num_unaffected': sum(len(s['unaffected_guids']) for s in samples_by_family.values()),
            'sample_type_families': {sample_type: set(samples_by_family.keys())},
        }

    @staticmethod
    def _family_passes_filter(sample_data, family_filter):
        if family_filter.get(AFFECTED_MALE_FAMILY_FILTER) and all(s['sex'] not in Individual.MALE_SEXES for s in sample_data['affecteds']):
            return False
        if CONFIRMED_FAMILY_FILTER in family_filter:
            proband = next((s for s in sample_data['affecteds'] if s['maternal_guid'] and s['paternal_guid']), None)
            if not proband:
                return False
            is_confirmed = proband['maternal_guid'] in sample_data['unaffected_guids'] and proband['paternal_guid'] in sample_data['unaffected_guids']
            return (not is_confirmed) if family_filter[CONFIRMED_FAMILY_FILTER] == False else is_confirmed
        return True

    @staticmethod
    def _get_metadata(today, metadata_key):
        def wrapped(v):
            return {name: today for name in v[metadata_key]} if v[metadata_key] else None
        return wrapped

    @staticmethod
    def _parse_new_saved_variants(dataset_type):
        def wrapped(new_variant_keys, family_variant_data):
            new_variant_data = {k: v for k, v in family_variant_data.items() if k in new_variant_keys}
            variants_by_id = get_saved_variant_annotations(
                {k for k, v in new_variant_data.items() if not (v.get('key') and v.get('variantId'))},
                dataset_type=dataset_type, genome_version=GENOME_VERSION_GRCh38, primary_id_field='key',
            )
            return {
                k: {**v, 'dataset_type': dataset_type, **json.loads(json.dumps(variants_by_id.get(k[1], {}), cls=DjangoJSONEncoderWithSets))}
                for k, v in family_variant_data.items() if k in new_variant_keys
            }
        return wrapped

    @classmethod
    def _run_multi_data_type_comp_het_search(cls, updates, search_counts, samples_by_dataset_type, family_guid_map, project, genes):
        sv_dataset_type = next(dt for dt in samples_by_dataset_type.keys() if dt.startswith('SV'))
        sample_type = sv_dataset_type.split('_')[-1]
        families = set(samples_by_dataset_type[sv_dataset_type].keys()).intersection(samples_by_dataset_type[Dataset.DATASET_TYPE_VARIANT_CALLS].keys())
        sv_samples_by_family = {
            guid: sample_data for guid, sample_data in samples_by_dataset_type[sv_dataset_type].items() if guid in families
        }
        snv_indel_samples_by_family = {
            guid: sample_data for guid, sample_data in samples_by_dataset_type[Dataset.DATASET_TYPE_VARIANT_CALLS].items()
            if guid in families
        }
        family_variant_data = defaultdict(lambda: {'matched_searches': set(), 'matched_comp_het_searches': set(), 'support_vars': set()})
        logger.info(f'Searching for prioritized multi data type variants in {len(families)} families in project {project.name}')
        for search_name, config_search in MULTI_DATA_TYPE_SEARCHES.items():
            logger.info(f'Searching for criteria: {search_name}')
            sv_sample_data = cls._get_valid_family_sample_data(
                project, sample_type, sv_samples_by_family, config_search.get('family_filter'),
            )
            snv_indel_sample_data = cls._get_valid_family_sample_data(
                project, sample_type, snv_indel_samples_by_family, config_search.get('family_filter'),
            )
            sample_data_by_dataset_type = {
                Dataset.DATASET_TYPE_VARIANT_CALLS: snv_indel_sample_data, sv_dataset_type: sv_sample_data,
            }
            num_results = cls._execute_search(
                sample_data_by_dataset_type, search_name, family_variant_data, family_guid_map,
                inheritance_mode=COMPOUND_HET, **config_search, **ALL_SEARCHES_CRITERIA, genes=genes,
            )
            search_counts[search_name] = num_results

        cls._bulk_tag_variants(family_variant_data, updates)

    @staticmethod
    def _execute_search(sample_data_by_dataset_type, search_name, family_variant_data, family_guid_map, **kwargs):
        results = get_clickhouse_variants(
            families=None, search=kwargs, user=None, genome_version=GENOME_VERSION_GRCh38,
            sample_data_by_dataset_type={
                **{dt: None for dt in ENTRY_CLASS_MAP[GENOME_VERSION_GRCh38]}, **sample_data_by_dataset_type,
            },
        )
        for result in results:
            if isinstance(result, list):
                for family_guid in result[0]['familyGuids']:
                    for variant, support_id in [(result[0], result[1]['key']), (result[1], result[0]['key'])]:
                        variant_data = family_variant_data[(family_guid_map[family_guid], variant['key'])]
                        variant_data.update(variant)
                        variant_data['genotypes'] = json.loads(json.dumps(variant_data['genotypes'], cls=DjangoJSONEncoderWithSets))
                        variant_data['support_vars'].add(support_id)
                        variant_data['matched_comp_het_searches'].add(search_name)
            else:
                for family_guid in result.pop('familyGuids'):
                    variant_data = family_variant_data[(family_guid_map[family_guid], result['key'])]
                    variant_data.update(result)
                    variant_data['genotypes'] = json.loads(json.dumps(variant_data['genotypes'], cls=DjangoJSONEncoderWithSets))
                    variant_data['matched_searches'].add(search_name)

        return len(results)

    @classmethod
    def _bulk_tag_variants(cls, family_variant_data, updates, dataset_type=None):
        today = datetime.now().strftime('%Y-%m-%d')
        new_tag_keys, update_tag_keys, skipped_tag_keys = bulk_create_tagged_variants(
            family_variant_data, tag_name=SEQR_TAG_TYPE, get_metadata=cls._get_metadata(today, 'matched_searches'),
            get_comp_het_metadata=cls._get_metadata(today, 'matched_comp_het_searches'), user=None,
            remove_missing_metadata=False, primary_id_field='key', parse_new_saved_variants=cls._parse_new_saved_variants(dataset_type),
        )
        updates['new_tag_keys'].update(new_tag_keys)
        updates['update_tag_keys'].update(update_tag_keys - updates['new_tag_keys'])
        updates['skipped_tag_keys'].update(skipped_tag_keys - updates['update_tag_keys'] - updates['new_tag_keys'])
        updates['matched_families'].update({family_id for family_id, _ in family_variant_data.keys()})

    @staticmethod
    def _get_gene_list_genes(name, confidences, gene_by_moi, exclude_gene_ids):
        ll = LocusList.objects.get(name=name, palocuslist__isnull=False)
        moi_gene_ids = ll.locuslistgene_set.exclude(gene_id__in=exclude_gene_ids).annotate(
            is_dominant=Q(
                Q(palocuslistgene__mode_of_inheritance__startswith='MONOALLELIC') &
                ~Q(palocuslistgene__mode_of_inheritance__contains=' paternally imprinted') &
                ~Q(palocuslistgene__mode_of_inheritance__contains=' maternally imprinted')
            ),
            is_recessive=Q(
                palocuslistgene__mode_of_inheritance__startswith='BIALLELIC'
            ) | Q(
                palocuslistgene__mode_of_inheritance__startswith='X-LINKED',
                palocuslistgene__mode_of_inheritance__contains='biallelic mutations',
            ),
            is_mito=Q(
                palocuslistgene__mode_of_inheritance__startswith='MITOCHONDRIAL'
            ),
        ).filter(palocuslistgene__confidence_level__in=[
            level for level, name in PaLocusListGene.CONFIDENCE_LEVEL_CHOICES if name in confidences
        ]).values('gene_id', 'is_dominant', 'is_recessive', 'is_mito')

        gene_id_mois = {g['gene_id']: g for g in moi_gene_ids}
        genes_by_id = get_genes(gene_id_mois.keys(), genome_version=GENOME_VERSION_GRCh38, additional_model_fields=['id'])
        gene_by_moi[DOMINANT_MOI].update({gene_id: gene for gene_id, gene in genes_by_id.items() if not gene_id_mois[gene_id]['is_recessive']})
        gene_by_moi[RECESSIVE_MOI].update({gene_id: gene for gene_id, gene in genes_by_id.items() if not gene_id_mois[gene_id]['is_dominant']})
        gene_by_moi[MITO_MOI].update({gene_id: gene for gene_id, gene in genes_by_id.items() if gene_id_mois[gene_id]['is_mito']})
