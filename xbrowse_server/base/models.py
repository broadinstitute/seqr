from collections import defaultdict
import gzip
import json
import random
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from pretty_times import pretty
from xbrowse import genomeloc
from xbrowse import Cohort as XCohort
from xbrowse import Family as XFamily
from xbrowse import FamilyGroup as XFamilyGroup
from xbrowse import Individual as XIndividual
from xbrowse import vcf_stuff
from xbrowse.core import constants
from xbrowse.core.variant_filters import get_default_variant_filters
from xbrowse_server.mall import get_datastore, get_coverage_store

log = logging.getLogger('xbrowse_server')

PHENOTYPE_CATEGORIES = (
    ('disease', 'Disease'),
    ('clinial_observation', 'Clinical Observation'),
    ('other', 'Other'),
)

PHENOTYPE_DATATYPES = (
    ('bool', 'Boolean'),
    ('number', 'Number'),
)


class UserProfile(models.Model):

    user = models.OneToOneField(User)
    display_name = models.CharField(default="", blank=True, max_length=100)
    set_password_token = models.CharField(max_length=40, blank=True, default="")

    def __unicode__(self):
        return self.display_name if self.display_name else self.user.email

    def get_set_password_link(self):
        """
        Absolute URL of set password link, without leading slash
        """
        return 'set-password?token=' + self.set_password_token

User.profile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])


class VCFFile(models.Model):

    DATASET_TYPE_VARIANT_CALLS = 'VARIANTS'
    DATASET_TYPE_SV = 'SV'
    #DATASET_TYPE_ALIGNMENT = 'ALIGN'
    #DATASET_TYPE_BREAKPOINTS = 'BREAK'
    #DATASET_TYPE_SPLICE_JUNCTIONS = 'SPLICE'
    #DATASET_TYPE_ASE = 'ASE'
    DATASET_TYPE_CHOICES = (
        (DATASET_TYPE_VARIANT_CALLS, 'Variant Calls'),
        (DATASET_TYPE_SV, 'SV Calls'),
        #(DATASET_TYPE_ALIGNMENT, 'Alignment'),
        #(DATASET_TYPE_BREAKPOINTS, 'Breakpoints'),
        #(DATASET_TYPE_SPLICE_JUNCTIONS, 'Splice Junction Calls'),
        #(DATASET_TYPE_ASE, 'Allele Specific Expression'),
    )

    SAMPLE_TYPE_WES = 'WES'
    SAMPLE_TYPE_WGS = 'WGS'
    SAMPLE_TYPE_RNA = 'RNA'
    SAMPLE_TYPE_ARRAY = 'ARRAY'
    SAMPLE_TYPE_CHOICES = (
        (SAMPLE_TYPE_WES, 'Exome'),
        (SAMPLE_TYPE_WGS, 'Whole Genome'),
        (SAMPLE_TYPE_RNA, 'RNA'),
        (SAMPLE_TYPE_ARRAY, 'ARRAY'),
        # ('ILLUMINA_INFINIUM_250K', ),
    )

    # for convenience, add a pointer back to the project that contains this dataset
    project = models.ForeignKey('Project', null=True, on_delete=models.CASCADE)

    file_path = models.TextField(default="", blank=True)

    dataset_type = models.CharField(max_length=10, choices=DATASET_TYPE_CHOICES, default=DATASET_TYPE_VARIANT_CALLS)
    sample_type = models.CharField(max_length=3, choices=SAMPLE_TYPE_CHOICES, null=True, blank=True)

    # if the variants are loaded into Elasticsearch, this field should be set to the name of the elasticsearch index.
    # otherwise, it should = None
    elasticsearch_index = models.TextField(null=True, blank=True, db_index=True)

    loaded_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.file_path

    def path(self):
        return self.file_path

    def file_handle(self):
        if self.file_path.endswith('.gz'):
            return gzip.open(self.file_path)
        else:
            return open(self.file_path)

    def sample_id_list(self):
        return vcf_stuff.get_ids_from_vcf_path(self.path())


class ReferencePopulation(models.Model):
    slug = models.SlugField(default="", max_length=50)
    name = models.CharField(default="", max_length=100)
    file_type = models.CharField(default="", max_length=50)
    file_path = models.CharField(default="", max_length=500)
    is_public = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def to_dict(self):
        return {
            'slug': self.slug,
            'name': self.name,
            'file_type': self.file_type,
            'file_path': self.file_path,
        }


COLLABORATOR_TYPES = (
    ('manager', 'Manager'),
    ('collaborator', 'Collaborator'),
)


class ProjectCollaborator(models.Model):
    user = models.ForeignKey(User)
    project = models.ForeignKey('base.Project')
    collaborator_type = models.CharField(max_length=20, choices=COLLABORATOR_TYPES, default="collaborator")


class Project(models.Model):
    DISEASE_AREA = [(da.lower().replace(" ", "_"), da) for da in (
        "Blood", "Cardio", "Kidney", "Muscle", "Neurodev", "Orphan Disease", "Retinal")
    ]

    genome_version = models.CharField(default=constants.GENOME_VERSION_GRCh37, max_length=3)
    project_id = models.SlugField(max_length=500, default="", blank=True, unique=True)

    project_name = models.TextField(default="", blank=True)
    description = models.TextField(blank=True, default="")

    created_date = models.DateTimeField(null=True, blank=True)  # default=timezone.now, db_index=True)
    created_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    # this is the last time a project is "accessed" - currently set whenever one looks at the project home view
    # used so we can reload projects in order of last access
    last_accessed_date = models.DateTimeField(null=True, blank=True)

    is_phenotips_enabled = models.BooleanField(default=False)
    phenotips_user_id = models.TextField(null=True, blank=True, db_index=True)

    is_mme_enabled = models.BooleanField(default=True)
    mme_primary_data_owner = models.TextField(null=True, blank=True, default=settings.MME_DEFAULT_CONTACT_NAME)
    mme_contact_url = models.TextField(null=True, blank=True, default=settings.MME_DEFAULT_CONTACT_HREF)
    mme_contact_institution = models.TextField(null=True, blank=True, default=settings.MME_DEFAULT_CONTACT_INSTITUTION)

    disease_area = models.TextField(null=True, blank=True, choices=DISEASE_AREA)

    private_reference_populations = models.ManyToManyField(ReferencePopulation, blank=True)
    gene_lists = models.ManyToManyField('gene_lists.GeneList', through='ProjectGeneList')

    default_control_cohort = models.CharField(max_length=100, default="", blank=True)

    # users
    collaborators = models.ManyToManyField(User, blank=True, through='ProjectCollaborator')
    is_public = models.BooleanField(default=False)

    # temporary field for storing metadata on projects that were combined into this one
    combined_projects_info = models.TextField(default="", blank=True)
    seqr_project = models.ForeignKey('seqr.Project', null=True, blank=True, on_delete=models.SET_NULL)  # simplifies migration to new seqr.models schema

    def __unicode__(self):
        return self.project_name if self.project_name != "" else self.project_id

    # Authx
    def can_view(self, user):

        if self.is_public:
            return True
        elif user.is_staff:
            return True
        else:
            return ProjectCollaborator.objects.filter(project=self, user=user).exists()

    def can_edit(self, user):
        if user.is_staff:
            return True
        else:
            return ProjectCollaborator.objects.filter(project=self, user=user).exists()

    def can_admin(self, user):
        if user.is_staff or user.is_superuser:
            return True
        else:
            return ProjectCollaborator.objects.filter(project=self, user=user, collaborator_type="manager").exists()

    def set_as_manager(self, user):
        collab = ProjectCollaborator.objects.get_or_create(user=user, project=self)[0]
        collab.collaborator_type = 'manager'
        collab.save()

        if self.seqr_project:
            self.seqr_project.can_edit_group.user_set.add(user)
            self.seqr_project.can_view_group.user_set.add(user)

    def set_as_collaborator(self, user):
        ProjectCollaborator.objects.get_or_create(user=user, project=self)

        if self.seqr_project:
            self.seqr_project.can_edit_group.user_set.remove(user)
            self.seqr_project.can_view_group.user_set.add(user)

    def get_managers(self):
        result = []
        for c in ProjectCollaborator.objects.filter(project=self, collaborator_type="manager"):
            try:
                result.append(c.user)
            except:
                print("WARNING: couldn't retrieve User object for %s" % str(c))

        return result

    def get_collaborators(self):
        result = []
        for c in ProjectCollaborator.objects.filter(project=self, collaborator_type="collaborator"):
            try:
                result.append(c.user)
            except:
                print("WARNING: couldn't retrieve User object for %s" % str(c))
        return result

    def get_users(self):
        result = []
        for c in ProjectCollaborator.objects.filter(project=self):
            try:
                result.append((c.user, c.collaborator_type))
            except:
                print("WARNING: couldn't retrieve User object for %s" % str(c))
        return result

    # Data / samples
    def has_families(self):
        return self.family_set.filter().exists()

    def num_families(self):
        return self.family_set.filter().count()

    def get_families(self):
        fams = list(self.family_set.all())
        return sorted(fams, key=lambda item: (len(item.family_id), item.family_id))

    def get_active_families(self):
        return [f for f in self.get_families() if f.num_individuals() > 0]

    def has_cohorts(self):
        return self.cohort_set.all().exists()

    def get_cohorts(self):
        return self.cohort_set.all().order_by('cohort_id')

    def num_cohorts(self):
        return self.cohort_set.all().count()

    def has_family_groups(self):
        return self.familygroup_set.all().exists()

    def get_family_groups(self):
        return self.familygroup_set.all().order_by('slug')

    def num_family_groups(self):
        return self.familygroup_set.all().count()

    def families_by_vcf(self):
        families_by_vcf = {}  # map of vcf_file -> list of families from that VCF
        for family in self.family_set.all():
            vcf_files = family.get_vcf_files()
            for vcf_file in vcf_files:
                vcf = vcf_file.path()
                if vcf not in families_by_vcf:
                    families_by_vcf[vcf] = []
                families_by_vcf[vcf].append(family)
        return families_by_vcf

    def cohorts_by_vcf(self):
        by_vcf = {}  # map of vcf_file -> list of families from that VCF
        for cohort in self.cohort_set.all():
            vcf_files = cohort.get_vcf_files()
            for vcf_file in vcf_files:
                vcf = vcf_file.path()
                if vcf not in by_vcf:
                    by_vcf[vcf] = []
                by_vcf[vcf].append(cohort)

        return by_vcf

    # todo: rename to "custom" everywhere
    def get_private_reference_populations(self):
        return self.private_reference_populations.all()

    def private_reference_population_slugs(self):
        return [r.slug for r in self.private_reference_populations.all()]

    def get_reference_population_slugs(self):
        return settings.ANNOTATOR_REFERENCE_POPULATION_SLUGS + self.private_reference_population_slugs()

    def get_options_json(self):
        d = dict(project_id=self.project_id)
        d['id'] = self.id
        d['reference_populations'] = (
            [{'slug': s['slug'], 'name': s['name']} for s in settings.ANNOTATOR_REFERENCE_POPULATIONS] +
            [{'slug': s.slug, 'name': s.name} for s in self.private_reference_populations.all()]
        )
        d['phenotypes'] = [p.toJSON() for p in self.get_phenotypes()]
        d['tags'] = [t.toJSON() for t in self.get_tags()]
        # this is an egrigious hack because get_default_variant_filters returns something other than VariantFilter objects
        filters = self.get_default_variant_filters()
        for f in filters:
            f['variant_filter'] = f['variant_filter'].toJSON()
        d['default_variant_filters'] = filters
        return json.dumps(d)

    def get_phenotypes(self):
        return self.projectphenotype_set.all()

    def get_project_phenotypes_json(self):
        d = [phenotype.toJSON() for phenotype in self.get_phenotypes()]
        return json.dumps(d)

    def get_gene_lists(self):
        return list(self.gene_lists.all())

    def get_gene_list_map(self):
        d = defaultdict(list)
        for gene_list in self.get_gene_lists():
            for gene_id in gene_list.gene_id_list():
                d[gene_id].append(gene_list)
        return d

    def get_individuals(self):
        return self.individual_set.all().order_by('family__family_id')

    def num_individuals(self):
        return self.individual_set.count()

    def get_all_vcf_files(self):
        vcf_files = set()
        for indiv in self.get_individuals():
            for vcf_file in indiv.get_vcf_files():
                vcf_files.add(vcf_file)
        return vcf_files

    def num_saved_variants(self):
        search_flags = FamilySearchFlag.objects.filter(family__project=self)
        return len({(v.xpos, v.ref, v.alt, v.family) for v in search_flags})

    def get_xfamilygroup(self, only_combined=True):
        """
        Get an xbrowse FamilyGroup from the families in this project
        only_combined means only consider families that have at least one aff and unaff (with variant data)
        TODO: what is a better name for only_combined?!?!?
        """
        families = [f for f in self.get_families() if f.has_aff_and_unaff()]
        return XFamilyGroup([family.xfamily() for family in families])

    def is_loaded(self):
        for family in self.get_families():
            if not family.is_loaded():
                return False
        for cohort in self.get_cohorts():
            if cohort.is_loaded():
                return False
        return True

    def get_tags(self):
        return self.projecttag_set.all().order_by('order')

    def get_notes(self):
        return self.variantnote_set.all()

    def get_default_variant_filters(self):
        return get_default_variant_filters(self.get_reference_population_slugs())

    def set_accessed(self):
        self.last_accessed_date = timezone.now()
        self.save()

    def get_elasticsearch_index(self):
        for vcf_file in self.vcffile_set.order_by('-pk'):
            if vcf_file.elasticsearch_index is not None:
                return vcf_file.elasticsearch_index

        return None


class ProjectGeneList(models.Model):
    gene_list = models.ForeignKey('gene_lists.GeneList')
    project = models.ForeignKey(Project)


ANALYSIS_STATUS_CHOICES = (
    ('S', ('Solved', 'fa-check-square-o')),
    ('S_kgfp', ('Solved - known gene for phenotype', 'fa-check-square-o')),
    ('S_kgdp', ('Solved - gene linked to different phenotype', 'fa-check-square-o')),
    ('S_ng', ('Solved - novel gene', 'fa-check-square-o')),
    ('Sc_kgfp', ('Strong candidate - known gene for phenotype', 'fa-check-square-o')),
    ('Sc_kgdp', ('Strong candidate - gene linked to different phenotype', 'fa-check-square-o')),
    ('Sc_ng', ('Strong candidate - novel gene', 'fa-check-square-o')),
    ('Rcpc', ('Reviewed, currently pursuing candidates', 'fa-check-square-o')),
    ('Rncc', ('Reviewed, no clear candidate', 'fa-check-square-o')),
    ('I', ('Analysis in Progress', 'fa-square-o')),
    ('Q', ('Waiting for data', 'fa-clock-o')),
)


class Family(models.Model):

    project = models.ForeignKey(Project, null=True, blank=True)
    family_id = models.CharField(max_length=140, default="", blank=True)
    family_name = models.CharField(max_length=140, default="", blank=True)  # what is the difference between family name and id?

    short_description = models.TextField(default="", blank=True)

    about_family_content = models.TextField(default="", blank=True)
    analysis_summary_content = models.TextField(default="", blank=True)

    pedigree_image = models.ImageField(upload_to='pedigree_images', null=True, blank=True)
    pedigree_image_height = models.IntegerField(default=0, blank=True, null=True)
    pedigree_image_width = models.IntegerField(default=0, blank=True, null=True)

    analysis_status = models.CharField(max_length=10,
        choices=[(s[0], s[1][0]) for s in ANALYSIS_STATUS_CHOICES],
        default="Q")
    analysis_status_date_saved = models.DateTimeField(null=True, blank=True)
    analysis_status_saved_by = models.ForeignKey(User, null=True, blank=True)

    internal_analysis_status = models.CharField(max_length=10,
        choices=[(s[0], s[1][0]) for s in ANALYSIS_STATUS_CHOICES], null=True, blank=True)  # analysis status that's only visible to staff

    causal_inheritance_mode = models.CharField(max_length=20, default="unknown")

    internal_case_review_notes = models.TextField(default="", blank=True, null=True)
    internal_case_review_summary = models.TextField(default="", blank=True, null=True)

    coded_phenotype = models.TextField(default="", blank=True, null=True)
    post_discovery_omim_number = models.TextField(default="", blank=True, null=True)

    # temporary field for storing metadata on the one or more families that were combined into this one
    combined_families_info = models.TextField(default="", blank=True)
    seqr_family = models.ForeignKey('seqr.Family', null=True, blank=True, on_delete=models.SET_NULL)  # simplifies migration to new seqr.models schema

    def __unicode__(self):
        return self.family_name if self.family_name != "" else self.family_id

    def toJSON(self):
        """
        Yet another encoder. This is preferred from now on - does not include individual data
        """
        return {
            'project_id': self.project.project_id,
            'family_id': self.family_id,
            'family_name': self.family_name,
            'analysis_status': self.get_analysis_status_json(),
        }

    # REMOVE
    def get_json_obj(self):

        return {
            'project_id': self.project.project_id,
            'family_id': self.family_id,
            'individuals': [i.get_json_obj() for i in self.get_individuals()],
            'family_name': self.family_name,
            'about_family_content': self.about_family_content,
            'analysis_summary_content': self.analysis_summary_content,
            'data_status': self.get_analysis_status_json(),
        }

    def get_meta_json_obj(self):
        return {
            'project_id': self.project.project_id,
            'family_id': self.family_id,
            'about_family_content': self.about_family_content,
            'analysis_summary_content': self.analysis_summary_content,
            'analysis_status': self.get_analysis_status_json(),
            'phenotypes': list({p.name for p in ProjectPhenotype.objects.filter(individualphenotype__individual__family=self, individualphenotype__boolean_val=True)}),
        }

    def get_json(self):
        return json.dumps(self.get_json_obj())

    def get_individuals(self):
        return list(self.individual_set.all().order_by('indiv_id'))

    def individual_map(self):
        return {i.indiv_id: i.to_dict() for i in self.individual_set.all()}

    def indiv_id_list(self):
        """
        List of indiv ids for members in family
        """
        return [ i.indiv_id for i in self.individual_set.all()]

    def can_edit(self, user):
        return self.project.can_edit(user)

    def can_view(self, user):
        return self.project.can_view(user)

    def num_individuals(self):
        return self.individual_set.all().count()

    def xfamily(self):
        individuals = [i.xindividual() for i in self.get_individuals_with_variant_data()]
        return XFamily(self.family_id, individuals, project_id=self.project.project_id)

    def get_data_status(self):
        if not self.has_variant_data():
            return 'no_variants'
        elif not get_datastore(self.project).family_exists(self.project.project_id, self.family_id):
            return 'not_loaded'
        else:
            return get_datastore(self.project).get_family_status(self.project.project_id, self.family_id)

    def get_analysis_status_json(self):
        return {
            "user" : str(self.analysis_status_saved_by.profile or self.analysis_status_saved_by.email or self.analysis_status_saved_by.username) if self.analysis_status_saved_by is not None else None,
            "date_saved": pretty.date(self.analysis_status_date_saved) if self.analysis_status_date_saved is not None else None,
            "status": self.analysis_status,
            "family": self.family_name,
            "analysed_by": [ab.toJSON() for ab in self.analysedby_set.all()],
        }

    def get_vcf_files(self):
        return list(set([v for i in self.individual_set.all() for v in i.vcf_files.all()]))

    #
    # Data for this family
    #

    def has_variant_data(self):
        """
        Can we do family variant analyses on this family
        So True if any of the individuals have any variant data
        """
        return any(individual.has_variant_data() for individual in self.get_individuals())


    def has_breakpoint_data(self):
        """
        True if any of the individuals has breakpoint data
        """
        if self.project.breakpointfile_set.count() == 0:
            return False

        return any(individual.has_breakpoint_data() for individual in self.get_individuals())

    def in_case_review(self):
        return any(individual.case_review_status == 'I' for individual in self.get_individuals())

    def num_individuals_with_read_data(self):
        """Number of individuals in this family that have bams available"""
        return sum(1 for individual in self.get_individuals() if individual.has_read_data())

    def has_read_data(self):
        """Whether any individuals in this family have bam paths available"""
        return any(individual.has_variant_data() for individual in self.get_individuals())

    def all_individuals_have_variant_data(self):
        return all(individual.has_variant_data() for individual in self.get_individuals())

    def num_individuals_with_variant_data(self):
        return sum(i.has_variant_data() for i in self.get_individuals())

    def get_individuals_with_variant_data(self):
        return [i for i in self.get_individuals() if i.has_variant_data()]

    def indiv_ids_with_variant_data(self):
        return [i.indiv_id for i in self.get_individuals_with_variant_data()]

    def has_coverage_data(self):
        for individual in self.get_individuals():
            if not individual.coverage_file:
                return False
        return True

    def has_cnv_data(self):
        for individual in self.get_individuals():
            if not individual.exome_depth_file:
                return False
        return True

    def is_loaded(self):
        return self.get_data_status() in ['loaded', 'no_variants']

    def num_saved_variants(self):
        search_flags = FamilySearchFlag.objects.filter(family=self)
        return len({(v.xpos, v.ref, v.alt) for v in search_flags})

    def num_causal_variants(self):
        return CausalVariant.objects.filter(family=self).count()


    def get_phenotypes(self):
        return list(set(ProjectPhenotype.objects.filter(individualphenotype__individual__family=self, individualphenotype__boolean_val=True)))

    def has_aff_and_unaff(self):
        """
        Does this family contain at least one affected and at least one unaffected individual? (With phenotype data)
        """
        indivs = self.indiv_ids_with_variant_data()
        return any(i for i in indivs if i.affected == 'A') and any(i for i in indivs if i.affected == 'N')

    def has_data(self, data_key):
        """
        Is data for data_key available and fully loaded for this family?
        """
        if data_key == 'variation':
            return self.has_variant_data() and self.get_data_status() == 'loaded'
        elif data_key == 'breakpoints':
            log.info("checking for breakpoints")
            return self.has_breakpoint_data()
        elif data_key == 'exome_coverage':
            if self.has_coverage_data() is False:
                return False
            sample_ids = [indiv.get_coverage_store_id() for indiv in self.get_individuals()]
            statuses = set(get_coverage_store().get_sample_statuses(sample_ids).values())

            # must be at least one fully loaded
            if 'loaded' not in statuses:
                return False

            # "there are no statuses other than loaded and None"
            return len(statuses.union({'loaded', None})) == 2

    def get_data_summary(self):
        data_summary = {
            'data_available': []
        }
        if self.has_coverage_data():
            data_summary['data_available'].append('callability')
        if self.has_variant_data():
            data_summary['data_available'].append('variants')
        if self.has_cnv_data():
            data_summary['data_available'].append('cnv')
        return data_summary

    def get_image_slides(self):
        return [{'url': i.image.url, 'caption': i.caption} for i in self.familyimageslide_set.all()]

    def get_tags(self):
        return self.project.get_variant_tags(family=self)

    def get_elasticsearch_index(self):
        for vcf_file in self.get_vcf_files():
            if vcf_file.elasticsearch_index is not None:
                return vcf_file.elasticsearch_index

        return None


class FamilyImageSlide(models.Model):
    family = models.ForeignKey(Family)
    image = models.ImageField(upload_to='family_image_slides', null=True, blank=True)
    order = models.FloatField(default=0.0)
    caption = models.CharField(max_length=300, default="", blank=True)


class Cohort(models.Model):
    project = models.ForeignKey(Project, null=True, blank=True)
    cohort_id = models.CharField(max_length=140, default="", blank=True)
    display_name = models.CharField(max_length=140, default="", blank=True)
    short_description = models.CharField(max_length=140, default="", blank=True)

    individuals = models.ManyToManyField('base.Individual')

    variant_stats_json = models.TextField(default="", blank=True)

    def __unicode__(self):
        return self.display_name if self.display_name != "" else self.cohort_id

    def get_individuals(self):
        return list(self.individuals.all().order_by('indiv_id'))

    # REMOVE
    def get_json_obj(self):

        return {
            'project_id': self.project.project_id,
            'cohort_id': self.cohort_id,
            'individuals': [i.get_json_obj() for i in self.individuals.all()],
        }

    def get_json(self):
        return json.dumps(self.get_json_obj())

    def individual_map(self):
        return {i.indiv_id: i.to_dict() for i in self.individuals.all()}

    def indiv_id_list(self):
        """
        List of indiv ids for members in family
        """
        return [ i.indiv_id for i in self.individuals.all() ]

    def can_edit(self, user):

        return self.project.can_edit(user)

    def can_view(self, user):
        return self.project.can_view(user)

    def num_individuals(self):
        return self.individuals.all().count()

    def xfamily(self):
        individuals = [i.xindividual() for i in self.individuals.all()]
        return XFamily(self.cohort_id, individuals, project_id=self.project.project_id)

    def xcohort(self):
        individuals = [i.xindividual() for i in self.individuals.all()]
        return XCohort(self.cohort_id, individuals, project_id=self.project.project_id)

    def get_vcf_files(self):
        vcf_files = { f for i in self.individuals.all() for f in i.get_vcf_files() }
        return list(vcf_files)

    #
    # Data lookups
    #

    def has_variant_data(self):
        """
        Can we do cohort variant analyses
        So all individuals must have variant data
        """
        return all(individual.has_variant_data() for individual in self.get_individuals())

    def get_data_status(self):
        if not self.has_variant_data():
            return 'no_variants'
        elif not get_datastore(self.project).family_exists(self.project.project_id, self.cohort_id):
            return 'not_loaded'
        else:
            return get_datastore(self.project).get_family_status(self.project.project_id, self.cohort_id)

    def is_loaded(self):
        return self.get_data_status() in ['loaded', 'no_variants']


GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('U', 'Unknown'),
)


AFFECTED_CHOICES = (
    ('A', 'Affected'),
    ('N', 'Unaffected'),
    ('U', 'Unknown'),
)

COVERAGE_STATUS_CHOICES = (
    ('S', 'In Sequencing'),
    ('I', 'Interim'),
    ('C', 'Complete'),
    ('A', 'Abandoned'),
)

CASE_REVIEW_STATUS_CHOICES = (
    ('N', 'Not In Review'),
    ('I', 'In Review'),
    ('U', 'Uncertain'),
    ('A', 'Accepted'),
    ('R', 'Not Accepted'),
    ('Q', 'More Info Needed'),
    ('P', 'Pending Results and Records'),
    ('W', 'Waitlist'),
    ('WD', 'Withdrew'),
    ('IE', 'Ineligible'),
    ('DP', 'Declined to Participate'),
)

CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS = (
    ('A', 'Array'),   # allow multiple-select. No selection = Platform Uncertain
    ('E', 'Exome'),
    ('G', 'Genome'),
    ('R', 'RNA-seq'),
    ('S', 'Store DNA'),
    ('P', 'Reprocess'),
)


class Individual(models.Model):
    # metadata tags
    created_date = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    # global unique id for this individual (<date>_<time_with_millisec>_<indiv_id>)
    project = models.ForeignKey(Project, null=True, blank=True)  # move to family only ?
    family = models.ForeignKey(Family, null=True, blank=True)

    indiv_id = models.SlugField(max_length=140, default="", blank=True, db_index=True)
    maternal_id = models.SlugField(max_length=140, default="", blank=True)
    paternal_id = models.SlugField(max_length=140, default="", blank=True)

    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')  # => sex
    affected = models.CharField(max_length=1, choices=AFFECTED_CHOICES, default='U')

    nickname = models.CharField(max_length=140, default="", blank=True)
    other_notes = models.TextField(default="", blank=True, null=True)

    case_review_status = models.CharField(max_length=2, choices=CASE_REVIEW_STATUS_CHOICES, blank=True, null=True, default='')
    case_review_status_accepted_for = models.CharField(max_length=10, null=True, blank=True)
    case_review_status_last_modified_date = models.DateTimeField(null=True, blank=True, db_index=True)
    case_review_status_last_modified_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.SET_NULL)
    case_review_discussion = models.TextField(null=True, blank=True)

    phenotips_patient_id = models.CharField(max_length=30, null=True, blank=True, db_index=True)    # PhenoTips internal id
    phenotips_id = models.SlugField(max_length=165, default="", blank=True, db_index=True)  # PhenoTips 'external id'
    phenotips_data = models.TextField(default="", null=True, blank=True)

    # to be moved to sample-specific record
    mean_target_coverage = models.FloatField(null=True, blank=True)
    coverage_status = models.CharField(max_length=1, choices=COVERAGE_STATUS_CHOICES, default='S')
    vcf_id = models.CharField(max_length=40, default="", blank=True)  # ID in VCF files, if different (rename => variant_callset_sample_id)

    in_case_review = models.BooleanField(default=False)

    bam_file_path = models.TextField(default="", blank=True)
    coverage_file = models.TextField(default="", blank=True)
    cnv_bed_file = models.TextField(default="", blank=True)  # copy number variants
    exome_depth_file = models.TextField(default="", blank=True)

    vcf_files = models.ManyToManyField(VCFFile, blank=True)

    #phenotips_last_modified_by = models.ForeignKey(User, null=True, blank=True)
    #phenotips_last_modified_date = models.TextField(default="", null=True, blank=True)

    # temporary field for storing metadata on the one or more individuals that were combined into this one
    combined_individuals_info = models.TextField(default="", blank=True)
    seqr_individual = models.ForeignKey('seqr.Individual', null=True, blank=True, on_delete=models.SET_NULL)  # simplifies migration to new seqr.models schema

    def __unicode__(self):
        ret = self.indiv_id
        if self.nickname:
            ret += " (%s)" % self.nickname
        return ret

    def save(self, *args, **kwargs):
        """Override the default save method so that guid is set whenever a new Individual record is created"""

        being_created = not self.pk
        if being_created:
            self.created_date = timezone.now()
            # generate the global unique id for this individual (<date>_<time>_<microsec>_<indiv_id>)

            self.phenotips_id = timezone.now().strftime("%Y%m%d_%H%M%S_%f_") + unicode(self.indiv_id).encode('utf-8')

        super(Individual, self).save(*args, **kwargs)

    def get_family_id(self):
        if self.family:
            return self.family.family_id
        else:
            return None

    def has_variant_data(self):
        return self.vcf_files.all().count() > 0

    def has_breakpoint_data(self):
        return self.breakpoint_set.count() > 0

    def has_read_data(self):
        return bool(self.bam_file_path)

    def gender_display(self):
        return dict(GENDER_CHOICES).get(self.gender, '')

    def affected_status_display(self):  # TODO: rename this to affected_display...that was dumb
        return dict(AFFECTED_CHOICES).get(self.affected, '')

    def phenotypes(self):
        return [t.phenotype_slug for t in self.individualphenotypetag_set.all()]

    def to_dict(self):
        """

        """
        return {
            'indiv_id': str(self.indiv_id),
            'project_id': str(self.project.project_id),
            'family_id': str(self.family.family_id) if self.family else "",
            'nickname': str(self.nickname),
            'gender': str(self.gender),
            'affected': str(self.affected),
            'maternal_id': str(self.maternal_id),
            'paternal_id': str(self.paternal_id),
            'in_case_review': self.case_review_status == 'I',
            'case_review_status': str(self.case_review_status),
            'has_variants': self.has_variant_data(),  # can we remove?
            'phenotypes': self.get_phenotype_dict(),
            'other_notes': self.other_notes,
        }

    def get_json_obj(self):
        return {
            'project_id': self.project.project_id,
            'indiv_id': self.indiv_id,
            'gender': self.gender,
            'affected': self.affected,
            'nickname': self.nickname,
            'has_variant_data': self.has_variant_data(),
            'read_data_is_available': bool(self.bam_file_path),
            'cnv_bed_file': self.cnv_bed_file,
            'read_data_format': None if not bool(self.bam_file_path) else ("cram" if self.bam_file_path.endswith(".cram") else "bam"),
            'family_id': self.get_family_id(),
        }

    def get_json(self):
        return json.dumps(self.get_json_obj())

    def xindividual(self):

        gender = 'unknown'
        if self.gender == 'M':
            gender = 'male'
        elif self.gender == 'F':
            gender = 'female'

        affected_status = 'unknown'
        if self.affected == 'A':
            affected_status = 'affected'
        elif self.affected == 'N':
            affected_status = 'unaffected'

        paternal_id = self.paternal_id
        if not Individual.objects.filter(indiv_id=paternal_id, project=self.project).exists():
            paternal_id = '.'

        maternal_id = self.maternal_id
        if not Individual.objects.filter(indiv_id=maternal_id, project=self.project).exists():
            maternal_id = '.'

        return XIndividual(
            self.indiv_id,
            project_id=self.project_id,
            family_id=self.family_id,
            paternal_id=paternal_id,
            maternal_id=maternal_id,
            gender=gender,
            affected_status=affected_status
        )

    def from_xindividual(self, xindividual):
        """
        Load other fields from xindiviudal object
        Ignores project_id, family_id, indiv_id - those should already be set
        """
        self.paternal_id = xindividual.paternal_id
        self.maternal_id = xindividual.maternal_id
        self.affected = 'A' if xindividual.affected_status == 'affected' else ('N' if xindividual.affected_status == 'unaffected' else 'U')
        self.gender = 'M' if xindividual.gender == 'male' else ('F' if xindividual.gender == 'female' else 'U')
        self.save()

    def get_vcf_files(self):
        """
        List of VCF file (paths) that this individual is in
        """
        return list(self.vcf_files.all())

    def get_cohorts(self):
        """
        List of Cohorts (if any) that this sample belongs to
        """
        return self.cohort_set.all()

    def get_phenotypes(self):
        return [i for i in self.individualphenotype_set.all() if i.val() is not None]

    def get_phenotype_dict(self):
        return {p.phenotype.slug: p.val() for p in self.get_phenotypes()}

    def phenotype_display(self, slug):
        pk = int(slug[6:])
        iphenotype = self.individualphenotype_set.filter(phenotype__pk=pk)
        if len(iphenotype) == 0:
            return ""
        iphenotype = iphenotype[0]
        if iphenotype.phenotype.datatype == 'bool':
            if iphenotype.boolean_val is True:
                return 'True'
            elif iphenotype.boolean_val is False:
                return 'False'
            else:
                return '.'

    def sample_display(self):
        if self.vcf_files.count() == 0:
            return "No variant data"
        else:
            s = "%d sample" % self.vcf_files.count()
            if self.vcf_files.count() > 1:
                s += "s"
            return s

    def is_loaded(self):
        return self.family.is_loaded()

    def has_coverage_data(self):
        return bool(self.coverage_file)

    # TODO: rename this to something more generic
    def get_coverage_store_id(self):
        return str(self.pk)

    def data(self):
        return {
            'exome_coverage': self.has_coverage_data(),
            'variants': self.has_variant_data(),
        }


FLAG_TYPE_CHOICES = (
    ('C', 'Likely causal'),
    ('R', 'Flag for review'),
    ('N', 'Other note'),
)


class FamilySearchFlag(models.Model):

    user = models.ForeignKey(User, null=True, blank=True)
    family = models.ForeignKey(Family, null=True, blank=True)

    xpos = models.BigIntegerField()
    ref = models.TextField()
    alt = models.TextField()

    flag_type = models.CharField(max_length=1, choices=FLAG_TYPE_CHOICES)
    suggested_inheritance = models.SlugField(max_length=40, default="")

    # REMOVE
    search_spec_json = models.TextField(default="", blank=True)
    date_saved = models.DateTimeField()
    note = models.TextField(default="", blank=True)

    def search_spec(self):
        return json.loads(self.search_spec_json)

    def to_dict(self):
        return {
            'username': self.user.username,
            'display_name': self.user.profile.display_name,
            'project_id': self.family.project.project_id,
            'family_id': self.family.family_id,
            'xpos': self.xpos,
            'ref': self.ref,
            'alt': self.alt,
            'flag_type': self.flag_type,
            'flag_type_display': dict(FLAG_TYPE_CHOICES).get(self.flag_type),
            'search_spec_json': self.search_spec_json,
            'note': self.note,
            'date_saved': pretty.date(self.date_saved) if self.date_saved is not None else '',
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def x_variant(self):
        v = get_datastore(self.family.project).get_single_variant(self.family.project.project_id, self.family.family_id, self.xpos, self.ref, self.alt)
        return v


class ProjectPhenotype(models.Model):

    project = models.ForeignKey(Project)
    slug = models.SlugField(max_length=140, default="pheno")
    name = models.CharField(max_length=140, default="")
    category = models.CharField(choices=PHENOTYPE_CATEGORIES, max_length=20)
    datatype = models.CharField(choices=PHENOTYPE_DATATYPES, max_length=20)

    def __unicode__(self):
        return "{} in {}".format(self.name, self.project)

    def toJSON(self):
        return {
            'slug': self.slug,
            'name': self.name,
            'category': self.category,
            'datatype': self.datatype,
        }


class IndividualPhenotype(models.Model):

    individual = models.ForeignKey(Individual)
    phenotype = models.ForeignKey(ProjectPhenotype)
    boolean_val = models.NullBooleanField()
    float_val = models.FloatField(null=True, blank=True)

    def slug(self):
        return self.phenotype.slug

    def val(self):
        if self.phenotype.datatype == 'bool':
            return self.boolean_val
        elif self.phenotype.datatype == 'number':
            return self.float_val


class FamilyGroup(models.Model):
    slug = models.SlugField(max_length=100)
    name = models.CharField(max_length=100)
    description = models.TextField()
    project = models.ForeignKey(Project)
    families = models.ManyToManyField(Family)

    def __unicode__(self):
        return self.name

    def get_families(self):
        return self.families.all().order_by('family_id')

    def num_families(self):
        return self.families.count()

    def xfamilygroup(self):
        return XFamilyGroup([family.xfamily() for family in self.get_families()])

    def toJSON(self):
        return {
            'project_id': self.project.project_id,
            'slug': self.slug,
            'name': self.name,
            'description': self.description,
            'families': {family.family_id: family.get_json_obj() for family in self.get_families()}
        }


class ProjectTag(models.Model):
    project = models.ForeignKey(Project)
    tag = models.TextField()
    category = models.TextField(default="")
    title = models.TextField(default="")  # aka. description
    color = models.CharField(max_length=10, default="")
    order = models.FloatField(null=True)

    seqr_variant_tag_type = models.ForeignKey('seqr.VariantTagType', null=True, blank=True, on_delete=models.SET_NULL)  # simplifies migration to new seqr.models schema

    def save(self, *args, **kwargs):
        if self.color == '':
            self.color = random.choice([
                '#a6cee3',
                '#1f78b4',
                '#b2df8a',
                '#33a02c',
                '#fdbf6f',
                '#ff7f00',
                '#ff0000',
                '#cab2d6',
                '#6a3d9a',
                '#8F754F',
                '#383838',
            ])
        super(ProjectTag, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title if self.title else self.tag

    def toJSON(self):
        return {
            'project': self.project.project_id,
            'tag': self.tag,
            'title': self.title,
            'color': self.color,
            'category': self.category,
        }

    def get_variant_tags(self, family=None):
        if family is not None:
            return self.varianttag_set.filter(family=family)
        else:
            return self.varianttag_set.all()


class CausalVariant(models.Model):
    family = models.ForeignKey(Family, null=True)
    variant_type = models.CharField(max_length=10, default="")
    xpos = models.BigIntegerField(null=True)
    ref = models.TextField(null=True)
    alt = models.TextField(null=True)


class VariantTag(models.Model):
    project_tag = models.ForeignKey(ProjectTag)

    user = models.ForeignKey(User, null=True, blank=True)
    date_saved = models.DateTimeField(null=True)

    family = models.ForeignKey(Family, null=True)
    xpos = models.BigIntegerField()
    ref = models.TextField()
    alt = models.TextField()

    search_url = models.TextField(null=True)

    seqr_variant_tag = models.ForeignKey('seqr.VariantTag', null=True, blank=True, on_delete=models.SET_NULL)  # simplifies migration to new seqr.models schema

    def __str__(self):
        chrom, pos = genomeloc.get_chr_pos(self.xpos)
        return "%s-%s-%s-%s:%s" % (chrom, pos, self.ref, self.alt, self.project_tag.tag)

    def to_variant_json(self):
        return {
            'user': {
                'username': self.user.username,
                'display_name': str(self.user.profile),
             } if self.user else None,
            'date_saved': pretty.date(self.date_saved) if self.date_saved is not None else '',
            'tag': self.project_tag.tag,
            'color': self.project_tag.color,
            'search_url': self.search_url,
        }


class VariantNote(models.Model):
    project = models.ForeignKey(Project)
    note = models.TextField(default="", blank=True)
    submit_to_clinvar = models.BooleanField(default=False)

    xpos = models.BigIntegerField()
    ref = models.TextField()
    alt = models.TextField()

    # these are for context - if note was saved for a family or an individual
    family = models.ForeignKey(Family, null=True, blank=True)
    individual = models.ForeignKey(Individual, null=True, blank=True)

    user = models.ForeignKey(User, null=True, blank=True)
    date_saved = models.DateTimeField()
    search_url = models.TextField(null=True)

    seqr_variant_note = models.ForeignKey('seqr.VariantNote', null=True, blank=True, on_delete=models.SET_NULL)  # simplifies migration to new seqr.models schema

    def get_context(self):
        if self.family:
            return 'family', self.family
        elif self.individual:
            return 'individual', self.individual
        else:
            return 'project', self.project

    def toJSON(self):
        d = {
            'user': {
                'username': self.user.username,
                'display_name': str(self.user.profile),
            } if self.user else None,
            'date_saved': pretty.date(self.date_saved) if self.date_saved is not None else '',

            'project_id': self.project.project_id,
            'note_id' : self.id,
            'note': self.note,
            'submit_to_clinvar': self.submit_to_clinvar,

            'xpos': self.xpos,
            'ref': self.ref,
            'alt': self.alt,

            'family_id': None,
            'individual_id': None,
        }
        context, obj = self.get_context()
        if context == 'family':
            d['family_id'] = obj.family_id
        elif context == 'individual':
            d['individual_id'] = obj.indiv_id

        return d


class GeneNote(models.Model):
    note = models.TextField(default="", blank=True)
    gene_id = models.CharField(max_length=20)  # ensembl ID
    user = models.ForeignKey(User, null=True, blank=True)
    date_saved = models.DateTimeField()

    def toJSON(self, user=None):
        return {
            'user': {
                'username': self.user.username,
                'display_name': str(self.user.profile),
            } if self.user else None,
            'date_saved': pretty.date(self.date_saved) if self.date_saved is not None else '',
            'gene_id': self.gene_id,
            'note_id': self.id,
            'note': self.note,
            'editable': user and self.can_edit(user)
        }

    def can_edit(self, user):
        if user.is_staff:
            return True
        else:
            return self.user == user


class AnalysisStatus(models.Model):
    user = models.ForeignKey(User, null=True, blank=True)
    date_saved = models.DateTimeField(null=True)
    family = models.ForeignKey(Family)
    status = models.CharField(max_length=10, choices=ANALYSIS_STATUS_CHOICES, default="I")


class AnalysedBy(models.Model):
    user = models.ForeignKey(User)
    date_saved = models.DateTimeField()
    family = models.ForeignKey(Family)

    def toJSON(self):
        return {
            'user': {
                'username': self.user.username,
                'display_name': str(self.user.profile),
            },
            'date_saved': pretty.date(self.date_saved),
        }
