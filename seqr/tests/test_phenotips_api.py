from django.test import TestCase
from django.http import QueryDict

from seqr.views.phenotips_api import _convert_django_query_dict_to_tuples


class PhenotipsAPITest(TestCase):

    def test_convert_django_query_dict_to_tuples(self):
        result = list(_convert_django_query_dict_to_tuples(QueryDict('a=1&a=2&c=3')))
        self.assertEqual(result, [('a', '1'), ('a', '2'), ('c', '3')])



