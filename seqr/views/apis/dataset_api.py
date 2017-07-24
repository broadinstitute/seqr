import datetime
import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from seqr.models import Dataset
from seqr.utils.file_utils import get_file_stats

logger = logging.Logger(__name__)


def get_dataset_by_id(dataset_id):
    try:
        return Dataset.objects.get(dataset_id=dataset_id)
    except ObjectDoesNotExist:
        return None


def get_dataset(project, analysis_type, source_file_path):
    try:
        return Dataset.objects.get(
            analysis_type=analysis_type,
            source_file_path=source_file_path,
            project=project,
        )
    except ObjectDoesNotExist:
        return None


def get_or_create_dataset(project, analysis_type, source_file_path, dataset_id=None):

    try:
        if dataset_id is None:
            dataset = Dataset.objects.get(
                analysis_type=analysis_type,
                source_file_path=source_file_path,
                project=project,
            )
        else:
            dataset = Dataset.objects.get(
                dataset_id=dataset_id,
            )

            dataset.analysis_type=analysis_type
            dataset.source_file_path = source_file_path
            dataset.project = project
            dataset.save()

    except ObjectDoesNotExist:
        logger.info("Creating %s dataset for %s" % (analysis_type, source_file_path))
        dataset = create_dataset(project, analysis_type, source_file_path, dataset_id)

    return dataset


def create_dataset(project, analysis_type, source_file_path, dataset_id=None):

    # compute a dataset_id based on source_file_path
    if dataset_id is None:
        file_stats = get_file_stats(source_file_path)
        dataset_id = "_".join(map(str, [
            datetime.datetime.fromtimestamp(float(file_stats.ctime)).strftime('%Y%m%d'),
            os.path.basename(source_file_path).split(".")[0][:20],
            file_stats.size
        ]))

    # create the Dataset
    dataset = Dataset.objects.create(
        dataset_id=dataset_id,
        analysis_type=analysis_type,
        source_file_path=source_file_path,
        project=project,
    )

    return dataset


def link_dataset_to_sample_records(dataset, sample_records):
    for sample in sample_records:
        dataset.samples.add(sample)

