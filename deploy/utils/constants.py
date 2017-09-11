DEPLOYMENT_TARGETS = ["local", "gcloud-dev", "gcloud-prod"]

DEPLOYABLE_COMPONENTS = [
    "init-cluster",
    "init-elasticsearch-cluster",
    "secrets",

    "cockpit",
    "elasticsearch",
    "kibana",
    "es-client",
    "es-master",
    "es-data",

    "matchbox",
    "mongo",
    "nginx",
    "phenotips",
    #"pipeline-runner",
    "postgres",
    "seqr",
]

COMPONENT_PORTS = {
    "init-cluster": [],
    "init-elasticsearch-cluster": [],
    "secrets": [],

    "cockpit":   [9090],
    "elasticsearch": [9200],
    "kibana":        [5601],
    "es-client":     [9200],
    "es-master":     [9020],
    "es-data":     [9020],

    "matchbox":  [9020],
    "mongo":     [27017],
    "phenotips": [8080],
    "pipeline-runner": [35000],
    "postgres":  [5432],
    "seqr":      [8000],
    "nginx":     [80, 443],
}

COMPONENTS_TO_OPEN_IN_BROWSER = set([
    "cockpit",
    "elasticsearch",
    "kibana",
    "phenotips",
    "pipeline-runner",
    "seqr",
])
