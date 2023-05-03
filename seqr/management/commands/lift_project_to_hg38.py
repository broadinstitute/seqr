import logging
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db.models.query_utils import Q
from pyliftover.liftover import LiftOver

from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Project, SavedVariant, Sample
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants
from seqr.views.utils.variant_utils import reset_cached_search_results
from seqr.utils.search.add_data_utils import add_new_search_samples
from seqr.utils.search.utils import get_variants_for_variant_ids, get_single_variant
from seqr.utils.xpos_utils import get_xpos, get_chrom_pos

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('--project', required=True)
        parser.add_argument('--es-index', required=True)

    def handle(self, *args, **options):
        """transfer project"""
        project_arg = options['project']
        project = Project.objects.get(Q(name=project_arg) | Q(guid=project_arg))
        logger.info('Updating project genome version for {}'.format(project.name))

        # Get expected saved variants
        saved_variant_models = SavedVariant.objects.filter(family__project=project)
        saved_variant_models_by_guid = {v.guid: v for v in saved_variant_models}
        expected_families = {sv.family for sv in saved_variant_models}

        logger.info('Validating es index {}'.format(options['es_index']))
        add_new_search_samples({
            'elasticsearchIndex': options['es_index'],
            'datasetType': Sample.DATASET_TYPE_VARIANT_CALLS,
            'genomeVersion': GENOME_VERSION_GRCh38,
        }, project, user=None, expected_families=expected_families)

        # Lift-over saved variants
        saved_variants = get_json_for_saved_variants(saved_variant_models, add_details=True)
        saved_variants_to_lift, hg37_to_hg38_xpos, lift_failed = _get_variants_to_lift(saved_variants)

        saved_variants_map = defaultdict(list)
        variant_ids = []
        for v in saved_variants_to_lift:
            if hg37_to_hg38_xpos.get(v['xpos']):
                variant_model = saved_variant_models_by_guid[v['variantGuid']]
                xpos_38 = hg37_to_hg38_xpos[v['xpos']]
                saved_variants_map[(xpos_38, v['ref'], v['alt'])].append(variant_model)

                chrom, pos = get_chrom_pos(xpos_38)
                variant_ids.append(f"{'MT' if chrom == 'M' else chrom}-{pos}-{v['ref']}-{v['alt']}")

        es_variants = get_variants_for_variant_ids(
            expected_families, variant_ids, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)

        missing_variants =_validate_missing_variants(es_variants, saved_variants_map)

        logger.info('Successfully lifted over {} variants'.format(len(es_variants)))

        missing_family_count = _update_saved_variants(es_variants, saved_variants_map)

        logger.info('Successfully updated {} variants'.format(len(es_variants)))

        # Update project and sample data
        update_model_from_json(project, {'genome_version': GENOME_VERSION_GRCh38}, None)

        reset_cached_search_results(project)

        logger.info('---Done---')
        logger.info('Succesfully lifted over {} variants. Skipped {} failed variants. Family data not updated for {} variants'.format(
            len(es_variants), len(missing_variants) + len(lift_failed), missing_family_count))

def _get_variants_to_lift(saved_variants):
    saved_variants_to_lift = [v for v in saved_variants if v['genomeVersion'] != GENOME_VERSION_GRCh38]
    num_already_lifted = len(saved_variants) - len(saved_variants_to_lift)
    if num_already_lifted:
        if input('Found {} saved variants already on Hg38. Continue with liftover (y/n)? '.format(
                num_already_lifted)) != 'y':
            raise CommandError('Error: found {} saved variants already on Hg38'.format(num_already_lifted))
    logger.info('Lifting over {} variants (skipping {} that are already lifted)'.format(
        len(saved_variants_to_lift), num_already_lifted))

    liftover_to_38 = LiftOver('hg19', 'hg38')
    hg37_to_hg38_xpos = {}
    lift_failed = {}
    for v in saved_variants_to_lift:
        if not (hg37_to_hg38_xpos.get(v['xpos']) or v['xpos'] in lift_failed):
            hg38_coord = liftover_to_38.convert_coordinate('chr{}'.format(v['chrom'].lstrip('chr')), int(v['pos']))
            if hg38_coord and hg38_coord[0]:
                hg37_to_hg38_xpos[v['xpos']] = get_xpos(hg38_coord[0][0], hg38_coord[0][1])
            else:
                lift_failed[v['xpos']] = v

    if lift_failed:
        if input(
                'Unable to lift over the following {} coordinates. Continue with update (y/n)?: {} '.format(
                    len(lift_failed), ', '.join([
                        '{}:{}-{}-{} ({})'.format(v['chrom'], v['pos'], v['ref'], v['alt'], ', '.join(v['familyGuids']))
                        for v in lift_failed.values()]))) != 'y':
            raise CommandError('Error: unable to lift over {} variants'.format(len(lift_failed)))

    return saved_variants_to_lift, hg37_to_hg38_xpos, lift_failed

def _validate_missing_variants(es_variants, saved_variants_map):
    missing_variants = set(saved_variants_map.keys()) - {(v['xpos'], v['ref'], v['alt']) for v in es_variants}
    if missing_variants:
        missing_variant_strings = []
        for xpos, ref, alt in missing_variants:
            var_id = '{}-{}-{}'.format(xpos, ref, alt)
            for v in saved_variants_map[(xpos, ref, alt)]:
                tags = v.varianttag_set.all()
                notes = v.variantnote_set.all()
                missing_variant_strings.append('{var_id} {family_id}: {tags} ({guid})'.format(
                    var_id=var_id, family_id=v.family.family_id, guid=v.guid,
                    tags=', '.join([tag.variant_tag_type.name for tag in tags]) if tags else 'No Tags; {}'.format(
                        '; '.join([note.note for note in notes]))
                ))
        if input('Unable to find the following {} variants in the index. Continue with update (y/n)?:\n{}\n'.format(
                len(missing_variants), '\n'.join(missing_variant_strings))) != 'y':
            raise CommandError('Error: unable to find {} lifted-over variants'.format(len(missing_variants)))
    return missing_variants

def _update_saved_variants(es_variants, saved_variants_map):
    missing_family_count = 0
    for var in es_variants:
        saved_variant_models = saved_variants_map[(var['xpos'], var['ref'], var['alt'])]
        missing_saved_variants = [v for v in saved_variant_models if v.family.guid not in var['familyGuids']]
        if missing_saved_variants:
            variant_id = '{}-{}-{}-{}'.format(var['chrom'], var['pos'], var['ref'], var['alt'])
            if input(('Variant {} (hg37: {}) not find for expected families {}. Continue with update (y/n)? '.format(
                variant_id, missing_saved_variants[0].xpos,
                ', '.join(['{} ({})'.format(v.family.guid, v.guid) for v in missing_saved_variants]))
            )) == 'y':
                var = get_single_variant([v.family for v in saved_variant_models], variant_id, return_all_queried_families=True)
                missing_family_count += len(missing_saved_variants)
            else:
                raise CommandError('Error: unable to find family data for lifted over variant')
        for saved_variant in saved_variant_models:
            saved_variant.xpos = var['xpos']
            saved_variant.saved_variant_json = var
            saved_variant.save()
    return missing_family_count