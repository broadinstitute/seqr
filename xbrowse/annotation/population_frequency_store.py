import gzip
import os

from xbrowse import vcf_stuff
from xbrowse.utils import get_aaf
from xbrowse.parsers.esp_vcf import get_variants_from_esp_file
from xbrowse.core import genomeloc


class PopulationFrequencyStore():

    def __init__(self, db_conn, reference_populations):
        self._db = db_conn
        self.reference_populations = reference_populations

    def get_frequencies(self, xpos, ref, alt):
        d = self._db.pop_variants.find_one(
            {'xpos': xpos, 'ref': ref, 'alt': alt},
            fields={'_id': False}
        )
        if d is None:
            d = {}
        return d

    def load(self):
        """
        Load up the database from settings_module
        """
        self._db.drop_collection('pop_variants')
        self._ensure_indices()
        self.load_populations(self.reference_populations)

    def _ensure_indices(self):
        self._db.pop_variants.ensure_index([('xpos', 1), ('ref', 1), ('alt', 1)])

    def _add_population_frequency(self, xpos, ref, alt, population, freq):
        self._db.pop_variants.update(
            {'xpos': xpos, 'ref': ref, 'alt': alt},
            {'$set': {population: freq}},
            upsert=True
        )

    def load_populations(self, population_list):
        """
        Load all the populations described in population_list into annotator
        TODO: create example-settings.py that shows format
        """
        for population in population_list:
            print "Loading populaiton: {}".format(population['slug'])
            self.load_population_to_annotator(population)

    def load_population_to_annotator(self, population):
        """
        Take a population and a data source; extract and load it into annotator
        Data source can be VCF file, VCF Counts file, or a counts dir (in the case of ESP data)
        """
        if population['file_type'] == 'vcf':
            if population['file_path'].endswith('.gz'):
                vcf_file = gzip.open(population['file_path'])
            else:
                vcf_file = open(population['file_path'])
            for i, variant in enumerate(vcf_stuff.iterate_vcf(vcf_file, genotypes=True, genotype_meta=False)):
                if i % 10000 == 0:
                    print i
                freq = get_aaf(variant)
                self._add_population_frequency(variant.xpos, variant.ref, variant.alt, population['slug'], freq)
        elif population['file_type'] == 'sites_vcf':
            if population['file_path'].endswith('.gz'):
                vcf_file = gzip.open(population['file_path'])
            else:
                vcf_file = open(population['file_path'])
            meta_key = population['vcf_info_key']
            for i, variant in enumerate(vcf_stuff.iterate_vcf(vcf_file, meta_fields=[meta_key,])):
                if i % 10000 == 0:
                    print i
                freq = float(variant.extras.get(meta_key, 0))
                self._add_population_frequency(
                    variant.xpos,
                    variant.ref,
                    variant.alt,
                    population['slug'],
                    freq
                )

        #
        # Directory of per-chromosome VCFs that ESP publishes
        #
        elif population['file_type'] == 'esp_vcf_dir':
            for filename in os.listdir(population['dir_path']):
                print "Adding %s" % filename
                file_path = os.path.abspath(os.path.join(population['dir_path'], filename))
                f = open(file_path)
                for i, variant in enumerate(get_variants_from_esp_file(f)):
                    if i % 10000 == 0:
                        print i
                    self._add_population_frequency(
                        variant['xpos'],
                        variant['ref'],
                        variant['alt'],
                        population['slug'],
                        variant[population['counts_key']]
                    )

        #
        # text file of allele counts, as Monkol has been using for the joint calling data
        #
        elif population['file_type'] == 'counts_file':
            if population['file_path'].endswith('.gz'):
                counts_file = gzip.open(population['file_path'])
            else:
                counts_file = open(population['file_path'])
            for i, line in enumerate(counts_file):
                if i % 10000 == 0:
                    print i
                fields = line.strip('\n').split('\t')
                chrom = 'chr' + fields[0]
                pos = int(fields[1])
                xpos = genomeloc.get_single_location(chrom, pos)
                ref = fields[2]
                alt = fields[3]
                if int(fields[5]) == 0:
                    continue
                freq = float(fields[4]) / float(fields[5])
                self._add_population_frequency(
                    xpos,
                    ref,
                    alt,
                    population['slug'],
                    freq
                )

        # this is now the canonical allele frequency file -
        # tab separated file with xpos / ref / alt / freq
        elif population['file_type'] == 'xbrowse_freq_file':
            if population['file_path'].endswith('.gz'):
                counts_file = gzip.open(population['file_path'])
            else:
                counts_file = open(population['file_path'])
            for i, line in enumerate(counts_file):
                if i % 10000 == 0:
                    print i
                fields = line.strip('\n').split('\t')
                xpos = int(fields[0])
                ref = fields[1]
                alt = fields[2]
                freq = float(fields[3])
                self._add_population_frequency(
                    xpos,
                    ref,
                    alt,
                    population['slug'],
                    freq
                )