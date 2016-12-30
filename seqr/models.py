from abc import abstractmethod
import string
import random
import uuid


from django.contrib.auth.models import User, Group
from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.utils.text import slugify

from guardian.shortcuts import assign_perm

from seqr.utils.xpos_utils import get_chrom_pos, get_xpos
from reference_data.models import GENOME_BUILD_GRCh37, GENOME_BUILD_GRCh38, _GENOME_BUILD_CHOICES


CAN_VIEW = 'can_view'
CAN_EDIT = 'can_edit'
IS_OWNER= 'is_owner'

_SEQR_OBJECT_PERMISSIONS = (
    (CAN_VIEW, CAN_VIEW),
    (CAN_EDIT, CAN_EDIT),
    (IS_OWNER, IS_OWNER),
)


class ModelWithGUID(models.Model):
    GUID_SIZE = 50   # not too long, not too short

    # GUID useful where a human-readable id is better than django's auto-incrementing integer id
    guid = models.CharField(max_length=GUID_SIZE, unique=True)
    created_date = models.DateTimeField(default=timezone.now)  # this is used instead of a version
    created_by = models.ForeignKey(User, null=True, blank=True, related_name='+')

    last_modified_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    last_modified_by = models.ForeignKey(User, null=True, blank=True, related_name='+')

    class Meta:
        abstract=True

    @abstractmethod
    def slug(self):
        """Returns a human-readable label (aka. slug) for this object that only has alphanumeric
        chars and '-'. This label doesn't have to be globally unique, but shouldn't be null or blank.
        """

    def save(self, *args, **kwargs):
        """Create a GUID at object creation time."""

        being_created = not self.pk
        if being_created:
            # create the GUID
            if self.created_date is None:
                self.created_date = timezone.now()

            # ensure uniqueness
            random_chars = ''.join(random.choice(string.ascii_uppercase) for _ in range(5))

            self.guid = ("%s_%s_%s" % (
                self.created_date.strftime("%Y%m%d"),  # _%H%M%S_%f
                random_chars,
                self.slug(),
            ))[:ModelWithGUID.GUID_SIZE]

        super(ModelWithGUID, self).save(*args, **kwargs)


class LocusList(ModelWithGUID):
    """List of gene ids or regions"""
    name = models.CharField(max_length=140)
    description = models.TextField(null=True, blank=True)

    is_public = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def slug(self):
        return slugify(self.name.strip())

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

    feature_id = models.CharField(max_length=20, null=True, blank=True, db_index=True)  # eg. ensembl id

    chrom = models.CharField(max_length=1, null=True, blank=True)  # optional chrom, start, end
    start = models.IntegerField(null=True, blank=True)
    end = models.IntegerField(null=True, blank=True)

    comment = models.TextField(null=True, blank=True)

    # whether to include or exclude this gene id or region in searches
    include_or_exclude_by_default = models.CharField(max_length=1, choices=INCLUDE_OR_EXCLUDE, default='+')

    def __unicode__(self):
        return "%s%s" % (self.include_or_exclude_by_default,
                         self.feature_id or "%s:%s-%s" % (self.chrom, self.start, self.end)
                         )

    def slug(self):
        return slugify(self.feature_id or "%s:%s-%s" % (self.chrom, self.start, self.end))


class Project(ModelWithGUID):
    name = models.CharField(max_length=140)  # human-readable project name

    description = models.TextField(null=True, blank=True)

    # user groups that allow Project permissions to be extended to other objects as long as
    # the user remains is in one of these groups.
    owners_group = models.ForeignKey(Group, related_name='+')
    can_edit_group = models.ForeignKey(Group, related_name='+')
    can_view_group = models.ForeignKey(Group, related_name='+')

    primary_investigator = models.ForeignKey(User, null=True, blank=True, related_name='+')

    # legacy
    custom_reference_populations = models.ManyToManyField('base.ReferencePopulation', blank=True, related_name='+')
    deprecated_project_id = models.CharField(max_length=140, default="", blank=True)

    def __unicode__(self):
        return self.name

    def slug(self):
        return slugify(self.name.strip())

    def save(self, *args, **kwargs):
        """Override the save method and create user permissions groups + add the created_by user.

        This could be done with signals, but seems cleaner to do it this way.
        """
        being_created = not self.pk

        if being_created:
            # create user groups
            self.owners_group = Group.objects.create(name="%s_%s_%s" % (self.slug()[:30], 'owners', uuid.uuid4()))
            self.can_edit_group = Group.objects.create(name="%s_%s_%s" % (self.slug()[:30], 'can_edit', uuid.uuid4()))
            self.can_view_group = Group.objects.create(name="%s_%s_%s" % (self.slug()[:30], 'can_view', uuid.uuid4()))

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


class ProjectTag(ModelWithGUID):
    """Used to categorize projects"""

    project = models.ForeignKey('Project', on_delete=models.CASCADE)

    name = models.CharField(max_length=50, db_index=True)

    def __unicode__(self):
        return self.name

    def slug(self):
        return slugify(self.name.strip())


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

    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=10, default="'#1f78b4")

    def __unicode__(self):
        return self.name

    def slug(self):
        return slugify(self.name.strip())


class VariantTag(ModelWithGUID):
    project = models.ForeignKey('Project', null=True, on_delete=models.SET_NULL)

    variant_tag_type = models.ForeignKey('VariantTagType', on_delete=models.CASCADE)

    genome_build_id = models.CharField(max_length=5, choices=_GENOME_BUILD_CHOICES, default=GENOME_BUILD_GRCh37)
    xpos_start = models.BigIntegerField()
    xpos_end = models.BigIntegerField()

    ref = models.TextField()
    alt = models.TextField()

    # Cache annotations to make them easier to look up
    # ENSG ensembl gene and transcript id for the canonical transcript as this position
    gene_id = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    transcript_id = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    molecular_consequence = models.CharField(max_length=35, null=True, blank=True)

    family = models.ForeignKey('Family', null=True, blank=True, on_delete=models.SET_NULL)
    search_parameters = models.TextField(null=True, blank=True)  # aka. search url

    def __unicode__(self):
        return self.name

    def slug(self):
        chrom, pos = get_chrom_pos(self.xpos_start)
        return slugify("%s:%s-%s" % (
            chrom, pos, self.variant_tag_type.name)
        )


class VariantNote(ModelWithGUID):
    project = models.ForeignKey('Project', null=True, on_delete=models.SET_NULL)

    note = models.TextField(null=True, blank=True)

    genome_build_id = models.CharField(max_length=5, choices=_GENOME_BUILD_CHOICES, default=GENOME_BUILD_GRCh37)
    xpos_start = models.BigIntegerField()
    xpos_end = models.BigIntegerField()
    ref = models.TextField()
    alt = models.TextField()

    # Cache annotations to make them easier to look up
    # ENSG ensembl gene and transcript id for the canonical transcript as this position
    gene_id = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    transcript_id = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    molecular_consequence = models.CharField(max_length=35, null=True, blank=True)

    # these are for context - if note was saved for a family or an individual
    family = models.ForeignKey('Family', null=True, blank=True, on_delete=models.SET_NULL)
    search_parameters = models.TextField(null=True, blank=True)  # aka. search url

    def __unicode__(self):
        return self.name

    def slug(self):
        chrom, pos = get_chrom_pos(self.xpos_start)
        return slugify("%s:%s-%s" % (
            chrom, pos, (self.note or "")[:20])
        )


"""
class FamilyGroup(ModelWithGUID):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    families = models.ManyToManyField(Family)

    def __unicode__(self):
        return self.name
"""


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

    # should this be one to many?
    project = models.ForeignKey('Project', null=True, blank=True)

    name = models.CharField(max_length=140)  # human-readable name

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
    internal_case_review_brief_summary = models.TextField(null=True, blank=True)

    # replaced with id as the GUID as the id, and name as the display name
    deprecated_family_id = models.CharField(max_length=140, default="", blank=True)

    #TODO add attachments  https://github.com/macarthur-lab/seqr-private/issues/228

    def __unicode__(self):
        return self.name

    def slug(self):
        return slugify(self.name.strip())


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
        ('U', 'Uncertain'),
        ('A', 'Accepted: Platform Uncertain'),
        ('E', 'Accepted: Exome'),
        ('G', 'Accepted: Genome'),
        ('R', 'Not Accepted'),
        ('H', 'Hold'),
        ('Q', 'More Info Needed'),
    )

    family = models.ForeignKey(Family, null=True, blank=True)

    individual_id = models.CharField(max_length=100)  # WARNING: this id is unique within a family, and is not necessarily globally-unique
    maternal_id = models.CharField(max_length=100, null=True, blank=True)  # individual_id of mother
    paternal_id = models.CharField(max_length=100, null=True, blank=True)  # individual_id of father
    # add ForeignKeys for mother Individual & father Individual?

    sex = models.CharField(max_length=1, choices=SEX_CHOICES, default='U')
    affected = models.CharField(max_length=1, choices=AFFECTED_CHOICES, default='U')

    display_name = models.CharField(max_length=140, default="", blank=True)

    case_review_status = models.CharField(max_length=1, choices=CASE_REVIEW_STATUS_CHOICES, null=True, blank=True)
    case_review_requested_info = models.TextField(null=True, blank=True)

    phenotips_eid = models.CharField(max_length=165, null=True, blank=True)  # PhenoTips 'external id'
    phenotips_id = models.CharField(max_length=30, null=True, blank=True)    # PhenoTips 'internal id'
    phenotips_data = models.TextField(null=True, blank=True)

    class Meta:
        permissions = _SEQR_OBJECT_PERMISSIONS

    def __unicode__(self):
        return self.display_name or self.individual_id

    def slug(self):
        return slugify(self.individual_id.strip())


class ProjectEvent(models.Model):
    PHENOTIPS_MODIFIED = 'pt_edit'
    VARIANT_TAG_ADDED = 'vt_a'
    VARIANT_TAG_REMOVED = 'vt_r'
    VARIANT_NOTE_CREATED = 'vn_c'
    VARIANT_SEARCH = 'vs'

    EVENT_TYPE_CHOICES = (
        (PHENOTIPS_MODIFIED, 'PhenoTips Modified'),
        (VARIANT_TAG_ADDED, 'Variant Tag Added'),
        (VARIANT_TAG_REMOVED, 'Variant Tag Removed'),
        (VARIANT_NOTE_CREATED, 'Variant Note'),
        (VARIANT_SEARCH, 'Variant Search'),
    )

    event_type = models.CharField(max_length=15, choices=EVENT_TYPE_CHOICES, db_index=True)
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, null=True, related_name='+')
    project = models.ForeignKey(Project, null=True, related_name='+')
    family = models.ForeignKey(Family, null=True, related_name='+')
    individual = models.ForeignKey(Individual, null=True, related_name='+')
    message = models.TextField(null=True)

    def __unicode__(self):
        return "%s: %s => %s" % (self.date, self.event_type, self.message)


class SequencingSample(ModelWithGUID):
    """Sequencing dataset sample"""

    SAMPLE_STATUS_CHOICES = (
        ('S', 'In Sequencing'),
        ('I', 'Interim'),    # needs additional sequencing to reach expected (95x) coverage
        ('C', 'Complete'),   # sample sequencing complete and achieved expected coverage
        ('A', 'Abandoned'),  # sample failed sequencing
    )

    SEQUENCING_TYPE_WES = 'WES'
    SEQUENCING_TYPE_WGS = 'WES'
    SEQUENCING_TYPE_RNA = 'RNA'
    SEQUENCING_TYPE_CHOICES = (
        (SEQUENCING_TYPE_WES, 'Exome'),
        (SEQUENCING_TYPE_WGS, 'Whole Genome'),
        (SEQUENCING_TYPE_RNA, 'Whole Genome'),
    )

    dataset = models.ForeignKey('Dataset', on_delete=models.PROTECT)
    individual = models.ForeignKey('Individual', null=True, on_delete=models.SET_NULL)

    sample_id = models.CharField(max_length=140)

    sequencing_type = models.CharField(max_length=3, choices=SEQUENCING_TYPE_CHOICES)

    sample_status = models.CharField(max_length=1, choices=SAMPLE_STATUS_CHOICES, default='S')

    bam_path = models.TextField(null=True, blank=True)


    # INBREEDING COEFF
    # https://github.com/macarthur-lab/seqr-private/issues/222
    # On the individuals page, change the coverage metric from MTC. A sample is considered complete if it hits 90% at 20x

    picard_metrics_directory = models.TextField(null=True, blank=True)

    # from picard .hybrid_selection_metrics
    TOTAL_READS = models.IntegerField(null=True, blank=True)
    PF_READS = models.IntegerField(null=True, blank=True)
    PCT_PF_UQ_READS = models.FloatField(null=True, blank=True)
    PCT_PF_UQ_READS_ALIGNED = models.FloatField(null=True, blank=True)
    PCT_PF_UQ_READS_ALIGNED = models.FloatField(null=True, blank=True)
    PCT_SELECTED_BASES = models.FloatField(null=True, blank=True)
    MEAN_TARGET_COVERAGE = models.FloatField(null=True, blank=True)
    MEDIAN_TARGET_COVERAGE = models.FloatField(null=True, blank=True)
    GQ0_FRACTION = models.FloatField(null=True, blank=True)
    PCT_TARGET_BASES_10X = models.FloatField(null=True, blank=True)
    PCT_TARGET_BASES_20X = models.FloatField(null=True, blank=True)
    PCT_TARGET_BASES_30X = models.FloatField(null=True, blank=True)
    PCT_TARGET_BASES_40X = models.FloatField(null=True, blank=True)
    PCT_TARGET_BASES_50X = models.FloatField(null=True, blank=True)
    PCT_TARGET_BASES_100X = models.FloatField(null=True, blank=True)
    HS_LIBRARY_SIZE = models.FloatField(null=True, blank=True)

    AT_DROPOUT = models.FloatField(null=True, blank=True)
    GC_DROPOUT = models.FloatField(null=True, blank=True)

    def __unicode__(self):
        return self.sample_id

    def slug(self):
        return slugify(self.sample_id)

"""
class ArraySample(models.Model):

    individual = models.ForeignKey('Individual', null=True, on_delete=models.SET_NULL)
    array_dataset = models.ForeignKey('Dataset', on_delete=models.PROTECT)

    ARRAY_TYPE_CHOICES = (
        ('ILLUMINA_INFINIUM_250K', ),
    )

    array_type = models.CharField(max_length=50, choices=ARRAY_TYPE_CHOICES)
"""


class Dataset(ModelWithGUID):
    """Represent a single data source file (like a variant callset or array dataset), that contains
    data for one or more samples. This model contains the metadata fields for this dataset.
    """

    name = models.CharField(max_length=140)
    description = models.TextField(null=True, blank=True)

    data_loaded_date = models.DateTimeField(null=True, blank=True)

    path = models.TextField(null=True, blank=True)   # file or url from which the data was loaded

    class Meta:
        permissions = _SEQR_OBJECT_PERMISSIONS

    def __unicode__(self):
        return self.name

    def slug(self):
        return slugify(self.name.strip())

