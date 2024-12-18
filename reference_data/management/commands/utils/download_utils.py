import logging
import os
import requests
import tempfile
from tqdm import tqdm

logger = logging.getLogger(__name__)


def download_file(url, to_dir=tempfile.gettempdir(), verbose=True):
    """Download the given file and returns its local path.
     Args:
        url (string): HTTP or FTP url
     Returns:
        string: local file path
    """

    if not (url and url.startswith(("http://", "https://"))):
        raise ValueError("Invalid url: {}".format(url))
    local_file_path = os.path.join(to_dir, os.path.basename(url))
    if os.path.isfile(local_file_path) and os.path.getsize(local_file_path) == _get_remote_file_size(url):
        logger.info("Re-using {} previously downloaded from {}".format(local_file_path, url))
        return local_file_path

    is_gz = url.endswith(".gz")
    response = requests.get(url, stream=is_gz, timeout=300)
    input_iter = response if is_gz else response.iter_content()
    if verbose:
        logger.info("Downloading {} to {}".format(url, local_file_path))
        input_iter = tqdm(input_iter, unit=" data" if is_gz else " lines")

    with open(local_file_path, 'wb') as f:
        f.writelines(input_iter)

    input_iter.close()

    return local_file_path


def _get_remote_file_size(url):
    try:
        response = requests.head(url, timeout=5)
        return int(response.headers.get('Content-Length', '0'))
    except Exception:
        # file size not yet implemented for FTP and other protocols, and HEAD not supported for all http requests
        return 0
