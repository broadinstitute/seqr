"""Utilities for populating family data."""

import logging
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist
from xbrowse_server.base.models import Family as BaseFamily, AnalysedBy as BaseAnalysedBy

logger = logging.getLogger(__name__)


def retrieve_family_analysed_by(family_raw_id):
    try:
        legacy_family = BaseFamily.objects.get(seqr_family_id=family_raw_id)
        return [ab.toJSON() for ab in legacy_family.analysedby_set.all()]
    except ObjectDoesNotExist:
        logger.error("Unable to find legacy family model with seqr model id % s" % family_raw_id)
        return []


def retrieve_multi_family_analysed_by(families):
    family_guid_map = {family.pop('id'): family['familyGuid'] for family in families}
    family_id_map = {family.id: family.seqr_family_id for family in BaseFamily.objects.filter(seqr_family_id__in=family_guid_map.keys())}
    analysed_by = defaultdict(list)
    for ab in BaseAnalysedBy.objects.filter(family_id__in=family_id_map.keys()):
        analysed_by[family_guid_map[family_id_map[ab.family_id]]].append(ab.toJSON())
    return analysed_by

