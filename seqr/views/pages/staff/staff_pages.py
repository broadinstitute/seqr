import logging

from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render

from seqr.models import Sample, Family, Individual
from settings import LOGIN_URL

logger = logging.getLogger(__name__)


@staff_member_required(login_url=LOGIN_URL)
def staff_dashboard(request):

    return render(request, "staff/staff_dashboard.html")


@staff_member_required(login_url=LOGIN_URL)
def seqr_stats_page(request):

    families_count = Family.objects.only('family_id').distinct('family_id').count()
    individuals_count = Individual.objects.only('individual_id').distinct('individual_id').count()

    sample_counts = defaultdict(set)
    for sample in Sample.objects.filter(sample_status=Sample.SAMPLE_STATUS_LOADED).only('sample_id', 'sample_type'):
        sample_counts[sample.sample_type].add(sample.sample_id)

    for sample_type, sample_ids_set in sample_counts.items():
        sample_counts[sample_type] = len(sample_ids_set)

    return render(request, "staff/seqr_stats.html", {
        'families_count': families_count,
        'individuals_count': individuals_count,
        'sample_counts': sample_counts,
    })


@staff_member_required(login_url=LOGIN_URL)
def users_page(request):

    return render(request, "staff/users_table.html", {
        'users': User.objects.all().order_by('email')
    })
