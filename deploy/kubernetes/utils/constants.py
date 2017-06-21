import os


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DEPLOYMENT_LABELS = ["local", "gcloud-dev", 'gcloud-prod']
DEPLOYABLE_COMPONENTS = ['postgres', 'phenotips', 'mongo', 'seqr', 'nginx', 'matchbox', 'cockpit', 'solr', 'cassandra', 'database-api']

PORTS = {
    'postgres':  [5432],
    'phenotips': [8080],
    'mongo':     [27017],
    'seqr':      [8000, 3000],
    'nginx':     [80, 443],
    'matchbox':  [9020],
    'cockpit':   [9090],

    'solr':         [30002],
    'cassandra':    [9042],
    'database-api': [6060],
}


DEPLOYMENT_SCRIPTS = [
    'scripts/deploy_init.sh',
    'scripts/deploy_nginx.sh',
    'scripts/deploy_postgres.sh',
    'scripts/deploy_mongo.sh',
    'scripts/deploy_phenotips.sh',
    'scripts/deploy_cockpit.sh',
    'scripts/deploy_matchbox.sh',
    'scripts/deploy_seqr.sh',

    'scripts/deploy_solr.sh',
    'scripts/deploy_cassandra.sh',
    'scripts/deploy_database_api.sh',
]


WEB_SERVER_COMPONENTS = [
    'seqr',
    'phenotips',
    'cockpit',
    'solr',
]
