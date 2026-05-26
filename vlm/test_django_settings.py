from settings import *

DATABASES = {
    db_name: {**db, 'TEST': {**db.get('TEST', {}), 'NAME': db_name}}
    for db_name, db in settings.DATABASES.items()
}