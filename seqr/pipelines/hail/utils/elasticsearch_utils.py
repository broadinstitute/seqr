# make sure elasticsearch is installed
import pip
pip.main(['install', 'elasticsearch'])

import collections
import elasticsearch
from pprint import pprint

from utils.vds_schema_string_utils import _parse_fields


# valid types:
#   https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping-types.html
#   long, integer, short, byte, double, float, half_float, scaled_float
#   text and keyword

VDS_TO_ES_TYPE_MAPPING = {
    "Boolean": "boolean",
    "Int":     "integer",
    "Long":    "long",
    "Double":  "float",
    "Float":   "float",
    "String":  "keyword",
}

for vds_type, es_type in VDS_TO_ES_TYPE_MAPPING.items():
    VDS_TO_ES_TYPE_MAPPING.update({"Array[%s]" % vds_type: es_type})
    VDS_TO_ES_TYPE_MAPPING.update({"Set[%s]" % vds_type: es_type})


def _map_vds_type_to_es_type(type_name):
    """Converts a VDS type (eg. "Array[Double]") to an ES type (eg. "float")"""

    es_type = VDS_TO_ES_TYPE_MAPPING.get(type_name)
    if not es_type:
        raise ValueError("Unexpected VDS type: %s" % str(type_name))

    return es_type


def generate_elasticsearch_schema(parsed_schema):
    properties = {}
    for field_path, field_type in parsed_schema.items():
        # drop the 'v', 'va' root from elastic search field names
        key = "_".join(field_path[1:] if field_path and field_path[0] in ("v", "va") else field_path)
        properties[key] = {"type": _map_vds_type_to_es_type(field_type)}

    return properties


def generate_vds_make_table_arg(parsed_schema, split_multi=True):
    result = []
    for field_path, field_type in parsed_schema.items():
        # drop the 'v', 'va' root from key-table key names
        key = "_".join(field_path[1:] if field_path and field_path[0] in ("v", "va") else field_path)
        expr = "%s = %s" % (key, ".".join(field_path))
        if split_multi and field_type.startswith("Array"):
            expr += "[va.aIndex-1]"
        result.append(expr)

    return result


def parse_vds_schema(vds_variant_schema_fields, current_parent=[], add_variant_fields=True):
    schema = {}
    if add_variant_fields:
        schema = {
            ("v", "contig", ): "String",
            ("v", "start", ): "Int",
            ("v", "ref", ): "String",
            ("v", "alt", ): "String",
        }

    for field in vds_variant_schema_fields:
        field_name = field.name
        field_type = str(field.typ)
        if field_type.startswith("Struct"):
            child_schema = parse_vds_schema(field.typ.fields, current_parent + [field_name])
            schema.update(child_schema)
        else:
            schema[tuple(current_parent + [field_name])] = field_type

    return schema


def convert_vds_schema_string_to_es_index_properties(
        top_level_fields="",
        info_fields="",
        enable_doc_values_for_fields=[],
        disable_index_for_fields=[],
):
    """Takes a string representation of the VDS variant schema and converts it to a dictionary
    that can be plugged in to the "properties" section of an Elasticsearch mapping. For example:

    'mappings': {
        'index_type1': {
            'properties': <return value>
        }
    }

    Args:
        top_level_fields (str): VDS fields that are direct children of the 'va' struct. For example:
            '''
                rsid: String,
                qual: Double,
                filters: Set[String],
                pass: Boolean,
            '''
        info_fields (str): For example:
            '''
                AC: Array[Int],
                AF: Array[Double],
                AN: Int,
            '''
    Returns:
        dict: a dictionary that represents the "properties" section of an Elasticsearch mapping.

        For example:
            {
                "AC": {"type": "integer"},
                "AF": {"type": "float"},
                "AN": {"type": "integer"},
            }

    """

    properties = collections.OrderedDict({
        "contig": {"type": "keyword"},
        "start": {"type": "integer"},
        "end": {"type": "integer"},
        "ref": {"type": "keyword"},
        "alt": {"type": "keyword"},
    })

    for fields_string in (top_level_fields, info_fields):
        for field_name, field_type in _parse_fields(fields_string):
            properties[field_name] = {
                "type": _map_vds_type_to_es_type(field_type)
                # other potential settings: "indexed":true,"analyzed":false,"doc_values":true,"searchable":true,"aggregatable":true
            }
    # by default, disable doc values for all fields
    for field_name, field_settings in properties.items():
        field_settings["doc_values"] = False

    for field_name in enable_doc_values_for_fields:
        properties[field_name]["doc_values"] = True
    for field_name in disable_index_for_fields:
        properties[field_name]["index"] = False

    return properties


def export_vds_to_elasticsearch(
        vds,
        export_genotypes=False,
        host="10.48.0.105",   #"elasticsearch-svc" #"localhost" #"k8solo-01"
        port=30001, # "9200"
        index_name="data",
        index_type_name="variant",
        block_size=5000,
        delete_index_before_exporting=True,
        verbose=True,
    ):

    #pprint(vds.variant_schema)
    #pprint(vds.sample_ids)

    parsed_schema = parse_vds_schema(vds.variant_schema.fields, current_parent=["va"])
    site_fields_list = sorted(generate_vds_make_table_arg(parsed_schema))
    if export_genotypes:
        genotype_fields_list = [
            'num_alt = if(g.isCalled) g.nNonRefAlleles else -1',
            'gq = if(g.isCalled) g.gq else NA:Int',
            'ab = let total=g.ad.sum in if(g.isCalled && total != 0) (g.ad[0] / total).toFloat else NA:Float',
            'dp = if(g.isCalled) g.dp else NA:Int',
            #'pl = if(g.isCalled) g.pl else NA:Array[Int]',  # store but don't index
        ]
    else:
        genotype_fields_list = []

    kt = vds.make_table(
        site_fields_list,
        genotype_fields_list,
    )

    export_kt_to_elasticsearch(kt, host, int(port), index_name, index_type_name, block_size, delete_index_before_exporting, verbose)


def export_kt_to_elasticsearch(
        kt,
        host="10.48.0.105",   #"elasticsearch-svc" #"localhost" #"k8solo-01"
        port=30001, # "9200"
        index_name="data",
        index_type_name="variant",
        block_size=5000,
        delete_index_before_exporting=True,
        verbose=True,
    ):

    if verbose:
        pprint(kt.schema)

    parsed_schema = parse_vds_schema(kt.schema.fields, current_parent=["va"])
    elasticsearch_schema = generate_elasticsearch_schema(parsed_schema)

    elasticsearch_mapping = {
        "settings" : {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index.mapping.total_fields.limit": 10000,
        },
        "mappings": {
            "variant": {
                "_all": { "enabled": "false" },
                "properties": elasticsearch_schema,
            },
        }
    }

    es = elasticsearch.Elasticsearch(host, port=port)
    if delete_index_before_exporting and es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
    es.indices.create(index=index_name, body=elasticsearch_mapping)

    kt.export_elasticsearch(host, int(port), index_name, index_type_name, block_size)

    if verbose:
        print_elasticsearch_stats(es)


def print_elasticsearch_stats(es):
    node_stats = es.nodes.stats(level="node")
    node_id = node_stats["nodes"].keys()[0]

    print("==========================")

    for index in es.indices.get('*'):
        print(index)

    print("Indices: %s total docs" % node_stats["nodes"][node_id]["indices"]["docs"]["count"])
    print("Free Memory: %0.1f%% (%d Gb out of %d Gb)" % (
        node_stats["nodes"][node_id]["os"]["mem"]["free_percent"],
        node_stats["nodes"][node_id]["os"]["mem"]["free_in_bytes"]/10**9,
        node_stats["nodes"][node_id]["os"]["mem"]["total_in_bytes"]/10**9,
    ))
    print("Free Disk Space: %0.1f%% (%d Gb out of %d Gb)" % (
        (100*node_stats["nodes"][node_id]["fs"]["total"]["free_in_bytes"]/node_stats["nodes"][node_id]["fs"]["total"]["total_in_bytes"]),
        node_stats["nodes"][node_id]["fs"]["total"]["free_in_bytes"]/10**9,
        node_stats["nodes"][node_id]["fs"]["total"]["total_in_bytes"]/10**9,
    ))

    print("CPU load: %s" % str(node_stats["nodes"][node_id]["os"]["cpu"]["load_average"]))
    print("Swap: %s (bytes used)" % str(node_stats["nodes"][node_id]["os"]["swap"]["used_in_bytes"]))
    print("Disk type: " + ("Regular" if node_stats["nodes"][node_id]["fs"]["total"]["spins"] else "SSD"))
    print("==========================")

    # other potentially interesting fields:
    """
    print("Current HTTP Connections: %s open" % node_stats["nodes"][node_id]["http"]["current_open"])
    [
        u'thread_pool',
        u'transport_address',
        u'http',
        u'name',
        u'roles',
        u'script',
        u'process',
        u'timestamp',
        u'ingest',
        u'breakers',
        u'host',
        u'fs',
        u'jvm',
        u'ip',
        u'indices',
        u'os',
        u'transport',
        u'discovery',
    ]
    """