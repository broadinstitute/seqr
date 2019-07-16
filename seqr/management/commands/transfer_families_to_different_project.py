from django.core.management.base import BaseCommand
from xbrowse_server.base.models import VariantNote as BaseVariantNote, ProjectTag, VCFFile

from seqr.models import Project, Family, SavedVariant, VariantTag, VariantTagType
from seqr.model_utils import find_matching_xbrowse_model, update_seqr_model, get_or_create_seqr_model
from seqr.views.apis.phenotips_api import _get_phenotips_uname_and_pwd_for_project, _add_user_to_patient, \
    _phenotips_patient_exists, _get_patient_data


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-project', required=True)
        parser.add_argument('--to-project', required=True)
        parser.add_argument('family_ids', nargs='+')

    def handle(self, *args, **options):
        from_project = Project.objects.get(guid=options['from_project'])
        to_project = Project.objects.get(guid=options['to_project'])
        to_base_project = find_matching_xbrowse_model(to_project)
        family_ids = options['family_ids']
        families = Family.objects.filter(project=from_project, family_id__in=family_ids)
        print('Found {} out of {} families. No match for: {}.'.format(len(families), len(set(family_ids)), set(family_ids) - set([f.family_id for f in families])))

        for f in families:
            print("==> Moving {}".format(f))
            for seqr_individual in f.individual_set.all():
                base_individual = find_matching_xbrowse_model(seqr_individual)
                base_individual.project = to_base_project
                base_individual.save()
                # Update individuals in phenotips
                if _phenotips_patient_exists(seqr_individual):
                    # make sure phenotips_patient_id is up to date
                    data_json = _get_patient_data(
                        from_project,
                        seqr_individual,
                    )

                    seqr_individual.phenotips_patient_id = data_json["id"]
                    seqr_individual.save()

                    # update permissions
                    phenotips_readonly_username, _ = _get_phenotips_uname_and_pwd_for_project(to_project.phenotips_user_id, read_only=True)
                    _add_user_to_patient(phenotips_readonly_username, seqr_individual.phenotips_patient_id, allow_edit=False)

                    phenotips_readwrite_username, _ = _get_phenotips_uname_and_pwd_for_project(to_project.phenotips_user_id, read_only=False)
                    _add_user_to_patient(phenotips_readwrite_username, seqr_individual.phenotips_patient_id, allow_edit=True)

                # Update individuals samples/ VCFs
                for from_vcf_file in base_individual.vcf_files.all():
                    to_vcf_file, _ = VCFFile.objects.get_or_create(
                        project=to_base_project,
                        elasticsearch_index=from_vcf_file.elasticsearch_index,
                        file_path=from_vcf_file.file_path,
                        dataset_type=from_vcf_file.dataset_type,
                        sample_type=from_vcf_file.sample_type,
                        loaded_date=from_vcf_file.loaded_date,
                    )
                    base_individual.vcf_files.add(to_vcf_file)
                    base_individual.vcf_files.remove(from_vcf_file)

            # Update variant tags/ notes
            saved_variants = SavedVariant.objects.filter(family=f)
            for saved_variant in saved_variants:
                saved_variant.project = to_project
                saved_variant.save()

            for variant_tag in VariantTag.objects.filter(saved_variant__in=saved_variants).select_related('variant_tag_type'):
                if variant_tag.variant_tag_type.project:
                    to_tag_type, created = get_or_create_seqr_model(
                        VariantTagType, project=to_project, name=variant_tag.variant_tag_type.name
                    )
                    if created:
                        update_seqr_model(
                            to_tag_type,
                            category=variant_tag.variant_tag_type.category,
                            description=variant_tag.variant_tag_type.description,
                            color=variant_tag.variant_tag_type.color,
                            order=variant_tag.variant_tag_type.order,
                        )
                    update_seqr_model(variant_tag, variant_tag_type=to_tag_type)
                else:
                    to_project_tag, created = ProjectTag.objects.get_or_create(
                        project=to_base_project, tag=variant_tag.variant_tag_type.name
                    )
                    if created:
                        to_project_tag.category = variant_tag.variant_tag_type.category
                        to_project_tag.title = variant_tag.variant_tag_type.description
                        to_project_tag.color = variant_tag.variant_tag_type.color
                        to_project_tag.order = variant_tag.variant_tag_type.order
                        to_project_tag.save()
                    variant_tag.project_tag = to_project_tag
                    variant_tag.save()

            base_family = find_matching_xbrowse_model(f)
            for note in BaseVariantNote.objects.filter(family=base_family):
                note.project = to_base_project
                note.save()

            # Update families
            update_seqr_model(f, project=to_project)

        print("Done.")
