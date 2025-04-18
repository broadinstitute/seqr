from settings import CLICKHOUSE_SERVICE_HOSTNAME

def clickhouse_backend_enabled():
    return bool(CLICKHOUSE_SERVICE_HOSTNAME)