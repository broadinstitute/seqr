import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render

logger = logging.getLogger(__name__)


@staff_member_required
def staff_dashboard(request):

    return render(request, "staff/staff_dashboard.html")


@staff_member_required
def users_page(request):

    return render(request, "staff/users_table.html", {
        'users': User.objects.all().order_by('email')
    })

