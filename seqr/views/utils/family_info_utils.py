"""Utilities for populating family data."""

import logging

from django.core.exceptions import ObjectDoesNotExist
from xbrowse_server.base.models import Family as BaseFamily

logger = logging.getLogger(__name__)


def retrieve_family_analysed_by(family_raw_id):
    try:
        legacy_family = BaseFamily.objects.get(seqr_family_id=family_raw_id)
        return [ab.toJSON() for ab in legacy_family.analysedby_set.all()]
    except ObjectDoesNotExist:
        logger.error("Unable to find legacy family model with seqr model id % s" % family_raw_id)
        return []

