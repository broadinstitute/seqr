import json
import datetime
from collections import defaultdict
import gzip
import random

from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import utc
from django.conf import settings

from pretty_times import pretty
from xbrowse import vcf_stuff
from xbrowse import Individual as XIndividual
from xbrowse import Family as XFamily
from xbrowse import Cohort as XCohort
from xbrowse import FamilyGroup as XFamilyGroup


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

    file_path = models.CharField(max_length=500, default="", blank=True)
    needs_reannotate = models.BooleanField(default=False)

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

    @staticmethod
    def get_annotator_spec():
        return [p.to_dict() for p in ReferencePopulation.objects.all()]


COLLABORATOR_TYPES = (
    ('manager', 'Manager'),
    ('collaborator', 'Collaborator'),
)


class ProjectCollaborator(models.Model):
    user = models.ForeignKey(User)
    project = models.ForeignKey('base.Project')
    collaborator_type = models.CharField(max_length=20, choices=COLLABORATOR_TYPES, default="collaborator")


class Project(models.Model): 
    
    # these are auto populated from xbrowse
    project_id = models.SlugField(max_length=140, default="", blank=True, unique=True)

    # these are user specified; only exist in the server
    project_name = models.CharField(max_length=140, default="", blank=True)
    description = models.TextField(blank=True, default="")
    is_public = models.BooleanField(default=False)

    private_reference_populations = models.ManyToManyField(ReferencePopulation, null=True, blank=True)
    gene_lists = models.ManyToManyField('gene_lists.GeneList', through='ProjectGeneList')

    # users
    collaborators = models.ManyToManyField(User, null=True, blank=True, through='ProjectCollaborator')

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

    def set_as_collaborator(self, user):
        ProjectCollaborator.objects.get_or_create(user=user, project=self)

    def get_managers(self):
        return [c.user for c in ProjectCollaborator.objects.filter(project=self, collaborator_type="manager")]

    def get_collaborators(self):
        return [c.user for c in ProjectCollaborator.objects.filter(project=self, collaborator_type="collaborator")]

    def get_users(self):
        return [(c.user, c.collaborator_type) for c in ProjectCollaborator.objects.filter(project=self)]

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
            if len(vcf_files) == 1:
                vcf = vcf_files[0].path()
                if vcf not in families_by_vcf:
                    families_by_vcf[vcf] = []
                families_by_vcf[vcf].append(family)
        return families_by_vcf

    def cohorts_by_vcf(self):
        by_vcf = {}  # map of vcf_file -> list of families from that VCF
        for cohort in self.cohort_set.all():
            vcf_files = cohort.get_vcf_files()
            if len(vcf_files) == 1:
                vcf = vcf_files[0].path()
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
        return settings.ANNOTATOR.reference_population_slugs + self.private_reference_population_slugs()

    def get_options_json(self):
        d = dict(project_id=self.project_id)

        d['reference_populations'] = (
            [{'slug': s['slug'], 'name': s['name']} for s in settings.ANNOTATOR.reference_populations] +
            [{'slug': s.slug, 'name': s.name} for s in self.private_reference_populations.all()]
        )
        d['phenotypes'] = [p.toJSON() for p in self.get_phenotypes()]
        d['bam_file_urls'] = {indiv.indiv_id: indiv.bam_file.get_url() for indiv in self.get_individuals() if indiv.bam_file}
        d['tags'] = [t.toJSON() for t in self.get_tags()]
        return json.dumps(d)

    def get_phenotypes(self):
        return self.projectphenotype_set.all()

    def get_project_phenotypes_json(self):
        d = [phenotype.toJSON() for phenotype in self.get_phenotypes()]
        return json.dumps(d)

    def get_gene_lists(self):
        return self.gene_lists.all()

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
        return self.projecttag_set.all()


class ProjectGeneList(models.Model):
    gene_list = models.ForeignKey('gene_lists.GeneList')
    project = models.ForeignKey(Project)


ANALYSIS_STATUS_CHOICES = (
    ('S', 'Solved'),
    ('I', 'In Progress'),
    ('Q', 'Waiting for data')
)


class Family(models.Model): 

    project = models.ForeignKey(Project, null=True, blank=True)
    family_id = models.CharField(max_length=140, default="", blank=True)

    # server only
    family_name = models.CharField(max_length=140, default="", blank=True)
    short_description = models.CharField(max_length=500, default="", blank=True)
    about_family_content = models.TextField(default="", blank=True)
    pedigree_image = models.ImageField(upload_to='pedigree_images', null=True, blank=True,  
        height_field='pedigree_image_height', width_field='pedigree_image_width')
    pedigree_image_height = models.IntegerField(default=0, blank=True)
    pedigree_image_width = models.IntegerField(default=0, blank=True)

    analysis_status = models.CharField(max_length=1, choices=ANALYSIS_STATUS_CHOICES, default="I")
    causal_inheritance_mode = models.CharField(max_length=20, default="unknown")

    # Other postprocessing
    relatedness_matrix_json = models.TextField(default="", blank=True)
    variant_stats_json = models.TextField(default="", blank=True)

    # QC stuff
    has_before_load_qc_error = models.BooleanField(default=False)
    before_load_qc_json = models.TextField(default="", blank=True)

    has_after_load_qc_error = models.BooleanField(default=False)
    after_load_qc_json = models.TextField(default="", blank=True)

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
            'analysis_status': self.analysis_status,
        }

    # REMOVE
    def get_json_obj(self):

        return {
            'project_id': self.project.project_id,
            'family_id': self.family_id,
            'individuals': [i.get_json_obj() for i in self.get_individuals()],
            'family_name': self.family_name,
            'about_family_content': self.about_family_content,
        }

    def get_meta_json_obj(self):
        return {
            'project_id': self.project.project_id,
            'family_id': self.family_id,
            'about_family_content': self.about_family_content,
            'analysis_status': self.analysis_status,
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
        elif not settings.DATASTORE.family_exists(self.project.project_id, self.family_id):
            return 'not_loaded'
        else:
            return settings.DATASTORE.get_family_status(self.project.project_id, self.family_id)

    def get_analysis_status(self):
        return self.analysis_status

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
        elif data_key == 'exome_coverage':
            if self.has_coverage_data() is False:
                return False
            sample_ids = [indiv.get_coverage_store_id() for indiv in self.get_individuals()]
            statuses = set(settings.COVERAGE_STORE.get_sample_statuses(sample_ids).values())

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
        elif not settings.DATASTORE.family_exists(self.project.project_id, self.cohort_id):
            return 'not_loaded'
        else:
            return settings.DATASTORE.get_family_status(self.project.project_id, self.cohort_id)

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


class Individual(models.Model): 

    indiv_id = models.SlugField(max_length=140, default="", blank=True, db_index=True)
    family = models.ForeignKey(Family, null=True, blank=True)
    project = models.ForeignKey(Project, null=True, blank=True)

    nickname = models.CharField(max_length=140, default="", blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    affected = models.CharField(max_length=1, choices=AFFECTED_CHOICES, default='U')
    maternal_id = models.SlugField(max_length=140, default="", blank=True)
    paternal_id = models.SlugField(max_length=140, default="", blank=True)

    other_notes = models.TextField(default="", blank=True, null=True)

    coverage_file = models.CharField(max_length=200, default="", blank=True)
    exome_depth_file = models.CharField(max_length=200, default="", blank=True)
    vcf_files = models.ManyToManyField(VCFFile, null=True, blank=True)
    bam_file = models.ForeignKey('datasets.BAMFile', null=True, blank=True)

    def __unicode__(self):
        ret = self.indiv_id
        if self.nickname:
            ret += " (%s)" % self.nickname
        return ret

    def get_family_id(self):
        if self.family:
            return self.family.family_id
        else:
            return None

    def has_variant_data(self):
        return self.vcf_files.all().count() > 0

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
            'has_variants': self.has_variant_data(),  # can we remove?
            'phenotypes': self.get_phenotype_dict(),
            'other_notes': self.other_notes,
        }

    # REMOVE
    def get_json_obj(self): 
        return {
            'indiv_id': self.indiv_id, 
            'gender': self.gender,
            'affected': self.affected,
            'nickname': self.nickname,
            'has_variant_data': self.has_variant_data(),
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

    def get_notes_plaintext(self):
        return self.other_notes if self.other_notes else ""

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


class DiseaseGeneList(models.Model): 

    slug = models.SlugField(max_length=40)
    title = models.CharField(max_length=140, default="", blank=True)
    list_admins = models.ManyToManyField(UserProfile, null=True, blank=True)

    def __unicode__(self): 
        return self.title if self.title != "" else self.slug

    def get_genes(self): 
        return settings.REFERENCE.get_disease_genes_for_phenotype(self.slug)

    def set_genes(self, gene_id_list): 
        settings.REFERENCE.set_disease_genes_for_phenotype(self.slug, gene_id_list)

    def is_admin(self, user): 
        return user.profile in self.list_admins.all() or user.is_staff


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
            'date_saved': pretty.date(self.date_saved.replace(tzinfo=None) + datetime.timedelta(hours=-5)),
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def x_variant(self):
        v = settings.DATASTORE.get_single_variant(self.family.project.project_id, self.family.family_id, self.xpos, self.ref, self.alt)
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


class CausalVariant(models.Model):
    family = models.ForeignKey(Family, null=True)
    variant_type = models.CharField(max_length=10, default="")
    xpos = models.BigIntegerField(null=True)
    ref = models.TextField(null=True)
    alt = models.TextField(null=True)


class ProjectTag(models.Model):
    project = models.ForeignKey(Project)
    tag = models.SlugField(max_length=50)
    title = models.CharField(max_length=300, default="")
    color = models.CharField(max_length=10, default="")

    def save(self, *args, **kwargs):
        if self.color == '':
            self.color = random.choice([
                '#a6cee3',
                '#1f78b4',
                '#b2df8a',
                '#33a02c',
                '#fb9a99',
                '#e31a1c',
                '#fdbf6f',
                '#ff7f00',
                '#cab2d6',
                '#6a3d9a',
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
        }


class VariantTag(models.Model):
    project_tag = models.ForeignKey(ProjectTag)
    family = models.ForeignKey(Family, null=True)
    xpos = models.BigIntegerField()
    ref = models.TextField()
    alt = models.TextField()
    def toJSON(self):
        d = {
            'project': self.project_tag.project.project_id,
            'tag': self.project_tag.tag,
            'title': self.project_tag.title,
            'color': self.project_tag.color,
            'xpos': self.xpos,
            'ref': self.ref,
            'alt': self.alt,
        }
        if self.family:
            d['family'] = self.family.family_id
        return d


class VariantNote(models.Model):

    user = models.ForeignKey(User, null=True, blank=True)
    date_saved = models.DateTimeField()
    project = models.ForeignKey(Project)
    note = models.TextField(default="", blank=True)

    # right now this is how we uniquely identify a variant
    xpos = models.BigIntegerField()
    ref = models.TextField()
    alt = models.TextField()

    # these are for context - if note was saved for a family or an individual
    family = models.ForeignKey(Family, null=True, blank=True)
    individual = models.ForeignKey(Individual, null=True, blank=True)

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
            },
            'date_saved': pretty.date(self.date_saved.replace(tzinfo=None) + datetime.timedelta(hours=-5)),
            'project_id': self.project.project_id,
            'note': self.note,

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
