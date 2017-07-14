import collections


def _parse_fields(fields_string):
    """Takes a string representation of one of the TStructs in a VDS variant_schema and generates a
    list of (field_name, field_type) tuples.

    Args:
        fields_string: For exapmle:
            '''
                rsid: String,
                qual: Double,
                filters: Set[String],
                pass: Boolean,
            '''
    Yields:
        2-tuple:  For example: ("rsid", "String"), ("qual", "Double"), ("filters", "Set[String]") ..
    """
    for field in fields_string.split(','):
        field = field.strip()  # eg. "AF: Array[Double],"
        if not field or field.startswith('---'):
            continue

        field_name, field_type = field.split(": ")

        yield field_name, field_type  # eg. ("AF", "Array[Double]")


# ES types:  (see https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping-types.html)
#   long, integer, short, byte, double, float, half_float, scaled_float, text and keyword, date,
#   boolean, binary, integer_range, float_range, long_range, double_range, date_range

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


def convert_vds_variant_schema_to_annotate_variants_expr(
        top_level_fields="",
        info_fields="",
        root="clean"):
    """Takes a string representation of the VDS variant_schema and generates a string expression
    that can be passed to hail's annotate_variants_expr function to clean up the data shape to:

    1. flatten the data so that VCF "top_level" fields and "INFO" fields now appear at the same level
    2. discard unused fields
    3. convert all Array-type values to a single value in the underlying primitive type by
        applying [va.aIndex - 1]. This assumes that split_multi() has already been run to
        split multi-allelic variants.

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
        root (str): Where to attach the new data shape in the 'va' data struct.

    Returns:
        string:

    """
    expr_lines = []
    for source_root, fields_string in [("va", top_level_fields), ("va.info", info_fields)]:
        for field_name, field_type in _parse_fields(fields_string):
            field_expr = "va.%(root)s.%(field_name)s = %(source_root)s.%(field_name)s" % locals()
            if field_type.startswith("Array"):
                field_expr += "[va.aIndex - 1]"
            expr_lines.append(field_expr)

    return ",\n".join(expr_lines)


def convert_vds_variant_schema_to_es_index_properties(top_level_fields="", info_fields="", vep_fields=""):
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

    return properties


def convert_vds_variant_schema_to_vds_make_table_list_arg(top_level_fields="", info_fields="", vep_fields="", root="clean"):
    """Takes a string representation of the VDS variant schema and converts it to a list that can be
    passed to the vds.make_table(..) function to create a key table.

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
        list: A list of strings

        For example:
            [
                "AC = va.clean.AC",
                "AF = va.clean.AF",
                ...
            ]

    """

    result = [
        "contig = v.contig",
        "start = v.start",
        #"end = v.end",
        "ref = v.ref",
        "alt = v.alt"
    ]

    for fields_string in (top_level_fields, info_fields):
        for field_name, field_type in _parse_fields(fields_string):
            result.append("%(field_name)s = va.%(root)s.%(field_name)s" % locals())

    return result



# TODO figure out why this doesn't work for the base VCF
'''
info_fields_expr = convert_info_fields_to_expr("""
     AC: Array[Int],
     AF: Array[Double],
     AN: Int,
     BaseQRankSum: Double,
     DP: Int,
     DS: Boolean,
     FS: Double,
     HaplotypeScore: Double,
     InbreedingCoeff: Double,
     MQ: Double,
     MQ0: Int,
     MQRankSum: Double,
     QD: Double,
     ReadPosRankSum: Double,
     VQSLOD: Double,
     culprit: String,
""")

expr = """
    va.for_seqr.rsid = va.rsid,
    va.for_seqr.qual = va.qual,
    va.for_seqr.filters = va.filters,
    va.for_seqr.info.CSQ = va.info.CSQ,
""" + info_fields_expr
'''