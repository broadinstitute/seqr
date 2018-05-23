from django.contrib import admin
from xbrowse_server.base.models import *


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'display_name']
    list_filter = ['user__is_staff', 'user__is_superuser']
    save_on_top = True
    list_per_page = 1000


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['project_id', 'project_name', 'description', 'disease_area', 'is_functional_data_enabled']
    search_fields = ['project_id', 'project_name', 'description', 'disease_area']
    list_filter = ['is_functional_data_enabled']
    save_on_top = True
    list_per_page = 1000


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    search_fields = ['family_id', 'family_name']
    list_display = search_fields + ['analysis_status']
    save_on_top = True
    list_per_page = 1000
    

@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    search_fields = ['indiv_id']
    list_display = search_fields + ['maternal_id', 'paternal_id', 'gender', 'affected', 'other_notes']
    save_on_top = True
    list_per_page = 1000


@admin.register(VCFFile)
class VCFFileAdmin(admin.ModelAdmin):
    search_fields = ['file_path']
    list_display = search_fields + ['project', 'sample_type', 'dataset_type', 'elasticsearch_index', 'loaded_date']
    save_on_top = True
    list_per_page = 1000
    

@admin.register(ReferencePopulation)
class ReferencePopulationAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 1000
    

@admin.register(FamilyGroup)
class FamilyGroupAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 1000
