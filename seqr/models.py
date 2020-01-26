from abc import abstractmethod
import uuid
import json
import random

from django.contrib.auth.models import User, Group
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from django.db.models import options, ForeignKey
from django.utils import timezone
from django.utils.text import slugify as __slugify

from guardian.shortcuts import assign_perm

from seqr.utils.xpos_utils import get_chrom_pos
from reference_data.models import GENOME_VERSION_GRCh37, GENOME_VERSION_CHOICES
from settings import MME_DEFAULT_CONTACT_NAME, MME_DEFAULT_CONTACT_HREF, MME_DEFAULT_CONTACT_INSTITUTION

#  Allow adding the custom json_fields and internal_json_fields to the model Meta
# (from https://stackoverflow.com/questions/1088431/adding-attributes-into-django-models-meta-class)
options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('json_fields', 'internal_json_fields',)

CAN_VIEW = 'can_view'
CAN_EDIT = 'can_edit'
IS_OWNER = 'is_owner'

_SEQR_OBJECT_PERMISSIONS = (
    (CAN_VIEW, CAN_VIEW),
    (CAN_EDIT, CAN_EDIT),
    (IS_OWNER, IS_OWNER),
)


def _slugify(text):
    # using _ instead of - makes ids easier to select, and use without quotes in a wider set of contexts
    return __slugify(text).replace('-', '_')


class ModelWithGUID(models.Model):
    MAX_GUID_SIZE = 30

    guid = models.CharField(max_length=MAX_GUID_SIZE, db_index=True, unique=True)

    created_date = models.DateTimeField(default=timezone.now, db_index=True)
    created_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    # used for optimistic concurrent write protection (to detect concurrent changes)
    last_modified_date = models.DateTimeField(null=True, blank=True,  db_index=True)

    class Meta:
        abstract = True

        json_fields = []
        internal_json_fields = []

    @abstractmethod
    def _compute_guid(self):
        """Returns a human-readable label (aka. slug) for this object with only alphanumeric
        chars, '-' and '_'. This label doesn't need to be globally unique by itself, but should not
        be null or blank, and should be globally unique when paired with this object's created-time
        in seconds.
        """

    def __unicode__(self):
        return self.guid

    def json(self):
        """Utility method that returns a json {field-name: value-as-string} mapping for all fields."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def save(self, *args, **kwargs):
        """Create a GUID at object creation time."""

        being_created = not self.pk
        current_time = timezone.now()

        # allows for overriding last_modified_date during save, but this should only be used for migrations
        self.last_modified_date = kwargs.pop('last_modified_date', current_time)

        if not being_created:
            super(ModelWithGUID, self).save(*args, **kwargs)
        else:
            # do an initial save to generate the self.pk id which is then used when computing self._compute_guid()
            # Temporarily set guid to a randint to avoid a brief window when guid="". Otherwise guid uniqueness errors
            # can occur if 2 objects are being created simultaneously and both attempt to save without setting guid.
            temp_guid = str(random.randint(10**10, 10**11))
            self.guid = kwargs.pop('guid', temp_guid)
            # allows for overriding created_date during save, but this should only be used for migrations
            self.created_date = kwargs.pop('created_date', current_time)
            super(ModelWithGUID, self).save(*args, **kwargs)

            self.guid = self._compute_guid()[:ModelWithGUID.MAX_GUID_SIZE]
            super(ModelWithGUID, self).save()


class Project(ModelWithGUID):
    name = models.TextField()  # human-readable project name
    description = models.TextField(null=True, blank=True)

    # user groups that allow Project permissions to be extended to other objects as long as
    # the user remains is in one of these groups.
    owners_group = models.ForeignKey(Group, related_name='+', on_delete=models.PROTECT)
    can_edit_group = models.ForeignKey(Group, related_name='+', on_delete=models.PROTECT)
    can_view_group = models.ForeignKey(Group, related_name='+', on_delete=models.PROTECT)

    genome_version = models.CharField(max_length=5, choices=GENOME_VERSION_CHOICES, default=GENOME_VERSION_GRCh37)

    phenotips_user_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    is_mme_enabled = models.BooleanField(default=True)
    mme_primary_data_owner = models.TextField(null=True, blank=True, default=MME_DEFAULT_CONTACT_NAME)
    mme_contact_url = models.TextField(null=True, blank=True, default=MME_DEFAULT_CONTACT_HREF)
    mme_contact_institution = models.TextField(null=True, blank=True, default=MME_DEFAULT_CONTACT_INSTITUTION)

    disable_staff_access = models.BooleanField(default=False)

    last_accessed_date = models.DateTimeField(null=True, blank=True, db_index=True)

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'R%04d_%s' % (self.id, _slugify(str(self)))

    def save(self, *args, **kwargs):
        """Override the save method and create user permissions groups + add the created_by user.

        This could be done with signals, but seems cleaner to do it this way.
        """
        being_created = not self.pk

        if being_created:
            # create user groups
            self.owners_group = Group.objects.create(name="%s_%s_%s" % (_slugify(self.name.strip())[:30], 'owners', uuid.uuid4()))
            self.can_edit_group = Group.objects.create(name="%s_%s_%s" % (_slugify(self.name.strip())[:30], 'can_edit', uuid.uuid4()))
            self.can_view_group = Group.objects.create(name="%s_%s_%s" % (_slugify(self.name.strip())[:30], 'can_view', uuid.uuid4()))

        super(Project, self).save(*args, **kwargs)

        if being_created:
            assign_perm(user_or_group=self.owners_group, perm=IS_OWNER, obj=self)
            assign_perm(user_or_group=self.owners_group, perm=CAN_EDIT, obj=self)
            assign_perm(user_or_group=self.owners_group, perm=CAN_VIEW, obj=self)

            assign_perm(user_or_group=self.can_edit_group, perm=CAN_EDIT, obj=self)
            assign_perm(user_or_group=self.can_edit_group, perm=CAN_VIEW, obj=self)

            assign_perm(user_or_group=self.can_view_group, perm=CAN_VIEW, obj=self)

            # add the user that created this Project to all permissions groups
            user = self.created_by
            if user and not user.is_staff:  # staff have access to all resources anyway
                user.groups.add(self.owners_group, self.can_edit_group, self.can_view_group)

    def delete(self, *args, **kwargs):
        """Override the delete method to also delete the project-specific user groups"""

        super(Project, self).delete(*args, **kwargs)

        self.owners_group.delete()
        self.can_edit_group.delete()
        self.can_view_group.delete()

    class Meta:
        permissions = _SEQR_OBJECT_PERMISSIONS

        json_fields = [
            'name', 'description', 'created_date', 'last_modified_date', 'genome_version', 'mme_contact_institution',
            'last_accessed_date', 'is_mme_enabled', 'mme_primary_data_owner', 'mme_contact_url', 'guid'
        ]


class ProjectCategory(ModelWithGUID):
    projects = models.ManyToManyField('Project')
    name = models.TextField(db_index=True)  # human-readable category name
    # color = models.CharField(max_length=20, default="#1f78b4")

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'PC%06d_%s' % (self.id, _slugify(str(self)))


class Family(ModelWithGUID):
    ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS='I'
    ANALYSIS_STATUS_WAITING_FOR_DATA='Q'
    ANALYSIS_STATUS_CHOICES = (
        ('S', 'Solved'),
        ('S_kgfp', 'Solved - known gene for phenotype'),
        ('S_kgdp', 'Solved - gene linked to different phenotype'),
        ('S_ng', 'Solved - novel gene'),
        ('Sc_kgfp', 'Strong candidate - known gene for phenotype'),
        ('Sc_kgdp', 'Strong candidate - gene linked to different phenotype'),
        ('Sc_ng', 'Strong candidate - novel gene'),
        ('Rcpc', 'Reviewed, currently pursuing candidates'),
        ('Rncc', 'Reviewed, no clear candidate'),
        ('C', 'Closed, no longer under analysis'),
        ('I', 'Analysis in Progress'),
        ('Q', 'Waiting for data'),
    )

    SUCCESS_STORY_TYPE_CHOICES = (
        ('N', 'Novel Discovery'),
        ('A', 'Altered Clinical Outcome'),
        ('C', 'Collaboration'),
        ('T', 'Technical Win'),
        ('D', 'Data Sharing'),
        ('O', 'Other'),
    )

    project = models.ForeignKey('Project', on_delete=models.PROTECT)

    # WARNING: family_id is unique within a project, but not necessarily unique globally.
    family_id = models.CharField(db_index=True, max_length=100)
    display_name = models.CharField(db_index=True, max_length=100, null=True, blank=True)  # human-readable name

    description = models.TextField(null=True, blank=True)

    pedigree_image = models.ImageField(null=True, blank=True, upload_to='pedigree_images')

    assigned_analyst = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                    related_name='assigned_families')  # type: ForeignKey

    success_story_types = ArrayField(models.CharField(
        max_length=1,
        choices=SUCCESS_STORY_TYPE_CHOICES,
        null=True,
        blank=True
    ), default=list())
    success_story = models.TextField(null=True, blank=True)

    analysis_notes = models.TextField(null=True, blank=True)
    analysis_summary = models.TextField(null=True, blank=True)

    coded_phenotype = models.TextField(null=True, blank=True)
    post_discovery_omim_number = models.TextField(null=True, blank=True)
    pubmed_ids = ArrayField(models.TextField(), default=list())

    analysis_status = models.CharField(
        max_length=10,
        choices=[(s[0], s[1][0]) for s in ANALYSIS_STATUS_CHOICES],
        default="Q"
    )

    internal_analysis_status = models.CharField(
        max_length=10,
        choices=[(s[0], s[1][0]) for s in ANALYSIS_STATUS_CHOICES],
        null=True,
        blank=True
    )

    internal_case_review_notes = models.TextField(null=True, blank=True)
    internal_case_review_summary = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.family_id.strip()

    def _compute_guid(self):
        return 'F%06d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('project', 'family_id')

        json_fields = [
            'guid', 'family_id', 'display_name', 'description', 'analysis_notes', 'analysis_summary',
            'analysis_status', 'pedigree_image', 'created_date', 'coded_phenotype',
            'post_discovery_omim_number', 'pubmed_ids', 'assigned_analyst'
        ]
        internal_json_fields = [
            'internal_analysis_status', 'internal_case_review_notes', 'internal_case_review_summary',
            'success_story_types', 'success_story'
        ]


# TODO should be an ArrayField directly on family once family fields have audit trail (https://github.com/macarthur-lab/seqr-private/issues/449)
class FamilyAnalysedBy(ModelWithGUID):
    family = models.ForeignKey(Family)

    def __unicode__(self):
        return '{}_{}'.format(self.family.guid, self.created_by)

    def _compute_guid(self):
        return 'FAB%06d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        json_fields = ['last_modified_date', 'created_by']


class Individual(ModelWithGUID):
    SEX_MALE = 'M'
    SEX_FEMALE = 'F'
    SEX_UNKNOWN = 'U'
    SEX_CHOICES = (
        (SEX_MALE, 'Male'),
        ('F', 'Female'),
        ('U', 'Unknown'),
    )

    AFFECTED_STATUS_AFFECTED = 'A'
    AFFECTED_STATUS_UNAFFECTED = 'N'
    AFFECTED_STATUS_UNKNOWN = 'U'
    AFFECTED_STATUS_CHOICES = (
        (AFFECTED_STATUS_AFFECTED, 'Affected'),
        (AFFECTED_STATUS_UNAFFECTED, 'Unaffected'),
        (AFFECTED_STATUS_UNKNOWN, 'Unknown'),
    )

    CASE_REVIEW_STATUS_IN_REVIEW = "I"
    CASE_REVIEW_STATUS_CHOICES = (
        ('I', 'In Review'),
        ('U', 'Uncertain'),
        ('A', 'Accepted'),
        ('R', 'Not Accepted'),
        ('Q', 'More Info Needed'),
        ('P', 'Pending Results and Records'),
        ('N', 'NMI Review'),
        ('W', 'Waitlist'),
    )

    SEX_LOOKUP = dict(SEX_CHOICES)
    AFFECTED_STATUS_LOOKUP = dict(AFFECTED_STATUS_CHOICES)
    CASE_REVIEW_STATUS_LOOKUP = dict(CASE_REVIEW_STATUS_CHOICES)
    CASE_REVIEW_STATUS_REVERSE_LOOKUP = {name.lower(): key for key, name in CASE_REVIEW_STATUS_CHOICES}

    family = models.ForeignKey(Family, on_delete=models.PROTECT)

    # WARNING: individual_id is unique within a family, but not necessarily unique globally
    individual_id = models.TextField(db_index=True)

    mother = models.ForeignKey('seqr.Individual', null=True, blank=True, on_delete=models.SET_NULL, related_name='maternal_children')
    father = models.ForeignKey('seqr.Individual', null=True, blank=True, on_delete=models.SET_NULL, related_name='paternal_children')

    sex = models.CharField(max_length=1, choices=SEX_CHOICES, default='U')
    affected = models.CharField(max_length=1, choices=AFFECTED_STATUS_CHOICES, default=AFFECTED_STATUS_UNKNOWN)

    # TODO once sample and individual ids are fully decoupled no reason to maintain this field
    display_name = models.TextField(default="", blank=True)

    notes = models.TextField(blank=True, null=True)

    case_review_status = models.CharField(max_length=2, choices=CASE_REVIEW_STATUS_CHOICES, default=CASE_REVIEW_STATUS_IN_REVIEW)
    case_review_status_last_modified_date = models.DateTimeField(null=True, blank=True, db_index=True)
    case_review_status_last_modified_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.SET_NULL)
    case_review_discussion = models.TextField(null=True, blank=True)

    phenotips_patient_id = models.CharField(max_length=30, null=True, blank=True, db_index=True)    # PhenoTips internal id
    phenotips_eid = models.CharField(max_length=165, null=True, blank=True)  # PhenoTips external id
    phenotips_data = models.TextField(null=True, blank=True)

    filter_flags = JSONField(null=True)
    pop_platform_filters = JSONField(null=True)
    population = models.CharField(max_length=5, null=True)

    def __unicode__(self):
        return self.individual_id.strip()

    def _compute_guid(self):
        return 'I%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('family', 'individual_id')

        json_fields = [
            'guid', 'individual_id', 'father', 'mother', 'sex', 'affected', 'display_name', 'notes',
            'phenotips_patient_id', 'phenotips_data', 'created_date', 'last_modified_date',
            'filter_flags', 'pop_platform_filters', 'population'
        ]
        internal_json_fields = [
            'case_review_status', 'case_review_discussion',
            'case_review_status_last_modified_date', 'case_review_status_last_modified_by',
        ]


class UploadedFileForFamily(models.Model):
    family = models.ForeignKey(Family, on_delete=models.PROTECT)
    name = models.TextField()
    uploaded_file = models.FileField(upload_to="uploaded_family_files", max_length=200)
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    uploaded_date = models.DateTimeField(null=True, blank=True)


class UploadedFileForIndividual(models.Model):
    individual = models.ForeignKey(Individual, on_delete=models.PROTECT)
    name = models.TextField()
    uploaded_file = models.FileField(upload_to="uploaded_individual_files", max_length=200)
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    uploaded_date = models.DateTimeField(null=True, blank=True)


class ProjectLastAccessedDate(models.Model):
    """Used to provide a user-specific 'last_accessed' column in the project table"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    last_accessed_date = models.DateTimeField(auto_now=True, db_index=True)


class Sample(ModelWithGUID):
    """This model represents a single data type (eg. Read Alignments, Variant Calls, or SV Calls) that's generated from
    a single biological sample (eg. WES, WGS, RNA, Array).

    It stores metadata on both the dataset (fields: dataset_type, dataset_file_path, loaded_date, etc.) and the
    underlying sample (fields: sample_type)

    A sample can have be used to generate multiple types of analysis results, depending on the
    sample type. For example, an exome, genome or rna sample can be used to generate an aligned bam,
    a variant callset, CNV callset, etc., and an rna sample can also yield ASE, and splice junction
    data.

    For now, all meta-data on these analysis results is stored in the sample record, but
    if versioning is needed for analysis results, it'll be necessary to create a separate table
    for each analysis type, where records have a many(analysis-versions)-to-one(sample) relationship with this table.
    """

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

    DATASET_TYPE_READ_ALIGNMENTS = 'ALIGN'
    DATASET_TYPE_VARIANT_CALLS = 'VARIANTS'
    DATASET_TYPE_SV_CALLS = 'SV'
    DATASET_TYPE_BREAKPOINTS = 'BREAK'
    DATASET_TYPE_SPLICE_JUNCTIONS = 'SPLICE'
    DATASET_TYPE_ASE = 'ASE'
    DATASET_TYPE_CHOICES = (
        (DATASET_TYPE_READ_ALIGNMENTS, 'Alignment'),
        (DATASET_TYPE_VARIANT_CALLS, 'Variant Calls'),
        (DATASET_TYPE_SV_CALLS, 'SV Calls'),
        (DATASET_TYPE_BREAKPOINTS, 'Breakpoints'),
        (DATASET_TYPE_SPLICE_JUNCTIONS, 'Splice Junction Calls'),
        (DATASET_TYPE_ASE, 'Allele Specific Expression'),
    )

    individual = models.ForeignKey('Individual', on_delete=models.PROTECT, null=True)

    sample_type = models.CharField(max_length=20, choices=SAMPLE_TYPE_CHOICES, null=True, blank=True)
    dataset_type = models.CharField(max_length=20, choices=DATASET_TYPE_CHOICES, null=True, blank=True)

    # The sample's id in the underlying dataset (eg. the VCF Id for variant callsets).
    sample_id = models.TextField(db_index=True)

    # only set for data stored in elasticsearch
    elasticsearch_index = models.TextField(null=True, blank=True, db_index=True)

    # source file
    dataset_file_path = models.TextField(db_index=True, null=True, blank=True)

    # sample status
    is_active = models.BooleanField(default=False)
    loaded_date = models.DateTimeField(null=True, blank=True)

    #funding_source = models.CharField(max_length=20, null=True)
    #is_external_data = models.BooleanField(default=False)

    def __unicode__(self):
        return self.sample_id.strip()

    def _compute_guid(self):
        return 'S%010d_%s' % (self.id, _slugify(str(self)))

    class Meta:
       json_fields = [
           'guid', 'created_date', 'sample_type', 'dataset_type', 'sample_id', 'elasticsearch_index',
           'dataset_file_path', 'is_active', 'loaded_date',
       ]


# TODO AliasFields work for lookups, but save/update doesn't work?
class AliasField(models.Field):
    def contribute_to_class(self, cls, name, private_only=False):
        super(AliasField, self).contribute_to_class(cls, name, private_only=True)
        setattr(cls, name, self)

    def __get__(self, instance, instance_type=None):
        return getattr(instance, self.db_column)


#class SampleBatch(ModelWithGUID):
#    """Represents a set of biological samples that were processed together."""
#
#    notes = models.TextField(null=True, blank=True)
#
#    def __unicode__(self):
#        return self.name.strip()
#
#    def _compute_guid(self):
#        return 'D%05d_%s' % (self.id, _slugify(str(self)))


class SavedVariant(ModelWithGUID):
    family = models.ForeignKey('Family', on_delete=models.CASCADE)

    xpos_start = models.BigIntegerField()
    xpos_end = models.BigIntegerField(null=True)
    xpos = AliasField(db_column="xpos_start")
    ref = models.TextField()
    alt = models.TextField()

    selected_main_transcript_id = models.CharField(max_length=20, null=True)
    saved_variant_json = JSONField(default=dict)

    def __unicode__(self):
        chrom, pos = get_chrom_pos(self.xpos_start)
        return "%s:%s-%s" % (chrom, pos, self.family.guid)

    def _compute_guid(self):
        return 'SV%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('xpos_start', 'xpos_end', 'ref', 'alt', 'family')

        json_fields = ['guid', 'xpos', 'ref', 'alt', 'selected_main_transcript_id']


class VariantTagType(ModelWithGUID):
    """
    Previous color choices:
        '#1f78b4',
        '#a6cee3',
        '#b2df8a',
        '#33a02c',
        '#fdbf6f',
        '#ff7f00',
        '#ff0000',
        '#cab2d6',
        '#6a3d9a',
        '#8F754F',
        '#383838',
    """
    project = models.ForeignKey('Project', null=True, on_delete=models.CASCADE)

    name = models.TextField()
    category = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=20, default="#1f78b4")
    order = models.FloatField(null=True)
    is_built_in = models.BooleanField(default=False)  # built-in tags (eg. "Pathogenic") can't be modified by users through the UI

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'VTT%05d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('project', 'name', 'color')

        json_fields = ['guid', 'name', 'category', 'description', 'color', 'order']


class VariantTag(ModelWithGUID):
    saved_variants = models.ManyToManyField('SavedVariant')
    variant_tag_type = models.ForeignKey('VariantTagType', on_delete=models.CASCADE)

    # context in which a variant tag was saved
    search_hash = models.CharField(max_length=50, null=True)
    #  TODO deprecate and migrate to search_hash
    search_parameters = models.TextField(null=True, blank=True)  # aka. search url

    def __unicode__(self):
        saved_variants_ids = "".join(str(saved_variant) for saved_variant in self.saved_variants.all())
        return "%s:%s" % (saved_variants_ids, self.variant_tag_type.name)

    def _compute_guid(self):
        return 'VT%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        json_fields = ['guid', 'search_parameters', 'search_hash', 'last_modified_date', 'created_by']


class VariantNote(ModelWithGUID):
    saved_variants = models.ManyToManyField('SavedVariant')
    note = models.TextField(null=True, blank=True) # TODO should never be null
    submit_to_clinvar = models.BooleanField(default=False)

    # these are for context
    search_hash = models.CharField(max_length=50, null=True)
    #  TODO deprecate and migrate to search_hash
    search_parameters = models.TextField(null=True, blank=True)  # aka. search url

    def __unicode__(self):
        saved_variants_ids = "".join(str(saved_variant) for saved_variant in self.saved_variants.all())
        return "%s:%s" % (saved_variants_ids, (self.note or "")[:20])

    def _compute_guid(self):
        return 'VN%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        json_fields = ['guid', 'note', 'submit_to_clinvar', 'last_modified_date', 'created_by']


class VariantFunctionalData(ModelWithGUID):
    FUNCTIONAL_DATA_CHOICES = (
        ('Functional Data', (
            ('Biochemical Function', json.dumps({
                'description': 'Gene product performs a biochemical function shared with other known genes in the disease of interest, or consistent with the phenotype.',
                'color': '#311B92',
            })),
            ('Protein Interaction', json.dumps({
                'description': 'Gene product interacts with proteins previously implicated (genetically or biochemically) in the disease of interest.',
                'color': '#4A148C',
            })),
            ('Expression', json.dumps({
                'description': 'Gene is expressed in tissues relevant to the disease of interest and/or is altered in expression in patients who have the disease.',
                'color': '#7C4DFF',
            })),
            ('Patient Cells', json.dumps({
                'description': 'Gene and/or gene product function is demonstrably altered in patients carrying candidate mutations.',
                'color': '#B388FF',
            })),
            ('Non-patient cells', json.dumps({
                'description': 'Gene and/or gene product function is demonstrably altered in human cell culture models carrying candidate mutations.',
                'color': '#9575CD',
            })),
            ('Animal Model', json.dumps({
                'description': 'Non-human animal models with a similarly disrupted copy of the affected gene show a phenotype consistent with human disease state.',
                'color': '#AA00FF',
            })),
            ('Non-human cell culture model', json.dumps({
                'description': 'Non-human cell-culture models with a similarly disrupted copy of the affected gene show a phenotype consistent with human disease state.',
                'color': '#BA68C8',
            })),
            ('Rescue', json.dumps({
                'description': 'The cellular phenotype in patient-derived cells or engineered equivalents can be rescued by addition of the wild-type gene product.',
                'color': '#663399',
            })),
        )),
        ('Functional Scores', (
            ('Genome-wide Linkage', json.dumps({
                'metadata_title': 'LOD Score',
                'description': 'Max LOD score used in analysis to restrict where you looked for causal variants; provide best score available, whether it be a cumulative LOD score across multiple families or just the best family\'s LOD score.',
                'color': '#880E4F',
            })),
            ('Bonferroni corrected p-value', json.dumps({
                'metadata_title': 'P-value',
                'description': 'Bonferroni-corrected p-value for gene if association testing/burden testing/etc was used to identify the gene.',
                'color': '#E91E63',
            })),
            ('Kindreds w/ Overlapping SV & Similar Phenotype', json.dumps({
                'metadata_title': '#',
                'description': 'Number of kindreds (1+) previously reported/in databases as having structural variant overlapping the gene and a similar phenotype.',
                'color': '#FF5252',
            })),
        )),
        ('Additional Kindreds (Literature, MME)', (
             ('Additional Unrelated Kindreds w/ Causal Variants in Gene', json.dumps({
                'metadata_title': '# additional families',
                'description': 'Number of additional kindreds with causal variants in this gene (Any other kindreds from collaborators, MME, literature etc). Do not count your family in this total.',
                'color': '#D84315',
             })),
         )),
    )

    saved_variants = models.ManyToManyField('SavedVariant')
    functional_data_tag = models.TextField(choices=FUNCTIONAL_DATA_CHOICES)
    metadata = models.TextField(null=True)

    search_hash = models.CharField(max_length=50, null=True)
    #  TODO deprecate and migrate to search_hash
    search_parameters = models.TextField(null=True, blank=True)

    def __unicode__(self):
        saved_variants_ids = "".join(str(saved_variant) for saved_variant in self.saved_variants.all())
        return "%s:%s" % (saved_variants_ids, self.functional_data_tag)

    def _compute_guid(self):
        return 'VFD%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        json_fields = ['guid', 'functional_data_tag', 'metadata', 'last_modified_date', 'created_by']


class GeneNote(ModelWithGUID):
    note = models.TextField(default="", blank=True)
    gene_id = models.CharField(max_length=20)  # ensembl ID

    def __unicode__(self):
        return "%s:%s" % (self.gene_id, (self.note or "")[:20])

    def _compute_guid(self):
        return 'GN%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        json_fields = ['guid', 'note', 'gene_id', 'last_modified_date', 'created_by']


class LocusList(ModelWithGUID):
    """List of gene ids or regions"""

    name = models.TextField(db_index=True)
    description = models.TextField(null=True, blank=True)

    is_public = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'LL%05d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        permissions = _SEQR_OBJECT_PERMISSIONS
        unique_together = ('name', 'description', 'is_public', 'created_by')

        json_fields = ['guid', 'created_by', 'created_date', 'last_modified_date', 'name', 'description', 'is_public']


class LocusListGene(ModelWithGUID):
    locus_list = models.ForeignKey('LocusList', on_delete=models.CASCADE)

    gene_id = models.TextField(db_index=True)

    description = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return "%s:%s" % (self.locus_list, self.gene_id)

    def _compute_guid(self):
        return 'LLG%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('locus_list', 'gene_id')


class LocusListInterval(ModelWithGUID):
    locus_list = models.ForeignKey('LocusList', on_delete=models.CASCADE)

    genome_version = models.CharField(max_length=5, choices=GENOME_VERSION_CHOICES, default=GENOME_VERSION_GRCh37)
    chrom = models.CharField(max_length=2)
    start = models.IntegerField()
    end = models.IntegerField()

    description = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return "%s:%s:%s-%s" % (self.locus_list, self.chrom, self.start, self.end)

    def _compute_guid(self):
        return 'LLI%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('locus_list', 'genome_version', 'chrom', 'start', 'end')

        json_fields = ['guid', 'genome_version', 'chrom', 'start', 'end']


class AnalysisGroup(ModelWithGUID):
    name = models.TextField()
    description = models.TextField(null=True, blank=True)

    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    families = models.ManyToManyField(Family)

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'AG%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('project', 'name')

        json_fields = ['guid', 'name', 'description']


class VariantSearch(ModelWithGUID):
    name = models.CharField(max_length=200, null=True)
    search = JSONField()

    def __unicode__(self):
        return self.name or self.id

    def _compute_guid(self):
        return 'VS%07d_%s' % (self.id, _slugify(self.name or ''))

    class Meta:
        unique_together = ('created_by', 'name')

        json_fields = ['guid', 'name', 'search', 'created_by_id']


class VariantSearchResults(ModelWithGUID):
    variant_search = models.ForeignKey('VariantSearch', on_delete=models.CASCADE)
    families = models.ManyToManyField('Family')
    search_hash = models.CharField(max_length=50, db_index=True, unique=True)

    def __unicode__(self):
        return self.search_hash

    def _compute_guid(self):
        return 'VSR%07d_%s' % (self.id, _slugify(str(self)))

