from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, VariantNote as BaseVariantNote, \
    VariantTag as BaseVariantTag, ProjectTag, VCFFile
from xbrowse_server.base.model_utils import update_xbrowse_model, find_matching_seqr_model, get_or_create_xbrowse_model
from seqr.views.apis.phenotips_api import _get_phenotips_uname_and_pwd_for_project, _add_user_to_patient, \
    _phenotips_patient_exists, _get_patient_data


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-project', required=True)
        parser.add_argument('--to-project', required=True)
        parser.add_argument('family_ids', nargs='+')

    def handle(self, *args, **options):
        from_project = BaseProject.objects.get(project_id=options['from_project'])
        to_project = BaseProject.objects.get(project_id=options['to_project'])
        to_seqr_project = find_matching_seqr_model(to_project)
        family_ids = options['family_ids']
        families = BaseFamily.objects.filter(project=from_project, family_id__in=family_ids)
        print('Found {} out of {} families. No match for: {}.'.format(len(families), len(set(family_ids)), set(family_ids) - set([f.family_id for f in families])))

        for f in families:
            print("==> Moving {}".format(f))
            for individual in f.individual_set.all():
                individual.project = to_project
                individual.save()
                # Update individuals in phenotips
                if _phenotips_patient_exists(individual.seqr_individual):
                    # make sure phenotips_patient_id is up to date
                    seqr_individual = individual.seqr_individual
                    data_json = _get_patient_data(
                        from_project.seqr_project,
                        seqr_individual,
                    )

                    seqr_individual.phenotips_patient_id = data_json["id"]
                    seqr_individual.save()

                    # update permissions
                    phenotips_readonly_username, _ = _get_phenotips_uname_and_pwd_for_project(to_project.seqr_project.phenotips_user_id, read_only=True)
                    _add_user_to_patient(phenotips_readonly_username, seqr_individual.phenotips_patient_id, allow_edit=False)

                    phenotips_readwrite_username, _ = _get_phenotips_uname_and_pwd_for_project(to_project.seqr_project.phenotips_user_id, read_only=False)
                    _add_user_to_patient(phenotips_readwrite_username, seqr_individual.phenotips_patient_id, allow_edit=True)

                # Update individuals samples/ VCFs
                for from_vcf_file in individual.vcf_files.all():
                    to_vcf_file, _ = VCFFile.objects.get_or_create(
                        project=to_project,
                        elasticsearch_index=from_vcf_file.elasticsearch_index,
                        file_path=from_vcf_file.file_path,
                        dataset_type=from_vcf_file.dataset_type,
                        sample_type=from_vcf_file.sample_type,
                        loaded_date=from_vcf_file.loaded_date,
                    )
                    individual.vcf_files.add(to_vcf_file)
                    individual.vcf_files.remove(from_vcf_file)

            # Update variant tags/ notes
            saved_variants = set()
            for note in BaseVariantNote.objects.filter(family=f):
                seqr_note = find_matching_seqr_model(note)
                if seqr_note:
                    saved_variants.add(seqr_note.saved_variant)
                note.project = to_project
                note.save()

            for variant_tag in BaseVariantTag.objects.filter(family=f):
                to_project_tag, created = get_or_create_xbrowse_model(
                    ProjectTag, project=to_project, tag=variant_tag.project_tag.tag
                )
                if created:
                    update_xbrowse_model(
                        to_project_tag,
                        category=variant_tag.project_tag.category,
                        title=variant_tag.project_tag.title,
                        color=variant_tag.project_tag.color,
                        order=variant_tag.project_tag.order,
                    )
                update_xbrowse_model(variant_tag, project_tag=to_project_tag)
                seqr_variant_tag = find_matching_seqr_model(variant_tag)
                if seqr_variant_tag:
                    saved_variants.add(seqr_variant_tag.saved_variant)

            for saved_variant in saved_variants:
                saved_variant.project = to_seqr_project
                saved_variant.save()

            # Update families
            update_xbrowse_model(f, project=to_project)

        print("Done.")
