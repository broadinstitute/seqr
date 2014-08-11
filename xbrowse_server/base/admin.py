from django.contrib import admin
from xbrowse_server.base.models import *
from django import forms

admin.site.register(Project)
admin.site.register(Family)
admin.site.register(Cohort)
admin.site.register(Individual)
admin.site.register(DiseaseGeneList)
admin.site.register(ReferencePopulation)
admin.site.register(ProjectPhenotype)
admin.site.register(UserProfile)

admin.site.register(FamilySearchFlag)

admin.site.register(VCFFile)
admin.site.register(FamilyGroup)


class FamilyModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s - %s" % (obj.project.project_id, obj.family_id)

class FamilyImageSlideAdminForm(forms.ModelForm):
    family = FamilyModelChoiceField(queryset=Family.objects.all())
    class Meta:
        model = FamilyImageSlide


class FamilyImageSlideAdmin(admin.ModelAdmin):
    form = FamilyImageSlideAdminForm






admin.site.register(FamilyImageSlide, FamilyImageSlideAdmin)
