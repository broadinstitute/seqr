from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from xbrowse_server.decorators import log_request
from xbrowse_server.base.models import Project, Family, ProjectGeneList
from xbrowse_server.gene_lists.models import GeneList
from xbrowse_server import server_utils
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from xbrowse.reference.utils import get_coding_regions_for_gene
from xbrowse import genomeloc

from collections import Counter
import json

