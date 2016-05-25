import csv

import pymongo
from django.conf import settings
from xbrowse.core import genomeloc


class CNVStore():

    def __init__(self, db_conn, reference):
        self.reference = reference
        self._db = db_conn

    def get_sample_ids(self):
        return [s['sample_id'] for s in self._db.samples.find()]

    def get_sample_status(self, sample_id):
        sample_doc = self._db.samples.find_one({'sample_id': sample_id})
        if not sample_doc:
            return None
        return sample_doc['status']

    def get_sample_statuses(self, sample_id_list):
        ret = {sample_id: None for sample_id in sample_id_list}
        for sample_doc in self._db.samples.find({'sample_id': {'$in': sample_id_list}}):
            ret[sample_doc['sample_id']] = sample_doc['status']
        return ret

    def add_sample(self, sample_id, cnv_file):
        """
        """
        print "Adding CNVs for %s" % sample_id
        self.remove_sample(sample_id)
        self._db.cnvs.ensure_index([('sample_id', 1), ('genes', 1)])  # silly to have this here

        self._db.samples.insert({
            'sample_id': str(sample_id),
            'status': 'loading',
        })

        reader = csv.reader(cnv_file)
        reader.next()
        for row in reader:
            chrom = 'chr' + row[7]
            start = int(row[5])
            stop = int(row[6])
            xstart = genomeloc.get_single_location(chrom, start)
            xstop = genomeloc.get_single_location(chrom, stop)
            cnv = {
                'sample_id': sample_id,
                'type': row[3],
                'nexons': int(row[4]),
                'xstart': xstart,
                'xstop': xstop,
                'genes': self.reference.get_genes_in_region(xstart, xstop),
                'reads': [int(row[10]), int(row[11])],
                'read_ratio': float(row[12]),
            }
            self._db.cnvs.insert(cnv)

    def remove_sample(self, sample_id):
        self._db.samples.remove({'sample_id': sample_id})
        self._db.cnvs.remove({'sample_id': sample_id})

    def get_cnvs_for_gene(self, sample_id, gene_id):
        genes = self._db.cnvs.find({
            'genes': gene_id,
            'sample_id': sample_id,
        }, projection={'_id': False, 'sample_id': False})
        return list(genes)