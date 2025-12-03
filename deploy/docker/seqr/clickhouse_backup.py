import datetime
import os
import requests

from google.cloud import storage

CLICKHOUSE_SERVICE_HOSTNAME =  os.environ.get('CLICKHOUSE_SERVICE_HOSTNAME')
CLICKHOUSE_SERVICE_PORT = int(os.environ.get('CLICKHOUSE_SERVICE_PORT', '9000'))
CLICKHOUSE_WRITER_USER = os.environ.get('CLICKHOUSE_WRITER_USER')
CLICKHOUSE_WRITER_PASSWORD = os.environ.get('CLICKHOUSE_WRITER_PASSWORD')
DEPLOYMENT_TYPE = os.environ.get('DEPLOYMENT_TYPE')

BUCKET = "seqr-clickhouse-backups"
TS_FORMAT = "%Y-%m-%d-%H-%M-%S"
TIMEOUT_S = 5400

def find_most_recent_success(bucket):
    successful = []
    blobs = bucket.list_blobs(prefix=DEPLOYMENT_TYPE + '/', delimiter='/')
    for page in blobs.pages:
        for folder in page.prefixes:
            parts = folder.split("/")
            try:
                ts = datetime.datetime.strptime(parts[1], TS_FORMAT)
                if bucket.blob(f"{DEPLOYMENT_TYPE}/{parts[1]}/_SUCCESS").exists():
                    successful.append((ts, parts[1]))
            except ValueError:
                continue
    latest_ts, latest_prefix = max(successful, key=lambda x: x[0])
    return latest_prefix

def main():
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    base_backup = find_most_recent_success(bucket)
    new_backup_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")
    backup_sql = (
        f"BACKUP DATABASE seqr "
        f"TO Disk('gcs_backups', '{DEPLOYMENT_TYPE}/{new_backup_timestamp}') "
        f"SETTINGS base_backup=Disk('gcs_backups', '{DEPLOYMENT_TYPE}/{base_backup}');"
    )
    url = f"http://{CLICKHOUSE_WRITER_USER}:{CLICKHOUSE_WRITER_PASSWORD}@{CLICKHOUSE_SERVICE_HOSTNAME}:{CLICKHOUSE_SERVICE_PORT}/"
    response = requests.post(url, data=backup_sql, timeout=TIMEOUT_S)
    if not (response.ok and 'BACKUP_CREATED' in response.text):
        sys.exit(1)
    blob = bucket.blob(f'{DEPLOYMENT_TYPE}/{new_backup_timestamp}/_SUCCESS')
    blob.upload_from_string("")

if __name__ == '__main__':
    main()