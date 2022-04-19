from django.contrib.admin import AdminSite, apps

class SuperuserAdminSite(AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser

class SuperuserAdminConfig(apps.AdminConfig):
    default_site = 'admin.apps.SuperuserAdminSite'
