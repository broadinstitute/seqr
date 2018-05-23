from django.contrib import admin
from xbrowse_server.base.models import *
from django import forms

class SharedAdminSettings:
    save_on_top = True
    list_per_page = 2000
    

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin, SharedAdminSettings):
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'display_name']
    list_filter = ['user__is_staff', 'user__is_superuser']

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin, SharedAdminSettings):
    list_display = ['project_id', 'project_name', 'description', 'disease_area', 'is_functional_data_enabled', 'disable_staff_access']
    search_fields = ['project_id', 'project_name', 'description', 'disease_area']
    list_filter = ['is_functional_data_enabled', 'disable_staff_access']

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin, SharedAdminSettings):
    pass


@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin, SharedAdminSettings):
    pass


@admin.register(VCFFile)
class VCFFileAdmin(admin.ModelAdmin, SharedAdminSettings):
    pass


@admin.register(ReferencePopulation)
class ReferencePopulationAdmin(admin.ModelAdmin, SharedAdminSettings):
    pass


@admin.register(FamilyGroup)
class FamilyGroupAdmin(admin.ModelAdmin, SharedAdminSettings):
    pass


class FamilyModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s - %s" % (obj.project.project_id, obj.family_id)


class FamilyImageSlideAdminForm(forms.ModelForm):
    family = FamilyModelChoiceField(queryset=Family.objects.all())
    class Meta:
        model = FamilyImageSlide
        exclude = []


class FamilyImageSlideAdmin(admin.ModelAdmin, SharedAdminSettings):
    form = FamilyImageSlideAdminForm


admin.site.register(FamilyImageSlide, FamilyImageSlideAdmin)
