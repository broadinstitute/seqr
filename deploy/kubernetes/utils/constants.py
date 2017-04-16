import os


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DEPLOYMENT_LABELS = ["local", "gcloud"]
DEPLOYABLE_COMPONENTS = ['postgres', 'phenotips', 'mongo', 'seqr', 'nginx', 'matchbox']

PORTS = {
    'postgres':  [5432],
    'phenotips': [8080],
    'mongo':     [27017],
    'seqr':      [8000, 3000],
    'nginx':     [80, 443],
    'matchbox':  [9020],
}

WEB_SERVER_COMPONENTS = ['seqr', 'phenotips']
