
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
    'scripts/deploy_init.sh',
    'scripts/deploy_nginx.sh',
    'scripts/deploy_cockpit.sh',
    'scripts/deploy_mongo.sh',
    'scripts/deploy_postgres.sh',
    'scripts/deploy_elasticsearch.sh',
    'scripts/deploy_kibana.sh',
    #'scripts/deploy_matchbox.sh',
    'scripts/deploy_pipeline_runner.sh',
    'scripts/deploy_phenotips.sh',
    'scripts/deploy_seqr.sh',
]
