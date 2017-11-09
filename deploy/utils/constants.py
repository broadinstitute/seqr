DEPLOYMENT_TARGETS = ["local", "gcloud-dev", "gcloud-prod", "gcloud-prod-v2", "gcloud-prod-elasticsearch"]

DEPLOYABLE_COMPONENTS = [
    "init-cluster",
    #"init-elasticsearch-cluster",
    "secrets",

    "cockpit",

    "elasticsearch",  # a single elasticsearch instance

    "es-client",
    "es-master",
    "es-data",
    "es-kibana",

    "kibana",

    "matchbox",
    "mongo",
    "nginx",
    "phenotips",
    #"pipeline-runner",
    "postgres",
    "seqr",
]


def _get_component_group_to_component_name_mapping():
    result = {
        "elasticsearch-sharded": ["es-master", "es-client", "es-data"],
    }
    return result


def resolve_component_groups(deployment_target, components_or_groups):
    component_groups = _get_component_group_to_component_name_mapping()

    return [component for component_or_group in components_or_groups for component in component_groups.get(component_or_group, [component_or_group])]


COMPONENT_GROUP_NAMES = list(_get_component_group_to_component_name_mapping().keys())


COMPONENT_PORTS = {
    "init-cluster": [],
    #"init-elasticsearch-cluster": [],
    "secrets": [],

    "cockpit":   [9090],

    "elasticsearch": [9200],
    "es-client":     [9200],
    "es-master":     [9020],
    "es-data":     [9020],

    "kibana":        [5601],

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
