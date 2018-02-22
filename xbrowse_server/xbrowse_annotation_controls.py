import collections
from xbrowse.core import genomeloc, constants
from xbrowse.core.genomeloc import CHROMOSOMES, get_xpos
from tqdm import tqdm

class CustomAnnotator():

    def __init__(self, settings_module, genome_version=constants.GENOME_VERSION_GRCh37):
        """Constructor.

        Args:
            settings_module (module): eg. imported instance of custom_annotator_settings.py
            genome_version (string): constants.GRCh37 or constants.GRCh38
        """
        self._settings = settings_module
        self._genome_version = genome_version
        self._db = settings_module.db[self._genome_version]
        self._esp_target_filter = None

    def get_annotations_for_variants(self, variant_t_list):

        # start with an empty ordereddict - add each variant as we look it up in the database
        ret = collections.OrderedDict()
        fields_to_include = ['rsid', 'polyphen', 'sift', 'fathmm', 'muttaster']
        for variant_t in variant_t_list:
            doc = self._db.variants.find_one({'xpos': variant_t[0], 'ref': variant_t[1], 'alt': variant_t[2]})

            d = {name: None for name in fields_to_include}
            if doc:
                d = {name: doc.get(name) for name in fields_to_include}

            ret[variant_t] = d

        return ret

    def load(self):
        self.load_dbnsfp()


    def load_dbnsfp(self):
        self._db.drop_collection('variants')
        self._db.variants.ensure_index([('xpos', 1), ('ref', 1), ('alt', 1)])

        # load dbnsfp info
        polyphen_map = {
            'D': 'probably_damaging',
            'P': 'possibly_damaging',
            'B': 'benign',
            '.': None
        }

        sift_map = {
            'D': 'damaging',
            'T': 'tolerated',
            '.': None
        }

        fathmm_map = {
            'D': 'damaging',
            'T': 'tolerated',
            '.': None
        }

        muttaster_map = {
            'A': 'disease_causing',
            'D': 'disease_causing',
            'N': 'polymorphism',
            'P': 'polymorphism',
            '.': None
        }

        def collapse(scores):
            s = set(scores.split(";"))
            if len(s) > 1:
                raise ValueError("Couldn't collapse %s" % str(scores))
            return list(s)[0]

        pred_rank = ['D', 'A', 'T', 'N', 'P', 'B', '.']

        def select_worst(pred_value):
            i = len(pred_rank) - 1
            for pred in pred_value.split(";"):
                r = pred_rank.index(pred)
                if r < i:
                    i = r
            return pred_rank[i]

        for chrom in CHROMOSOMES:
            if chrom == "chrM":
                continue  # no dbNSFP data for chrM

            print "Reading dbNSFP data for {}".format(chrom)
            single_chrom_file = open(self._settings.dbnsfp_dir[self._genome_version] + 'dbNSFP2.9_variant.' + chrom)
            header = single_chrom_file.readline()
            header_fields = header.strip("\n").split()
            field_index = {name: header_fields.index(name) for name in header_fields}

            for i, line in tqdm(enumerate(single_chrom_file)):
                if i == 0:
                    continue
                fields = line.strip('\n').split('\t')
                chrom, pos, ref, alt = fields[:4]
                chrom = 'chr' + chrom
                pos = int(pos)
                xpos = genomeloc.get_single_location(chrom, pos)
                if not xpos:
                    raise ValueError("Unexpected chr, pos: %(chrom)s, %(pos)s" % (chrom, pos))

                rsid = fields[field_index["rs_dbSNP141"]]
                annotations_dict = {
                    'rsid': rsid if rsid != '.' else None,
                    'polyphen': polyphen_map[select_worst(fields[field_index["Polyphen2_HVAR_pred"]])],
                    'sift': sift_map[select_worst(fields[field_index["SIFT_pred"]])],
                    'fathmm': fathmm_map[select_worst(fields[field_index["FATHMM_pred"]])],
                    'muttaster': muttaster_map[select_worst(fields[field_index["MutationTaster_pred"]])],
                    'metasvm': collapse(fields[field_index["MetaSVM_pred"]]),
                    #'cadd_phred': collapse(fields[field_index["CADD_phred"]]),
                }

                self._db.variants.update(
                    {'xpos': xpos, 'ref': ref, 'alt': alt},
                    {'$set': annotations_dict},
                    upsert=True
                )
