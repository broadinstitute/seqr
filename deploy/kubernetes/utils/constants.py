
DEPLOYMENT_LABELS = ["local", "gcloud-dev", 'gcloud-prod']
DEPLOYABLE_COMPONENTS = [
    'cockpit',
    'elasticsearch',
    'kibana',
    'matchbox',
    'mongo',
    'nginx',
    'phenotips',
    'pipeline-runner',
    'postgres',
    'seqr',
]

PORTS = {
    'cockpit':   [9090],
    'elasticsearch': [30001],
    'kibana':        [5601],
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


# scripts to run, in order
DEPLOYMENT_SCRIPTS = [
    'kubernetes/scripts/deploy_begin.sh',
    'kubernetes/scripts/deploy_mongo.sh',
    'kubernetes/scripts/deploy_postgres.sh',
    'kubernetes/scripts/deploy_elasticsearch.sh',
    #'kubernetes/scripts/deploy_matchbox.sh',
    'kubernetes/scripts/deploy_phenotips.sh',
    'kubernetes/scripts/deploy_seqr.sh',
    'kubernetes/scripts/deploy_kibana.sh',
    'kubernetes/scripts/deploy_nginx.sh',
    'kubernetes/scripts/deploy_pipeline_runner.sh',
    'kubernetes/scripts/deploy_cockpit.sh',
]
