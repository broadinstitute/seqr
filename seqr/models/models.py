from django.db import models
from django.db.models import signals
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from __future__ import unicode_literals


# Create your models here.

class ResourceLastAccessed(models.Model):
    """Represents the last time a given User accessed a given Resource"""
    resource = models.ForeignKey(Resource)
    last_accessed_by = models.ForeignKey(User)
    last_accessed_date = models.DateTimeField(null=True)



class Resource(models.Model):
    """Represents a generic user-created or user-uploaded resource."""

    id = models.SlugField(max_length=150, primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(User,
                                   null=True, related_name='created_by', on_delete=models.SET_NULL)
    created_date = models.DateTimeField(null=True)

    is_public = models.BooleanField(default=False)
    user_permissions = models.ManyToManyField(User, through='ResourcePermissions')

    #RESOURCE_TYPES = {'variants-VCF': 'VCF file path',
    #                  'reads-BAM': 'BAM file path',
    #                  'genelist': 'Gene list',
    #                  }

    #type = models.CharField(max_length=15, choices=RESOURCE_TYPES.items())


    def get_last_accessed_date(self, user):
        """Returns a datetime object representing the last time the given User
        accessed this Resource. Returns None if the User hasn't ever accessed
        this Resource."""

        try:
            return ResourceLastAccessed.objects.get(resource=self,
                                                    last_accessed_by=user).last_accessed_date
        except ObjectDoesNotExist:
            return None

    def set_last_accessed_date(self, user):
        """Sets the last time the given User accessed this Resource to now."""

        rla_obj, created = ResourceLastAccessed.objects.get_or_create(
                resource=self,
                last_accessed_by=user)
        rla_obj.last_accessed_date = timezone.now()
        rla_obj.save()

    def to_dict(self, user=None):
        """Returns a dict that maps column names to column values.
        If user is specified, then last_accessed_date is also added to the dict.
        """

        # based on http://www.metaltoad.com/blog/what-i-learned-today-django-modeltodict-and-missing-fields
        r = {f.name: f.value_from_object(self) for f in self._meta.fields}

        if user is not None:
            r['last_accessed_date'] = self.get_last_accessed_date(user)

        return r

    def save(self, *args, **kwargs):
        """Overridden to execute extra steps when a new Resource is created.
        This could be done with signals, but seems cleaner to do this way.
        """
        being_created = not self.pk

        super(Resource, self).save(*args, **kwargs)

        if not being_created:
            return

        # grant CREATOR resource permissions to the user that created this resource.
        user = self.created_by
        if not user.is_staff:  # staff have access too all resources anyway
            ResourcePermissions.objects.create(resource=self,
                                               user=user,
                                               permissions_level=ResourcePermissions.CREATOR)


class ResourcePermissions(models.Model):
    """Represents the permission level for a given User to access a given Resource"""

    COLLABORATOR = 1
    MANAGER = 2
    CREATOR = 3

    PERMISSION_LEVEL_CHOICES = (
        (COLLABORATOR, "COLLABORATOR"),
        (MANAGER, "MANAGER"),
        (CREATOR, "CREATOR"),
    )

    resource = models.ForeignKey(Resource)
    user = models.ForeignKey(User)
    permissions_level = models.SmallIntegerField(
            choices=PERMISSION_LEVEL_CHOICES,
            default=COLLABORATOR)


class UserProfile(models.Model):
    """UserProfile serves to add fields and utility methods to Django's built-in
    User model without replacing it."""

    user = models.OneToOneField(User)

    def can_view(self, resource):
        """Returns True if this user can view the given resource"""
        return self._has_permissions_at_or_above(
                ResourcePermissions.COLLABORATOR,
                resource)

    def can_modify(self, resource):
        """Returns True if this user can modify the given resource"""
        return self._has_permissions_at_or_above(
                ResourcePermissions.MANAGER,
                resource)

    def _has_permissions_at_or_above(self, permissions_level, resource):
        """Whether this user has the given permissions level with respect to
        the given resource.

        Args:
            permissions_level: A ResourcePermissions level (eg.
                ResourcePermissions.COLLABORATOR, ResourcePermissions.MANAGER)
            resource: The Resource object to check permissions for
        """
        if resource.is_public:
            return True
        if self.user.is_staff:
            return True

        has_permissions = ResourcePermissions.objects.filter(
                user=self.user,
                resource=resource,
                permissions_level__gte=permissions_level).exists()
        return has_permissions

    @staticmethod
    def create_user_profile_for_new_user(sender,
                                         instance,
                                         created=False,
                                         **kwargs):
        """Signal handler for User model creation events. Creates the
        corresponding UserProfile whenever a User is created."""
        if created:
            UserProfile.objects.create(user=instance)

    @staticmethod
    def delete_user_profile_for_deleted_user(sender, instance, **kwargs):
        """Signal handler for User model creation events. Deletes the
        corresponding UserProfile whenever a User is deleted."""
        UserProfile.objects.filter(user=instance).delete()

signals.post_save.connect(UserProfile.create_user_profile_for_new_user,
                          sender=User,
                          dispatch_uid="create_user_profile_for_new_user")
signals.post_delete.connect(UserProfile.delete_user_profile_for_deleted_user,
                            sender=User,
                            dispatch_uid="delete_user_profile_for_deleted_user")




###  Resource Sub-classes  ####

class Project(Resource):
    pass

    #def to_dict(self):
    #    return super(Project, self).to_dict()


class ResourceWithVersions(Resource):
    """Base class for resources that support multiple versions"""
    version = models.IntegerField(null=True)

    #version_name = models.CharField(null=True,
    #   blank=True, max_length=50, related_name="version_name")  # human-readable description of the version

    class Meta:
        # use child's table instead of creating a separate table for Model
        # based on https://docs.djangoproject.com/en/1.8/topics/db/models/#model-inheritance
        abstract = True


#class VariantCallset(ResourceWithVersions):
#    """Represents a pointer to a VCF file. Should this be a raw VCF or
#       a VEP-annotated VCF?"""
#    pass

admin.site.register(Resource)
admin.site.register(ResourcePermissions)
admin.site.register(ResourceLastAccessed)
admin.site.register(Project)
#admin.site.register(LocalGeminiDatabase)

