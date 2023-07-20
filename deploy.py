#!/usr/bin/env python3

# This script is heavily inspired by the deployment pattern in the Google Cloud Docs
# https://cloud.google.com/composer/docs/dag-cicd-integration-guide#add_a_dag_sync_job
# https://github.com/GoogleCloudPlatform/python-docs-samples/blob/65492281e5ba257129ef2ad728455a9feb811791/composer/cicd_sample/utils/add_dags_to_composer.py
import argparse
import glob
import os
from typing import Iterator, Tuple

from google.cloud import storage

EXCLUDE_PATTERNS = ['test']


def find_pyfiles_for_upload(
    dags_directory: str, gcs_prefix: str
) -> Iterator[Tuple[str, str]]:
    local_files = glob.iglob(os.path.join(dags_directory, '**/*.py'), recursive=True)
    for local_file in local_files:
        if any((pattern in local_file for pattern in EXCLUDE_PATTERNS)):
            continue
        rel_path = os.path.relpath(local_file, dags_directory)
        remote_file = os.path.join(gcs_prefix, rel_path)
        yield local_file, remote_file


def upload_dags_to_composer(
    dags_directory: str,
    gcs_project: str,
    gcs_bucket_name: str,
    gcs_prefix: str,
) -> None:
    storage_client = storage.Client(project=gcs_project)
    bucket = storage_client.bucket(gcs_bucket_name)
    for local_file, remote_file in find_pyfiles_for_upload(dags_directory, gcs_prefix):
        blob = bucket.blob(remote_file)
        blob.upload_from_filename(local_file)
        print(f'File {local_file} uploaded to {gcs_bucket_name}/{remote_file}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dags-directory',
        default='dags/',
        help='Relative path to the source directory containing your DAGs',
    )
    parser.add_argument(
        '--gcs-project',
        default='seqr-project',
        help='Name of the GCS project',
    )
    parser.add_argument(
        '--gcs-bucket-name',
        default='us-central1-seqr-airflow2-51ffae41-bucket',
        help='Name of the DAGs bucket of your Composer environment without the gs:// prefix',
    )
    parser.add_argument(
        '--gcs-prefix',
        default='dags/',
        help='Prefix within the DAGs bucket of your Composer environment',
    )
    args = parser.parse_args()
    upload_dags_to_composer(
        args.dags_directory,
        args.gcs_project,
        args.gcs_bucket_name,
        args.gcs_prefix,
    )
