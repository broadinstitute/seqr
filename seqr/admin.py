from copy import deepcopy
from django.contrib import admin
from seqr.models import Project, Family, Individual, Sample, LocusList, LocusListGene, LocusListInterval, VariantNote, \
    VariantTag, VariantTagType, VariantFunctionalData, SavedVariant, GeneNote, AnalysisGroup, ProjectCategory, \
    FamilyAnalysedBy

for model_class in [
    Project,
    Family,
    Individual,
    Sample,
    LocusList,
    LocusListGene,
    LocusListInterval,
    VariantNote,
    VariantTag,
    VariantTagType,
    VariantFunctionalData,
    SavedVariant,
    GeneNote,
    AnalysisGroup,
    ProjectCategory,
    FamilyAnalysedBy,
]:

    @admin.register(model_class)
    class SpecificModelAdmin(admin.ModelAdmin):
        search_fields = [field.name for field in model_class._meta.get_fields() if field.name in set([
            'guid', 'name', 'display_name', 'deprecated_project_id', 'family_id', 'individual_id', 'description'
        ])]
        list_display = deepcopy(model_class._meta.json_fields if hasattr(model_class._meta, 'json_fields') else search_fields)
        if hasattr(model_class._meta, 'internal_json_fields'):
            list_display = model_class._meta.internal_json_fields + list_display
        if 'created_date' not in list_display:
            list_display.append('created_date')
        if 'last_modified_date' not in list_display:
            list_display.append('last_modified_date')
        save_on_top = True
        list_per_page = 2000
