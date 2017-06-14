import gzip
import os
from xbrowse.utils import get_progressbar

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
            projection={'_id': False}
        )
        if d is None:
            d = {}
        return d

    def add_populations_to_variants(self, variants, population_slug_list):
        """
        variants is a list of annotated variants, this adds more population frequencies to that annotation
        """
        for variant in variants:
            freqs = self.get_frequencies(variant.xpos, variant.ref, variant.alt)
            for slug in population_slug_list:
                if slug in freqs:
                    variant.annotation['freqs'][slug] = freqs[slug]
                else:
                    variant.annotation['freqs'][slug] = 0.0

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
            self.load_population(population)

    def load_population(self, population):
        """
        Take a population and a data source; extract and load it into annotator
        Data source can be VCF file, VCF Counts file, or a counts dir (in the case of ESP data)
        """
        if population['file_type'] == 'vcf':
            if population['file_path'].endswith('.gz'):
                vcf_file = gzip.open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = vcf_file.fileobj
            else:
                vcf_file = open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = vcf_file
            progress = get_progressbar(size, 'Loading vcf: {}'.format(population['slug']))
            for variant in vcf_stuff.iterate_vcf(vcf_file, genotypes=True, genotype_meta=False):
                progress.update(progress_file.tell())
                freq = get_aaf(variant)
                self._add_population_frequency(variant.xpos, variant.ref, variant.alt, population['slug'], freq)
            vcf_file.close()

        elif population['file_type'] == 'sites_vcf':
            if population['file_path'].endswith('.gz'):
                vcf_file = gzip.open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = vcf_file.fileobj
            else:
                vcf_file = open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = vcf_file
            meta_key = population.get('vcf_info_key', 'AF')

            progress = get_progressbar(size, 'Loading sites vcf: {}'.format(population['slug']))
            for variant in vcf_stuff.iterate_vcf(vcf_file, meta_fields=[meta_key,]):
                progress.update(progress_file.tell())
                freq = float(variant.extras.get(meta_key, 0).split(',')[variant.extras['alt_allele_pos']])
                self._add_population_frequency(
                    variant.xpos,
                    variant.ref,
                    variant.alt,
                    population['slug'],
                    freq
                )
            vcf_file.close()

        #
        # Directory of per-chromosome VCFs that ESP publishes
        #
        elif population['file_type'] == 'esp_vcf_dir':
            for filename in os.listdir(population['dir_path']):
                file_path = os.path.abspath(os.path.join(population['dir_path'], filename))
                f = open(file_path)
                file_size = os.path.getsize(file_path)
                progress = get_progressbar(file_size, 'Loading ESP file: {}'.format(filename))
                for variant in get_variants_from_esp_file(f):
                    progress.update(f.tell())
                    self._add_population_frequency(
                        variant['xpos'],
                        variant['ref'],
                        variant['alt'],
                        population['slug'],
                        variant[population['counts_key']]
                    )
                f.close()
        #
        # text file of allele counts, as Monkol has been using for the joint calling data
        #
        elif population['file_type'] == 'counts_file':
            if population['file_path'].endswith('.gz'):
                counts_file = gzip.open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = counts_file.fileobj
            else:
                counts_file = open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = counts_file

            progress = get_progressbar(size, 'Loading population: {}'.format(population['slug']))
            for line in counts_file:
                progress.update(progress_file.tell())
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
            counts_file.close()

        # this is now the canonical allele frequency file -
        # tab separated file with xpos / ref / alt / freq
        elif population['file_type'] == 'xbrowse_freq_file':
            if population['file_path'].endswith('.gz'):
                counts_file = gzip.open(population['file_path'])
                progress_file = counts_file.fileobj
            else:
                counts_file = open(population['file_path'])
                progress_file = counts_file
            size = os.path.getsize(population['file_path'])
            progress = get_progressbar(size, 'Loading population: {}'.format(population['slug']))

            for line in counts_file:
                progress.update(progress_file.tell())
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
            counts_file.close()

        elif population['file_type'] == 'tsv_file':
            if population['file_path'].endswith('.gz'):
                freq_file = gzip.open(population['file_path'])
                progress_file = freq_file.fileobj
            else:
                freq_file = open(population['file_path'])
                progress_file = freq_file
            size = os.path.getsize(population['file_path'])
            progress = get_progressbar(size, 'Loading population: {}'.format(population['slug']))
            header = next(freq_file)
            print("Header: " + header)
            for line in freq_file:
                progress.update(progress_file.tell())
                fields = line.strip('\n').split('\t')
                chrom = fields[0]
                pos = int(fields[1])
                ref = fields[2]
                alt = fields[3]
                freq = float(fields[4])

                xpos = genomeloc.get_single_location(chrom, pos) 
                self._add_population_frequency(
                    xpos,
                    ref,
                    alt,
                    population['slug'],
                    freq
                )
            freq_file.close()

        elif population['file_type'] == 'sites_vcf_with_counts':
            if population['file_path'].endswith('.gz') or population['file_path'].endswith('.bgz'):
                vcf_file = gzip.open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = vcf_file.fileobj
            else:
                vcf_file = open(population['file_path'])
                size = os.path.getsize(population['file_path'])
                progress_file = vcf_file
            ac_info_key = population['ac_info_key']
            an_info_key = population['an_info_key']

            progress = get_progressbar(size, 'Loading sites vcf: {}'.format(population['slug']))
            for variant in vcf_stuff.iterate_vcf(vcf_file, meta_fields=[ac_info_key, an_info_key]):
                progress.update(progress_file.tell())

                alt_allele_pos = variant.extras['alt_allele_pos']  
                try:
                    ac = int(variant.extras.get(ac_info_key).split(',')[alt_allele_pos].replace("NA", "0"))
                except Exception, e:
                    print("Couldn't parse AC value %s from %s: %s" % (alt_allele_pos, ac_info_key, variant.extras), e)
                    continue

                try:
                    if "popmax" in ac_info_key.lower():
                        AN_index = alt_allele_pos  # each allele may have a different AN value from a different population 
                    else:
                        AN_index = 0

                    an = int(variant.extras.get(an_info_key).split(',')[AN_index].replace("NA", "0"))
                except Exception, e:
                    print("Couldn't parse AN value %s from %s: %s" % (alt_allele_pos, an_info_key, variant.extras), e)
                    continue

                if an == 0:
                    freq = 0.0
                else:
                    freq = float(ac)/an
                self._add_population_frequency(
                    variant.xpos,
                    variant.ref,
                    variant.alt,
                    population['slug'],
                    freq
                )
            vcf_file.close()
        else:
            raise ValueError("Unexpected population['file_type']: " + population['file_type'])

    def passes_frequency_filters(self, xpos, ref, alt, frequency_filter_list):
        """
        Does variant defined by (xpos, ref, alt) pass these frequency filters?
        :param xpos:
        :param ref:
        :param alt:
        :param frequency_filter_list: list of (slug, cutoff) tuples
        :return: True or False
        """
        freqs = self.get_frequencies(xpos, ref, alt)
        for slug, cutoff in frequency_filter_list:
            if slug in freqs and freqs[slug] > cutoff:
                return False
        return True



