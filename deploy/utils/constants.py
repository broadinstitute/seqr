
DEPLOYMENT_TARGETS = ["local", "gcloud-dev", "gcloud-prod"]

DEPLOYABLE_COMPONENTS = [
    'cockpit',
    'elasticsearch',
    'elasticsearch-sharded',
    'kibana',
    'matchbox',
    'mongo',
    'nginx',
    'phenotips',
    'pipeline-runner',
    'postgres',
    'seqr',
]

COMPONENT_PORTS = {
    'cockpit':   [9090],
    'elasticsearch': [30001],
    'elasticsearch-sharded': [3000],
    'kibana':        [30002],
    'phenotips': [8080],
    'pipeline-runner': [35000],
    'postgres':  [5432],
    'mongo':     [27017],
    'matchbox':  [9020],
    'nginx':     [80, 443],
    'seqr':      [8000],
}


COMPONENTS_TO_OPEN_IN_BROWSER = set([
    'cockpit',
    'elasticsearch',
    'kibana',
    'phenotips',
    'pipeline-runner',
    'seqr',
])
