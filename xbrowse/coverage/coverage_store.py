import utils


class CoverageDatastore(object):
    """
    This is the main class
    """

    def __init__(self, db, reference):
        """
        Takes a pymongo Database to start
        Should be empty - unsure what collections will be used
        """
        self._db = db
        self._reference = reference
        self._coding_regions = None

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

    def add_sample(self, sample_id, coverage_file):
        """
        Adds an individual with data from coverage_file
        Idempotent - will overwrite any data already in there for sample_id
        Args:
            sample_id (str): arbitrary identifier for this sample
            coverage_file (file):
        """
        print "Adding coverage for %s" % sample_id
        self.remove_sample(sample_id)

        self._db.samples.insert({
            'sample_id': str(sample_id),
            'status': 'loading',
        })

        if self._coding_regions is None:
            self._coding_regions = self._reference.get_all_coding_regions_sorted()

        for coverage in utils.iterate_coding_region_coverages(coverage_file, iter(self._coding_regions)):
            doc = dict(
                coding_region=coverage['coding_region']._asdict(),
                totals=coverage['totals'],
                coverage_list=[c._asdict() for c in coverage['coverage_list']],
                sample_id=sample_id,
                gene_id=coverage['coding_region'].gene_id
            )
            self._db.exons.insert(doc)

        self._db.samples.update({'sample_id': sample_id}, {'$set': {'status': 'loaded'}})

    def remove_sample(self, sample_id):
        self._db.exons.remove({'sample_id': sample_id})
        self._db.samples.remove({'sample_id': sample_id})

    def ensure_indices(self):
        self._db.exons.ensure_index([('sample_id', 1), ('gene_id', 1)])

    def get_coverage_for_gene(self, sample_id, gene_id):
        """
        List of coverages for each coding region in a gene
        """
        docs = self._db.exons.find({'sample_id': sample_id, 'gene_id': gene_id}, fields={'_id': False})
        coverage_specs = sorted(docs, key=lambda x: x['coding_region']['index_in_gene'])
        totals = utils.get_totals_for_coding_region_list(coverage_specs)
        return {
            'coverage_specs': coverage_specs,
            'gene_totals': totals
        }

    def get_coverage_totals_for_gene(self, gene_id, sample_ids):
        """
        Get total coverage in this gene across sample_ids
        """
        coverages = {}
        for sample_id in sample_ids:
            coverages[sample_id] = self.get_coverage_for_gene(sample_id, gene_id)
        total = {'callable': 0, 'low_coverage': 0, 'poor_mapping': 0}
        for coverage_spec in coverages.values():
            total['callable'] += coverage_spec['gene_totals']['callable']
            total['low_coverage'] += coverage_spec['gene_totals']['low_coverage']
            total['poor_mapping'] += coverage_spec['gene_totals']['poor_mapping']
        return total

