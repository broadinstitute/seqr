from django.contrib import admin
from xbrowse_server.base.models import *

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
