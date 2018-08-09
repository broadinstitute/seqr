import logging
from tqdm import tqdm
import urllib

logger = logging.getLogger(__name__)


def download_file_to(url, local_path, verbose=True):
    input_iter = urllib.urlopen(url)
    if verbose:
        logger.info("Downloading {} to {}".format(url, local_path))
        input_iter = tqdm(input_iter, unit=" data" if url.endswith("gz") else " lines")

    with open(local_path, 'w') as f:
        f.writelines(input_iter)

    input_iter.close()
