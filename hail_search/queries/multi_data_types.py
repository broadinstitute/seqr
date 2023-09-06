from hail_search.queries.variants import VariantHailTableQuery
from hail_search.queries.sv import SvHailTableQuery
from hail_search.queries.gcnv import GcnvHailTableQuery

QUERY_CLASS_MAP = {cls.DATA_TYPE: cls for cls in [VariantHailTableQuery, SvHailTableQuery, GcnvHailTableQuery]}
