import collections
from xbrowse.core import genomeloc
from xbrowse.core.genome_subset import create_genome_subset_from_interval_list
from xbrowse import vcf_stuff
from xbrowse.core.genomeloc import CHROMOSOMES


class CustomAnnotator():

    def __init__(self, settings_module):
        self._settings = settings_module
        self._db = settings_module.db
        self._esp_target_filter = None

    def get_annotations_for_variants(self, variant_t_list):

        # start with an empty ordereddict - add each variant as we look it up in the database
        ret = collections.OrderedDict()
        for variant_t in variant_t_list:
            d = {
                'rsid': None,
                'polyphen': None,
                'sift': None,
                'fathmm': None,
                'muttaster': None,
            }
            doc = self._db.variants.find_one({'xpos': variant_t[0], 'ref': variant_t[1], 'alt': variant_t[2]})
            if doc:
                d['rsid'] = doc.get('rsid')
                d['polyphen'] = doc.get('polyphen')
                d['sift'] = doc.get('sift')
                d['fathmm'] = doc.get('fathmm')
                d['muttaster'] = doc.get('muttaster')
            ret[variant_t] = d

        # everything is looked up from database, now move on to calculated annotations

        # esp target
        for variant_t, in_target in self.get_esp_target_filter().filter_variant_list(variant_t_list):
            ret[variant_t]['in_esp_target'] = in_target

        return ret

    def get_esp_target_filter(self):
        if self._esp_target_filter is None:
            self._esp_target_filter = create_genome_subset_from_interval_list(open(self._settings.esp_target_file))
        return self._esp_target_filter

    def load(self):
        self._db.drop_collection('variants')
        self._db.variants.ensure_index([('xpos', 1), ('ref', 1), ('alt', 1)])

        # load dbsnp info
        for i, variant in enumerate(vcf_stuff.iterate_vcf(open(self._settings.dbsnp_vcf_file))):
            if not i % 100000:
                print i
            self._db.variants.update(
                {'xpos': variant.xpos, 'ref': variant.ref, 'alt': variant.alt},
                {'$set': {'rsid': variant.vcf_id}},
                upsert=True
            )

        # load dbnsfp info
        polyphen_map = {
            'D': 'probably_damaging',
            'P': 'possibly_damaging',
            'B': 'benign',
        }

        sift_map = {
            'D': 'damaging',
            'T': 'tolerated',
        }

        fathmm_map = {
            'D': 'damaging',
            'T': 'tolerated',
        }

        muttaster_map = {
            'A': 'disease_causing',
            'D': 'disease_causing',
            'N': 'polymorphism',
            'P': 'polymorphism',
        }

        for chrom in CHROMOSOMES:
            print "Reading dbNSFP data for {}".format(chrom)
            single_chrom_file = open(self._settings.dbnsfp_dir + 'dbNSFP2.9_variant.' + chrom)
            for i, line in enumerate(single_chrom_file):
                if i == 0:
                    continue
                if not i%100000:
                    print i
                fields = line.strip('\n').split('\t')
                chrom, pos, ref, alt = fields[:4]
                chrom = 'chr' + chrom
                pos = int(pos)
                xpos = genomeloc.get_single_location(chrom, pos)
                if not xpos:
                    continue
                polyphen = polyphen_map.get(fields[25])
                sift = sift_map.get(fields[23])
                fathmm = fathmm_map.get(fields[39])
                muttaster = muttaster_map.get(fields[33])

                self._db.variants.update(
                    {'xpos': xpos, 'ref': ref, 'alt': alt},
                    {'$set': {
                        'polyphen': polyphen,
                        'sift': sift,
                        'fathmm': fathmm,
                        'muttaster': muttaster,
                    }},
                    upsert=True
                )
