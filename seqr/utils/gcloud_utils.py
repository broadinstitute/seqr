import logging
import re
import time

from seqr.utils.shell_utils import run_shell_command, FileStats

logger = logging.getLogger(__name__)

#def get_gcloud_default_service_acount():
#     "gcloud compute instances list --format=json"


def does_gcloud_file_exist(gs_path):
    return get_gcloud_file_stats(gs_path) is not None


def get_gcloud_file_ctime(gs_path):
    stats = get_gcloud_file_stats(gs_path)
    if not stats:
        return None

    return


def get_gcloud_file_stats(gs_path):
    _, gsutil_stat_output, _ = run_shell_command("gsutil stat %(gs_path)s" % locals(), wait_and_return_log_output=True, verbose=False)

    """
    Example gsutil stat output:

    Creation time:          Fri, 09 Jun 2017 09:36:23 GMT
    Update time:            Fri, 09 Jun 2017 09:36:23 GMT
    Storage class:          REGIONAL
    Content-Length:         363620675
    Content-Type:           text/x-vcard
    Hash (crc32c):          SWOktA==
    Hash (md5):             fEdIumyOFR7HvULeAwXCwQ==
    ETag:                   CMae+J67sNQCEAE=
    Generation:             1497000983793478
    Metageneration:         1
    """

    if not gsutil_stat_output:
        return None

    EMPTY_MATCH_OBJ = re.match("()", "")
    DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'

    creation_time = (re.search("Creation.time:[\s]+(.+)", gsutil_stat_output, re.IGNORECASE) or EMPTY_MATCH_OBJ).group(1)
    update_time = (re.search("Update.time:[\s]+(.+)", gsutil_stat_output, re.IGNORECASE) or EMPTY_MATCH_OBJ).group(1)
    file_size = (re.search("Content-Length:[\s]+(.+)", gsutil_stat_output, re.IGNORECASE) or EMPTY_MATCH_OBJ).group(1)
    file_md5 = (re.search("Hash (md5):[\s]+(.+)", gsutil_stat_output, re.IGNORECASE) or EMPTY_MATCH_OBJ).group(1)

    ctime = time.mktime(time.strptime(creation_time, DATE_FORMAT))
    mtime = time.mktime(time.strptime(update_time, DATE_FORMAT))
    return FileStats(ctime=ctime, mtime=mtime, size=file_size, md5=file_md5)


def read_gcloud_file_header(gs_path, header_prefix="#"):
    gunzip_command = "gunzip -c - | " if gs_path.endswith("gz") else ""

    _, header_content, _ = run_shell_command(
        "gsutil cat %(gs_path)s | %(gunzip_command)s head -n 5000 | grep ^%(header_prefix)s" % locals(),
        wait_and_return_log_output=True,
        verbose=False)

    return header_content


def copy_file_to_gcloud(source_path, gs_destination_path):
    returncode = run_shell_command("gsutil cp -P %(source_path)s %(gs_destination_path)s" % locals(), verbose=False).wait()

    if returncode:
        raise ValueError("Failed to copy %s %s. Return code: " % (source_path, gs_destination_path, returncode))

