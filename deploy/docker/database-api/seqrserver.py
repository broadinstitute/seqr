from hail import *
from hail.utils import *
from hail.seqr import *

import os

solr_host = os.environ['SOLR_SVC_SERVICE_HOST']
solr_port = os.environ['SOLR_SVC_SERVICE_PORT']
solr_port = os.environ['SOLR_SVC_SERVICE_PORT_ZK']

cassandra_host = os.environ['CASSANDRA_SVC_SERVICE_HOST']

print('in seqrserver.py...')

hc = HailContext()

handler = compound_handler(
    solr_search_engine(solr_client('%s:%s' % (solr_host, solr_port), 'seqr_noref')),
    cass_lookup_engine(hc, cassandra_host, 'seqr', 'seqr'))
server = run_server(handler)

print('up and running!')

server.awaitShutdown()
