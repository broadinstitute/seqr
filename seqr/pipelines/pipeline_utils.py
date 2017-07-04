import logging

from seqr.utils.gcloud_utils import get_gcloud_file_stats
from seqr.utils.shell_utils import get_file_stats

logger = logging.getLogger(__name__)


def get_local_or_gcloud_file_stats(file_path):
    if file_path.startswith("gs://"):
        file_stats = get_gcloud_file_stats(file_path)
    else:
        file_stats = get_file_stats(file_path)
    return file_stats


def _get_file_ctime(file_path):
    file_stats = get_local_or_gcloud_file_stats(file_path)
    return file_stats.ctime if file_stats else 0


def inputs_older_than_outputs(inputs, outputs, label=""):
    max_input_ctime = max(_get_file_ctime(input_path) for input_path in inputs)
    min_output_ctime = min(_get_file_ctime(output_path) for output_path in outputs)

    if max_input_ctime < min_output_ctime:
        logger.info(label + "output(s) (%s) up to date relative to input(s) (%s)" % (", ".join(outputs), ", ".join(inputs)))

    return max_input_ctime < min_output_ctime

