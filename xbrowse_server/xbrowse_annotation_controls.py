import collections
import gzip
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
        fields_to_include = ['rsid', 'polyphen', 'sift', 'fathmm', 'muttaster', 'clinvar_rs', 'clinvar_clnsig', 'clinvar_trait']
        for variant_t in variant_t_list:
            doc = self._db.variants.find_one({'xpos': variant_t[0], 'ref': variant_t[1], 'alt': variant_t[2]})

            d = {name: None for name in fields_to_include}
            if doc:
                d = {name: doc.get(name) for name in fields_to_include}


            ret[variant_t] = d

        # everything is looked up from database, now move on to calculated annotations

        # esp target
        #for variant_t, in_target in self.get_esp_target_filter().filter_variant_list(variant_t_list):
        #    ret[variant_t]['in_esp_target'] = in_target

        return ret

    def get_esp_target_filter(self):
        if self._esp_target_filter is None:
            self._esp_target_filter = create_genome_subset_from_interval_list(open(self._settings.esp_target_file))
        return self._esp_target_filter

    def load(self):
        self._db.drop_collection('variants')
        self._db.variants.ensure_index([('xpos', 1), ('ref', 1), ('alt', 1)])

        # load dbsnp info
        #for i, variant in enumerate(vcf_stuff.iterate_vcf(gzip.open(self._settings.dbsnp_vcf_file))):
        #    if not i % 100000:
        #        print i
        #    self._db.variants.update(
        #        {'xpos': variant.xpos, 'ref': variant.ref, 'alt': variant.alt},
        #        {'$set': {'rsid': variant.vcf_id}},
        #        upsert=True
        #    )

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

        interesting_fields = "rs_dbSNP141     Ancestral_allele        SIFT_score      SIFT_converted_rankscore        SIFT_pred       Polyphen2_HDIV_pred     Polyphen2_HVAR_pred     LRT_pred        MutationTaster_pred     MutationAssessor_pred   FATHMM_pred     MetaSVM_pred    MetaLR_pred     VEST3_rankscore PROVEAN_converted_rankscore     PROVEAN_pred    CADD_raw        CADD_raw_rankscore      CADD_phred      GERP++_NR       GERP++_RS       GERP++_RS_rankscore    ESP6500_AA_AF   ESP6500_EA_AF   ARIC5606_AA_AC  ARIC5606_AA_AF  ARIC5606_EA_AC  ARIC5606_EA_AF  ExAC_AC ExAC_AF ExAC_Adj_AC     ExAC_Adj_AF     ExAC_AFR_AC     ExAC_AFR_AF     ExAC_AMR_AC     ExAC_AMR_AF     ExAC_EAS_AC     ExAC_EAS_AF     ExAC_FIN_AC     ExAC_FIN_AF     ExAC_NFE_AC     ExAC_NFE_AF     ExAC_SAS_AC     ExAC_SAS_AF     clinvar_rs      clinvar_clnsig  clinvar_trait"
        interesting_fields = interesting_fields.split()

        for chrom in CHROMOSOMES:
            print "Reading dbNSFP data for {}".format(chrom)
            single_chrom_file = open(self._settings.dbnsfp_dir + 'dbNSFP2.9_variant.' + chrom)
            header = single_chrom_file.readline()
            header_fields = header.strip("\n").split("\t")
            field_index = {name : header_fields.index(name) for name in interesting_fields}


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
                    raise ValueError("Unexpected chr, pos: %(chrom)s, %(pos)s" % (chrom, pos))

                annotations_dict = {
                    'rsid' : fields[field_index["rs_dbSNP141"]],
                    'polyphen': polyphen_map[fields[field_index["Polyphen2_HVAR_pred"]]],
                    'sift': sift_map[fields[field_index["SIFT_pred"]]],
                    'fathmm': fathmm_map[fields[field_index["FATHMM_pred"]]],
                    'muttaster': muttaster_map[fields[field_index["MutationTaster_pred"]]],
                    'metasvm': muttaster_map[fields[field_index["MetaSVM_pred"]]],
                    'cadd_phred': muttaster_map[fields[field_index["CADD_phred"]]],
                }

                extras_to_add_now = ["clinvar_rs", "clinvar_clnsig", "clinvar_trait"]
                for name in extras_to_add_now:
                    annotations_dict[name] = fields[field_index[name]]

                self._db.variants.update(
                    {'xpos': xpos, 'ref': ref, 'alt': alt},
                    {'$set': annotations_dict},
                    upsert=True
                )
