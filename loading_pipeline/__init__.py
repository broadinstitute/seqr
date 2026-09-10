import datetime

MAJOR_VERSION = 3

__version__ = (
    f'{MAJOR_VERSION}.{datetime.datetime.now(datetime.UTC).strftime("%Y%m%d.%H%M%S")}'
)
