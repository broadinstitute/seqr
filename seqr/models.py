from abc import abstractmethod
import uuid


from django.contrib.auth.models import User, Group
from django.db import models
from django.utils import timezone
from django.utils.text import slugify as __slugify

from guardian.shortcuts import assign_perm

from seqr.utils.xpos_utils import get_chrom_pos, get_xpos
from reference_data.models import GENOME_BUILD_GRCh37, GENOME_BUILD_GRCh38, _GENOME_BUILD_CHOICES


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

    created_date = models.DateTimeField(default=timezone.now,  db_index=True)
    created_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    # used for optimistic concurrent write protection (to detect concurrent changes)
    last_modified_date = models.DateTimeField(null=True, blank=True,  db_index=True)

    class Meta:
        abstract = True

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
        if being_created and not self.created_date:
            self.created_date = timezone.now()
        else:
            self.last_modified_date = timezone.now()

        super(ModelWithGUID, self).save(*args, **kwargs)

        if being_created:
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

    #primary_investigator = models.ForeignKey(User, null=True, blank=True, related_name='+')

    is_phenotips_enabled = models.BooleanField(default=False)
    phenotips_user_id = models.CharField(max_length=100, null=True, blank=True)

    is_mme_enabled = models.BooleanField(default=False)
    mme_primary_data_owner = models.CharField(max_length=100, null=True, blank=True)

    # legacy
    custom_reference_populations = models.ManyToManyField('base.ReferencePopulation', blank=True, related_name='+')
    deprecated_last_accessed_date = models.DateTimeField(null=True, blank=True)
    deprecated_project_id = models.TextField(default="", blank=True)  # replace with model's 'id' field

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        label = (self.name or self.deprecated_project_id).strip()
        return 'R%04d_%s' % (self.id, _slugify(str(label)))

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
            if user and not user.is_staff:  # staff have access too all resources anyway
                user.groups.add(self.owners_group, self.can_edit_group, self.can_view_group)

    def delete(self, *args, **kwargs):
        """Override the delete method to also delete the project-specific user groups"""

        super(Project, self).delete(*args, **kwargs)

        self.owners_group.delete()
        self.can_edit_group.delete()
        self.can_view_group.delete()

    class Meta:
        permissions = _SEQR_OBJECT_PERMISSIONS


class ProjectCategory(ModelWithGUID):
    projects = models.ManyToManyField('Project')
    name = models.TextField(db_index=True)  # human-readable category name
    # color = models.CharField(max_length=20, default="#1f78b4")

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'PC%06d_%s' % (self.id, _slugify(str(self)))


class Family(ModelWithGUID):
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
        ('I', 'Analysis in Progress'),
        ('Q', 'Waiting for data'),
    )

    CAUSAL_INHERITANCE_MODE_CHOICES = (
        ('u', 'unknown'),
        ('d', 'dominant'),
        ('x', 'x-linked recessive'),
        ('n', 'de novo'),
        ('r', 'recessive'),
    )

    project = models.ForeignKey('Project', on_delete=models.PROTECT)

    # WARNING: family_id is unique within a project, but not necessarily unique globally.
    family_id = models.CharField(db_index=True, max_length=100)
    display_name = models.CharField(db_index=True, max_length=100, null=True, blank=True)  # human-readable name

    description = models.TextField(null=True, blank=True)

    pedigree_image = models.ImageField(null=True, blank=True, upload_to='pedigree_images')

    analysis_notes = models.TextField(null=True, blank=True)
    analysis_summary = models.TextField(null=True, blank=True)

    causal_inheritance_mode = models.CharField(max_length=20, default='u', choices=CAUSAL_INHERITANCE_MODE_CHOICES)

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


class Individual(ModelWithGUID):
    SEX_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('U', 'Unknown'),
    )

    AFFECTED_CHOICES = (
        ('A', 'Affected'),
        ('N', 'Unaffected'),
        ('U', 'Unknown'),
    )

    CASE_REVIEW_STATUS_CHOICES = (
        ('I', 'In Review'),
        ('U', 'Uncertain'),
        ('A', 'Accepted'),
        ('R', 'Not Accepted'),
        ('Q', 'More Info Needed'),
    )

    CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS = (
        ('A', 'Array'),   # allow multiple-select. No selection = Platform Uncertain
        ('E', 'Exome'),
        ('G', 'Genome'),
        ('R', 'RNA-seq'),
        ('S', 'Store DNA'),
    )

    SEX_LOOKUP = dict(SEX_CHOICES)
    AFFECTED_LOOKUP = dict(AFFECTED_CHOICES)
    CASE_REVIEW_STATUS_LOOKUP = dict(CASE_REVIEW_STATUS_CHOICES)

    family = models.ForeignKey(Family, on_delete=models.PROTECT)

    # WARNING: individual_id is unique within a family, but not necessarily unique globally
    individual_id = models.TextField()
    maternal_id = models.TextField(null=True, blank=True)  # individual_id of mother
    paternal_id = models.TextField(null=True, blank=True)  # individual_id of father
    # add ForeignKeys for mother Individual & father Individual?

    sex = models.CharField(max_length=1, choices=SEX_CHOICES, default='U')
    affected = models.CharField(max_length=1, choices=AFFECTED_CHOICES, default='U')

    display_name = models.TextField(default="", blank=True)

    notes = models.TextField(blank=True, null=True)

    case_review_status = models.CharField(max_length=1, choices=CASE_REVIEW_STATUS_CHOICES, null=True, blank=True)
    case_review_status_accepted_for = models.CharField(max_length=10, null=True, blank=True)
    case_review_status_last_modified_date = models.DateTimeField(null=True, blank=True, db_index=True)
    case_review_status_last_modified_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    case_review_requested_info = models.TextField(null=True, blank=True)

    phenotips_patient_id = models.CharField(max_length=30, null=True, blank=True, db_index=True)    # PhenoTips internal id
    phenotips_eid = models.CharField(max_length=165, null=True, blank=True)  # PhenoTips external id
    phenotips_data = models.TextField(null=True, blank=True)

    mme_id = models.CharField(max_length=50, null=True, blank=True)
    mme_submitted_data = models.TextField(null=True, blank=True)


    # An Individual record represents info about a person within the context of a particular project.
    # In some cases, the same person may be added to more than one project. The ManyToMany
    # replationship between Individual and Sample allows an Individual to have multiple samples
    # (eg. both Exome and Genome), and also allows a sample from a person to be mapped to different
    # Individual records in different projects (eg. the usecase where a 2nd project is created to
    # give some collaborators access to only a small subset of the samples in a callset)

    samples = models.ManyToManyField('Sample')


    def __unicode__(self):
        return self.individual_id.strip()

    def _compute_guid(self):
        return 'I%06d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        unique_together = ('family', 'individual_id')


class UploadedFileForFamily(models.Model):
    family = models.ForeignKey(Family)
    name = models.TextField()
    uploaded_file = models.FileField(upload_to="uploaded_family_files", max_length=200)
    uploaded_by = models.ForeignKey(User, null=True)
    uploaded_date = models.DateTimeField(null=True, blank=True)


class UploadedFileForIndividual(models.Model):
    individual = models.ForeignKey(Individual)
    name = models.TextField()
    uploaded_file = models.FileField(upload_to="uploaded_individual_files", max_length=200)
    uploaded_by = models.ForeignKey(User, null=True)
    uploaded_date = models.DateTimeField(null=True, blank=True)


class ProjectLastAccessedDate(models.Model):
    """Used to provide a user-specific 'last_accessed' column in the project table"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    last_accessed_date = models.DateTimeField(auto_now=True, db_index=True)


class Sample(ModelWithGUID):
    """Sequencing dataset sample - represents a biological sample"""

    SAMPLE_STATUS_CHOICES = (
        ('S', 'In Sequencing'),
        ('I', 'Interim'),    # needs additional sequencing to reach expected (95x) coverage
        ('C', 'Complete'),   # sample sequencing complete and achieved expected coverage
        ('A', 'Abandoned'),  # sample failed sequencing
    )

    sample_batch = models.ForeignKey('SampleBatch', on_delete=models.PROTECT, null=True)

    # This sample_id should be used for looking up this sample in the underlying dataset (for
    # example, for variant callsets, it should be the VCF sample id). It is not a ForeignKey
    # into another table.
    sample_id = models.TextField()

    # This individual_id text field is not a foreign key, and is meant to serve as a place holder
    # for potential use-cases where a dataset is created/uploaded before a project is created.
    # Later when a project is created and a pedigree file or a list of individuals provided,
    # those individuals can be linked through the Individual model's ManyToMany relationship to
    # Sample records by matching against this individual_id field.
    individual_id = models.TextField(null=True, blank=True)

    sample_status = models.CharField(max_length=1, choices=SAMPLE_STATUS_CHOICES, default='S')

    # reference back to xbrowse base_project is a temporary work-around to support merging of
    # different projects into one - including those that contain different types of callsets
    # such as exome and genome
    deprecated_base_project = models.ForeignKey('base.Project', null=True)

    is_loaded = models.BooleanField(default=False)
    loaded_date = models.DateTimeField(null=True, blank=True)

    source_file_path = models.TextField(null=True, blank=True) # bam, CNV or other file path

    def __unicode__(self):
        return self.sample_id.strip()

    def _compute_guid(self):
        return 'S%06d_%s' % (self.id, _slugify(str(self)))

    #class Meta:
    #    unique_together = ('sample_batch', 'sample_id')

"""
class ArraySample(models.Model):

    sample_batch = models.ForeignKey('SampleBatch', on_delete=models.PROTECT)

    ARRAY_TYPE_CHOICES = (
        ('ILLUMINA_INFINIUM_250K', ),
    )

    array_type = models.CharField(max_length=50, choices=ARRAY_TYPE_CHOICES)
"""


class SampleBatch(ModelWithGUID):
    """Represent a single data source file (like a variant callset or array dataset), that contains
    data for one or more samples. This model contains the metadata fields for this dataset.
    """

    name = models.TextField()
    description = models.TextField(null=True, blank=True)

    SAMPLE_TYPE_WES = 'WES'
    SAMPLE_TYPE_WGS = 'WGS'
    SAMPLE_TYPE_RNA = 'RNA'
    SAMPLE_TYPE_CHOICES = (
        (SAMPLE_TYPE_WES, 'Exome'),
        (SAMPLE_TYPE_WGS, 'Whole Genome'),
        (SAMPLE_TYPE_RNA, 'RNA'),
    )
    sample_type = models.CharField(max_length=3, choices=SAMPLE_TYPE_CHOICES)

    genome_build_id = models.CharField(max_length=5, choices=_GENOME_BUILD_CHOICES, default=GENOME_BUILD_GRCh37)

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'D%05d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        permissions = _SEQR_OBJECT_PERMISSIONS


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
    project = models.ForeignKey('Project', on_delete=models.CASCADE)

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


class VariantTag(ModelWithGUID):
    variant_tag_type = models.ForeignKey('VariantTagType', on_delete=models.CASCADE)

    genome_build_id = models.CharField(max_length=5, choices=_GENOME_BUILD_CHOICES, default=GENOME_BUILD_GRCh37)
    xpos_start = models.BigIntegerField()
    xpos_end = models.BigIntegerField()

    ref = models.TextField()
    alt = models.TextField()

    # Cache genotypes and annotations for the variant as gene id and consequence - in case the dataset gets deleted, etc.
    variant_annotation = models.TextField(null=True, blank=True)
    variant_genotypes = models.TextField(null=True, blank=True)

    # context in which a variant tag was saved
    family = models.ForeignKey('Family', null=True, blank=True, on_delete=models.SET_NULL)
    search_parameters = models.TextField(null=True, blank=True)  # aka. search url

    def __unicode__(self):
        chrom, pos = get_chrom_pos(self.xpos_start)
        return "%s:%s: %s" % (chrom, pos, self.variant_tag_type.name)

    def _compute_guid(self):
        return 'VT%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        index_together = ('xpos_start', 'ref', 'alt', 'genome_build_id')

        unique_together = ('variant_tag_type', 'genome_build_id', 'xpos_start', 'xpos_end', 'ref', 'alt', 'family')


class VariantNote(ModelWithGUID):
    project = models.ForeignKey('Project', null=True, on_delete=models.SET_NULL)

    note = models.TextField(null=True, blank=True)

    genome_build_id = models.CharField(max_length=5, choices=_GENOME_BUILD_CHOICES, default=GENOME_BUILD_GRCh37)
    xpos_start = models.BigIntegerField()
    xpos_end = models.BigIntegerField()
    ref = models.TextField()
    alt = models.TextField()

    # Cache genotypes and annotations for the variant as gene id and consequence - in case the dataset gets deleted, etc.
    variant_annotation = models.TextField(null=True, blank=True)
    variant_genotypes = models.TextField(null=True, blank=True)

    # these are for context - if note was saved for a family or an individual
    family = models.ForeignKey('Family', null=True, blank=True, on_delete=models.SET_NULL)
    search_parameters = models.TextField(null=True, blank=True)  # aka. search url

    def __unicode__(self):
        chrom, pos = get_chrom_pos(self.xpos_start)
        return "%s:%s: %s" % (chrom, pos, (self.note or "")[:20])

    def _compute_guid(self):
        return 'VT%07d_%s' % (self.id, _slugify(str(self)))


class LocusList(ModelWithGUID):
    """List of gene ids or regions"""
    name = models.TextField()
    description = models.TextField(null=True, blank=True)

    is_public = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name.strip()

    def _compute_guid(self):
        return 'LL%05d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        permissions = _SEQR_OBJECT_PERMISSIONS


class LocusListEntry(ModelWithGUID):
    """Either the gene_id or the genome_build_id & xpos_start & xpos_end must be specified"""

    INCLUDE_OR_EXCLUDE = (
        ('+', 'include'),
        ('-', 'exclude'),
    )

    parent = models.ForeignKey('LocusList', on_delete=models.CASCADE)
    genome_build_id = models.CharField(max_length=5, choices=_GENOME_BUILD_CHOICES, default=GENOME_BUILD_GRCh37)

    # must specify either feature_id or chrom, start, end
    feature_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    chrom = models.CharField(max_length=2, null=True, blank=True)
    start = models.IntegerField(null=True, blank=True)
    end = models.IntegerField(null=True, blank=True)

    comment = models.TextField(null=True, blank=True)

    # whether to include or exclude this gene id or region in searches
    include_or_exclude_by_default = models.CharField(max_length=1, choices=INCLUDE_OR_EXCLUDE, default='+')

    def __unicode__(self):
        return "%s%s" % (self.include_or_exclude_by_default,
                         self.feature_id or "%s:%s-%s" % (self.chrom, self.start, self.end)
                         )

    def _compute_guid(self):
        return 'LLE%07d_%s' % (self.id, _slugify(str(self)))

    class Meta:
        # either feature_id or chrom, start, end must be provided, so together they should be unique
        unique_together = ('parent', 'genome_build_id', 'feature_id', 'chrom', 'start', 'end')


"""
class FamilyGroup(ModelWithGUID):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    name = models.TextField()
    description = models.TextField(null=True, blank=True)

    families = models.ManyToManyField(Family)

    def __unicode__(self):
        return self.name
"""

