DEPLOYMENT_TARGETS = ["minikube", "kube-solo", "gcloud-dev", "gcloud-prod", "gcloud-prod-v2", "gcloud-prod-elasticsearch"]

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
    "postgres",
    "seqr",
    "pipeline-runner",
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
    "postgres":  [5432],
    "seqr":      [8000],
    "pipeline-runner": [30005],
    "nginx":     [80, 443],
}

COMPONENTS_TO_OPEN_IN_BROWSER = set([
    "cockpit",
    "elasticsearch",
    "kibana",
    "phenotips",
    "seqr",
    "pipeline-runner",
])

REFERENCE_DATA_FILES = {
    'gencode': 'gencode.v27lift37.annotation.gtf.gz',
    'high_variability_genes': 'high_variability.genes.txt',
    'constraint_scores': 'constraint_scores.csv',
    'gtex_expression': 'GTEx_Analysis_v6_RNA-seq_RNA-SeQCv1.1.8_gene_rpkm.gct.gz',
    'gtex_samples': 'GTEx_Data_V6_Annotations_SampleAttributesDS.txt',
    'omim_genmap': 'omim/genemap2.txt',
    'clinvar': 'clinvar/.tsv',
    'dbnsfp': 'dbNSFP3.5_gene'
}
