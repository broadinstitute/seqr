import logging
import os
import re
import subprocess
import tempfile

from django.core.validators import URLValidator

logger = logging.getLogger(__name__)


def download_remote_file(url, to_dir=tempfile.gettempdir()):
    """Uses wget to download the given file and returns its local path.

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
        return local_file_path

    logger.info("Downloading {} to {}".format(url, local_file_path))

    os.system("wget %s -O %s" % (url, local_file_path))

    return local_file_path


def get_remote_file_size(url):
    URLValidator()(url)  # make sure it's a valid url, to avoid security issues with shell execution

    curl_output = subprocess.check_output("curl -s --head '{}'".format(url), shell=True)

    match = re.search("Content-Length:[ ](\d+)", curl_output)
    if match:
        return int(match.group(1))

    return None