import logging
import os
import re
import subprocess
import tempfile
from tqdm import tqdm
import urllib

from django.core.validators import URLValidator

logger = logging.getLogger(__name__)


def download_file(url, to_dir=tempfile.gettempdir(), verbose=True):
    """Download the given file and returns its local path.
     Args:
        url (string): HTTP or FTP url
     Returns:
        string: local file path
    """

    if not url or (not url.startswith("http://") and not url.startswith("ftp://")):
        raise ValueError("Invalid url: {}".format(url))
    local_file_path = os.path.join(to_dir, os.path.basename(url))
    remote_file_size = get_remote_file_size(url)
    if os.path.isfile(local_file_path) and os.path.getsize(local_file_path) == remote_file_size:
        logger.info("Re-using {} previously downloaded from {}".format(local_file_path, url))
        return local_file_path

    input_iter = urllib.urlopen(url)
    if verbose:
        logger.info("Downloading {} to {}".format(url, local_file_path))
        input_iter = tqdm(input_iter, unit=" data" if url.endswith("gz") else " lines")

    with open(local_file_path, 'w') as f:
        f.writelines(input_iter)

    input_iter.close()

    return local_file_path


def get_remote_file_size(url):
    URLValidator()(url)  # make sure it's a valid url, to avoid security issues with shell execution
    curl_output = subprocess.check_output("curl -s --head '{}'".format(url), shell=True)
    match = re.search("Content-Length:[ ](\d+)", curl_output)
    if match:
        return int(match.group(1))

    return None