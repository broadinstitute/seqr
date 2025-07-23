from collections import defaultdict

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand
from django.db.models import F
import logging
import re

from clickhouse_search.search import get_clickhouse_key_lookup
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import SavedVariant, Sample
from seqr.utils.file_utils import file_iter
from seqr.utils.search.utils import parse_variant_id

logger = logging.getLogger(__name__)

GCNV_CALLSET_PATH = 'gs://seqr-datasets-gcnv/GRCh38/RDG_WES_Broad_Internal/v4/CMG_gCNV_2022_annotated.ensembl.round2_3.strvctvre.tsv.gz'

SV_ID_UPDATE_MAP = {
    'WGS': {
        'CMG.phase1_CMG_DEL_chr10_2038': 'phase2_DEL_chr10_4611',
        'CMG.phase1_CMG_DEL_chr11_2963': 'phase2_DEL_chr11_5789',
        'CMG.phase1_CMG_DEL_chr13_153': 'phase2_DEL_chr13_378',
        'cohort_2911.chr1.final_cleanup_BND_chr1_1167': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_1376',
        'cohort_2911.chr1.final_cleanup_BND_chr1_1017': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_1208',
        'cohort_2911.chr1.final_cleanup_BND_chr1_2837': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_3326',
        'cohort_2911.chr1.final_cleanup_DEL_chr1_12237': 'phase2_DEL_chr1_9347',
        'cohort_2911.chr1.final_cleanup_DEL_chr1_2953': 'phase2_DEL_chr1_2503',
        'cohort_2911.chrX.final_cleanup_CPX_chrX_20': 'cohort_2911.chrX.final_cleanup_CPX_chrX_19',
        'phase2_DUP_chr1_1164': 'phase4_all_batches.chr1.final_cleanup_DUP_chr1_1666',
        'phase2_CPX_chr1_73': 'phase4_all_batches.chr1.final_cleanup_CPX_chr1_85',
        'cohort_2911.chr1.final_cleanup_DEL_chr1_3844': 'phase2_DEL_chr1_3148',
        'cohort_2911.chr1.final_cleanup_DEL_chr1_4181': 'phase2_DEL_chr1_3389',
        'cohort_2911.chr1.final_cleanup_DEL_chr1_6414': 'phase2_DEL_chr1_5030',
        'cohort_2911.chr10.final_cleanup_DEL_chr10_6275': 'phase2_DEL_chr10_4600',
        'cohort_2911.chr10.final_cleanup_DEL_chr10_7793': 'phase2_DEL_chr10_5695',
        'cohort_2911.chr10.final_cleanup_DUP_chr10_1491': 'phase2_DUP_chr10_1234',
        'cohort_2911.chr10.final_cleanup_DUP_chr10_3659': 'phase2_DUP_chr10_3132',
        'cohort_2911.chr11.final_cleanup_DUP_chr11_3003': 'phase2_DUP_chr11_2757',
        'cohort_2911.chr12.final_cleanup_DEL_chr12_244': 'phase2_DEL_chr12_207',
        'cohort_2911.chr12.final_cleanup_DEL_chr12_5405': 'phase2_DEL_chr12_4072',
        'cohort_2911.chr12.final_cleanup_INS_chr12_42': 'phase4_all_batches.chr12.final_cleanup_INS_chr12_61',
        'cohort_2911.chr14.final_cleanup_DEL_chr14_1513': 'phase2_DEL_chr14_1140',
        'cohort_2911.chr14.final_cleanup_DEL_chr14_2595': 'phase2_DEL_chr14_1998',
        'cohort_2911.chr15.final_cleanup_DEL_chr15_3281': 'phase2_DEL_chr15_2486',
        'cohort_2911.chr16.final_cleanup_DEL_chr16_5308': 'phase2_DEL_chr16_4074',
        'cohort_2911.chr17.final_cleanup_BND_chr17_209': 'phase4_all_batches.chr17.final_cleanup_BND_chr17_250',
        'cohort_2911.chr16.final_cleanup_BND_chr16_635': 'phase4_all_batches.chr16.final_cleanup_BND_chr16_744',
        'cohort_2911.chr17.final_cleanup_CPX_chr17_79': 'phase2_CPX_chr17_46',
        'cohort_2911.chr17.final_cleanup_DEL_chr17_306': 'phase2_DEL_chr17_271',
        'cohort_2911.chr17.final_cleanup_DEL_chr17_3161': 'phase2_DEL_chr17_2627',
        'cohort_2911.chr17.final_cleanup_DEL_chr17_4111': 'phase2_DEL_chr17_3390',
        'cohort_2911.chr17.final_cleanup_DEL_chr17_5157': 'phase2_DEL_chr17_4242',
        'cohort_2911.chr18.final_cleanup_DEL_chr18_3519': 'phase2_DEL_chr18_2585',
        'cohort_2911.chr19.final_cleanup_BND_chr19_162': 'phase4_all_batches.chr19.final_cleanup_BND_chr19_185',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_3395': 'phase2_DEL_chrX_2020',
        'cohort_2911.chr19.final_cleanup_DEL_chr19_1825': 'phase2_DEL_chr19_1567',
        'cohort_2911.chr19.final_cleanup_DEL_chr19_3787': 'phase2_DEL_chr19_3203',
        'cohort_2911.chr19.final_cleanup_DEL_chr19_807': 'phase2_DEL_chr19_692',
        'cohort_2911.chr19.final_cleanup_DEL_chr19_971': 'phase2_DEL_chr19_832',
        'cohort_2911.chr2.final_cleanup_DEL_chr2_7485': 'phase2_DEL_chr2_5601',
        'cohort_2911.chr20.final_cleanup_DEL_chr20_37': 'phase2_DEL_chr20_25',
        'cohort_2911.chr20.final_cleanup_INV_chr20_6': 'phase2_INV_chr20_3',
        'cohort_2911.chr22.final_cleanup_DEL_chr22_1440': 'phase2_DEL_chr22_1210',
        'cohort_2911.chr3.final_cleanup_DUP_chr3_566': 'phase2_DUP_chr3_522',
        'cohort_2911.chr4.final_cleanup_DEL_chr4_5267': 'phase2_DEL_chr4_3794',
        'cohort_2911.chr6.final_cleanup_DEL_chr6_9094': 'phase2_DEL_chr6_6868',
        'cohort_2911.chr7.final_cleanup_DEL_chr7_1540': 'phase2_DEL_chr7_1311',
        'cohort_2911.chr8.final_cleanup_DEL_chr8_75': 'phase2_DEL_chr8_67',
        'cohort_2911.chr8.final_cleanup_DEL_chr8_7934': 'phase2_DEL_chr8_5754',
        'cohort_2911.chr9.final_cleanup_DEL_chr9_6983': 'phase2_DEL_chr9_5130',
        'cohort_2911.chrX.final_cleanup_BND_chrX_166': 'phase4_all_batches.chrX.final_cleanup_BND_chrX_227',
        'cohort_2911.chrX.final_cleanup_CPX_chrX_106': 'cohort_2911.chrX.final_cleanup_CPX_chrX_105',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_1861': 'phase2_DEL_chrX_1151',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_1922': 'phase2_DEL_chrX_1184',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_1936': 'phase2_DEL_chrX_1194',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_1974': 'phase2_DEL_chrX_1222',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_2607': 'phase2_DEL_chrX_1550',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_2882': 'phase2_DEL_chrX_1715',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_3450': 'phase2_DEL_chrX_2061',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_6616': 'phase2_DEL_chrX_3880',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_7868': 'phase2_DEL_chrX_4582',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_7872': 'phase2_DEL_chrX_4585',
        'cohort_2911.chrX.final_cleanup_DEL_chrX_7882': 'phase2_DEL_chrX_4594',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_1102': 'phase2_DUP_chrX_1000',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_1791': 'phase2_DUP_chrX_1595',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_2682': 'phase2_DUP_chrX_2394',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_3233': 'phase2_DUP_chrX_2875',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_3564': 'phase2_DUP_chrX_3160',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_3599': 'phase2_DUP_chrX_3192',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_3621': 'phase2_DUP_chrX_3211',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_600': 'phase2_DUP_chrX_554',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_656': 'phase2_DUP_chrX_606',
        'cohort_2911.chrX.final_cleanup_DUP_chrX_818': 'phase2_DUP_chrX_743',
        'phase2_BND_chr17_485': 'phase4_all_batches.chr17.final_cleanup_BND_chr17_710',
        'phase2_BND_chr1_1262': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_1669',
        'phase2_BND_chr1_19': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_25',
        'phase2_BND_chr4_1666': 'phase4_all_batches.chr4.final_cleanup_BND_chr4_2264',
        'phase2_BND_chr5_1124': 'phase4_all_batches.chr5.final_cleanup_BND_chr5_1476',
        'phase2_DUP_chr11_942': 'phase4_all_batches.chr11.final_cleanup_DUP_chr11_1405',
    },
    'WES': {
        'R4_variant_7334_DUP_08162023': 'R4_variant_7334_DUP',
        'prefix_112949_DEL': 'suffix_210553_DEL',
        'prefix_131670_DUP': 'suffix_251025_DUP',
        'suffix_19443_DEL_2': 'suffix_20030_DEL',
        'prefix_184342_DEL': 'suffix_194439_DEL',
        'prefix_255018_DEL': 'suffix_155939_DEL',
        'prefix_188042_DUP': 'suffix_107531_DUP',
        'suffix_104367_DUP_2': 'suffix_107531_DUP',
        'prefix_59865_DEL': 'suffix_124465_DEL',
        'suffix_120814_DEL_2': 'suffix_124465_DEL',
        'prefix_152595_DEL': 'suffix_286580_DEL',
        'suffix_277504_DEL_2': 'suffix_286581_DEL',
        'prefix_185630_DEL': 'suffix_217490_DEL',
        'suffix_210888_DEL_2': 'suffix_217490_DEL',
        'prefix_126071_DUP': 'suffix_48694_DUP',
        'suffix_47226_DUP_2': 'suffix_48694_DUP',
        'prefix_177696_DUP': 'suffix_23_DUP',
        'prefix_33049_DEL': 'suffix_123373_DEL',
        'suffix_119753_DEL_2': 'suffix_123373_DEL',
        'prefix_6968_DUP': 'suffix_8158_DUP',
        'prefix_111128_DEL': 'suffix_124250_DEL',
        'prefix_265455_DEL': 'suffix_124250_DEL',
        'prefix_133233_DEL': 'suffix_149757_DEL',
        'suffix_145373_DEL_2': 'suffix_149757_DEL',
        'prefix_104962_DEL': 'suffix_262703_DEL',
        'prefix_230669_DUP': 'suffix_37212_DUP',
        'prefix_195634_DUP': 'suffix_337680_DUP',
        'suffix_326904_DUP_2': 'suffix_337680_DUP',
        'prefix_252896_DUP': 'suffix_154760_DUP',
        'prefix_252895_DUP': 'suffix_150484_DUP',
        'prefix_192808_DUP': 'suffix_182662_DUP',
        'prefix_31312_DUP': 'suffix_343278_DUP',
        'suffix_332369_DUP_2': 'suffix_343278_DUP',
        'prefix_201559_DEL': 'suffix_228780_DEL',
        'prefix_173086_DEL': 'suffix_195404_DEL',
        'prefix_230567_DEL': 'suffix_261336_DEL',
        'prefix_25206_DEL': 'suffix_27995_DEL',
        'prefix_72517_DEL': 'suffix_27995_DEL',
        'prefix_194936_DUP': 'suffix_220746_DUP',
        'prefix_117065_DEL': 'suffix_131048_DEL',
        'suffix_127235_DEL_2': 'suffix_131048_DEL',
        'prefix_168621_DEL': 'suffix_336993_DEL',
        'prefix_297236_DEL': 'suffix_336993_DEL',
        'prefix_198998_DUP': 'suffix_225862_DUP',
        'prefix_239300_DUP': 'suffix_271302_DUP',
        'prefix_236836_DEL': 'suffix_268435_DEL',
        'prefix_31131_DUP': 'suffix_34872_DUP',
        'prefix_238314_DEL': 'suffix_336979_DEL',
        'prefix_75798_DUP': 'suffix_84697_DUP',
        'prefix_261715_DEL': 'suffix_337689_DEL',
        'prefix_183989_DEL': 'suffix_4946_DEL',
        'prefix_26448_DEL': 'suffix_43066_DEL',
        'suffix_41786_DEL_2': 'suffix_43066_DEL',
        'prefix_103176_DEL': 'suffix_114811_DEL',
        'suffix_111479_DEL_2': 'suffix_114811_DEL',
        'prefix_120528_DEL': 'suffix_135375_DEL',
        'prefix_296302_DEL': 'suffix_335637_DEL',
        'prefix_108274_DEL': 'suffix_121089_DEL',
        'prefix_46615_DEL': 'suffix_118481_DEL',
        'prefix_185022_DUP': 'suffix_12708_DUP',
        'suffix_12284_DUP_2': 'suffix_12708_DUP',
        'prefix_252585_DUP': 'suffix_309117_DUP',
        'suffix_299264_DUP_2': 'suffix_309117_DUP',
        'prefix_80031_DUP': 'suffix_241944_DUP',
        'suffix_234357_DUP_2': 'suffix_241944_DUP',
        'prefix_117179_DEL': 'suffix_131305_DEL',
        'prefix_71499_DUP': 'suffix_330986_DUP',
        'suffix_320433_DUP_2': 'suffix_330986_DUP',
        'prefix_24788_DUP': 'suffix_336670_DUP',
        'suffix_325911_DUP_2': 'suffix_336670_DUP',
        'prefix_192365_DUP': 'suffix_139090_DUP',
        'prefix_255360_DUP': 'suffix_337082_DUP',
        'prefix_237614_DEL': 'suffix_269379_DEL',
        'prefix_284003_DEL': 'suffix_321174_DEL',
        'suffix_12426_DEL_2': 'suffix_12852_DEL',
        'prefix_9852_DEL': 'suffix_12852_DEL',
        'suffix_50042_DEL_2': 'suffix_51609_DEL',
        'prefix_223675_DEL': 'suffix_51609_DEL',
        'prefix_175156_DEL': 'suffix_54122_DEL',
        'suffix_52499_DEL_2': 'suffix_54122_DEL',
        'prefix_3138_DEL': 'suffix_109381_DEL',
        'suffix_106163_DEL_2': 'suffix_109381_DEL',
        'prefix_255276_DEL': 'suffix_93464_DEL',
        'prefix_152594_DEL': 'suffix_286542_DEL',
        'prefix_77396_DEL': 'suffix_287070_DEL',
        'prefix_152599_DEL': 'suffix_287163_DEL',
        'prefix_152600_DEL': 'suffix_287381_DEL',
        'prefix_108317_DEL': 'suffix_161791_DEL',
        'prefix_201562_DEL': 'suffix_168210_DEL',
        'suffix_163193_DEL_2': 'suffix_168210_DEL',
        'prefix_246635_DEL': 'suffix_92687_DEL',
        'suffix_89974_DEL_2': 'suffix_92687_DEL',
        'prefix_246642_DEL': 'suffix_93299_DEL',
        'suffix_90573_DEL_2': 'suffix_93299_DEL',
        'prefix_246674_DUP': 'suffix_126676_DUP',
        'suffix_122983_DUP_2': 'suffix_126676_DUP',
        'prefix_199389_DEL': 'suffix_94004_DEL',
        'prefix_3593_DEL': 'suffix_27094_DEL',
        'prefix_100725_DEL': 'suffix_336955_DEL',
        'prefix_297227_DEL': 'suffix_336980_DEL',
        'prefix_179648_DEL': 'suffix_202719_DEL',
        'prefix_143182_DEL': 'suffix_100756_DEL',
        'prefix_34890_DEL': 'suffix_38919_DEL',
        'prefix_36703_DEL': 'suffix_39815_DEL',
        'prefix_164553_DEL': 'suffix_185929_DEL',
        'prefix_132206_DEL': 'suffix_282692_DEL',
        'suffix_273714_DEL_2': 'suffix_282692_DEL',
        'prefix_144442_DEL': 'suffix_282716_DEL',
        'suffix_273738_DEL_2': 'suffix_282716_DEL',
        'suffix_273732_DEL_2': 'suffix_282710_DEL',
        'prefix_6326_DEL': 'suffix_282710_DEL',
        'prefix_178200_DEL': 'suffix_118870_DEL',
        'suffix_115409_DEL_2': 'suffix_118870_DEL',
        'prefix_254507_DUP': 'suffix_283948_DUP',
        'prefix_254510_DUP': 'suffix_39298_DUP',
        'prefix_13260_DEL': 'suffix_38202_DEL',
        'suffix_37073_DEL_2': 'suffix_38202_DEL',
        'prefix_278497_DEL': 'suffix_338533_DEL',
        'suffix_327734_DEL_2': 'suffix_338533_DEL',
        'prefix_242131_DEL': 'suffix_176483_DEL',
        'suffix_171236_DEL_2': 'suffix_176483_DEL',
        'suffix_32210_DEL_2': 'suffix_33192_DEL',
        'prefix_37286_DEL': 'suffix_33192_DEL',
        'prefix_113302_DUP': 'suffix_236396_DUP',
        'suffix_228996_DUP_2': 'suffix_236396_DUP',
        'prefix_154396_DEL': 'suffix_174270_DEL',
        'prefix_71769_DEL': 'suffix_227830_DEL',
        'suffix_220764_DEL_2': 'suffix_227830_DEL',
        'prefix_44455_DEL': 'suffix_50096_DEL',
        'prefix_135473_DEL': 'suffix_152259_DEL',
        'prefix_83881_DUP': 'suffix_93771_DUP',
        'prefix_185180_DEL': 'suffix_190807_DEL',
        'prefix_230340_DEL': 'suffix_217490_DEL',
        'prefix_98781_DUP': 'suffix_118080_DUP',
        'suffix_333515_DEL_2': 'suffix_344457_DEL',
        'prefix_50567_DEL': 'suffix_344457_DEL',
        'suffix_243997_DEL_2': 'suffix_251931_DEL',
        'prefix_185688_DEL': 'suffix_251931_DEL',
        'prefix_185697_DEL': 'suffix_252985_DEL',
        'suffix_245019_DEL_2': 'suffix_252985_DEL',
        'prefix_185700_DEL': 'suffix_253165_DEL',
        'suffix_245194_DEL_2': 'suffix_253165_DEL',
        'prefix_164600_DUP': 'suffix_33272_DUP',
        'suffix_32287_DUP_2': 'suffix_33272_DUP',
        'prefix_239826_DUP': 'suffix_339672_DUP',
        'suffix_328837_DUP_2': 'suffix_339672_DUP',
        'prefix_239847_DUP': 'suffix_341812_DUP',
        'suffix_330933_DUP_2': 'suffix_341812_DUP',
        'suffix_217083_DUP_2': 'suffix_223945_DUP',
        'prefix_78332_DUP': 'suffix_223945_DUP',
        'prefix_81687_DUP': 'suffix_132894_DUP',
        'suffix_129007_DUP_2': 'suffix_132894_DUP',
        'suffix_150605_DEL_2': 'suffix_155170_DEL',
        'prefix_47681_DEL': 'suffix_155170_DEL',
        'suffix_119752_DUP_2': 'suffix_123374_DUP',
        'prefix_75741_DUP': 'suffix_123374_DUP',
        'prefix_17370_DUP': 'suffix_19297_DUP',
        'prefix_54006_DUP': 'suffix_19297_DUP',
        'prefix_137115_DUP': 'suffix_67761_DUP',
        'suffix_65769_DUP_2': 'suffix_67761_DUP',
        'prefix_127018_DUP': 'suffix_183995_DUP',
        'prefix_179697_DUP': 'suffix_183995_DUP',
        'prefix_65335_DEL': 'suffix_334692_DEL',
        'prefix_26523_DEL': 'suffix_92931_DEL',
        'suffix_90209_DEL_2': 'suffix_92931_DEL',
        'prefix_121355_DEL': 'suffix_310958_DEL',
        'prefix_3970_DEL': 'suffix_311681_DEL',
        'prefix_16643_DEL': 'suffix_337172_DEL',
        'suffix_326410_DEL_2': 'suffix_337172_DEL',
        'prefix_98251_DEL': 'suffix_179586_DEL',
        'suffix_174257_DEL_2': 'suffix_179586_DEL',
        'prefix_302982_DUP': 'suffix_344928_DUP',
        'prefix_78630_DUP': 'suffix_344928_DUP',
        'prefix_248115_DEL': 'suffix_344177_DEL',
        'prefix_60051_DUP': 'suffix_338928_DUP',
        'suffix_328124_DUP_2': 'suffix_338928_DUP',
        'prefix_202120_DUP': 'suffix_10024_DUP',
        'prefix_137202_DEL': 'suffix_105069_DEL',
        'suffix_101981_DEL_2': 'suffix_105069_DEL',
        'suffix_312453_DEL_2': 'suffix_322732_DEL',
        'prefix_101760_DEL': 'suffix_322732_DEL',
        'prefix_164827_DUP': 'suffix_67293_DUP',
        'prefix_164831_DEL': 'suffix_223792_DEL',
        'suffix_216934_DEL_2': 'suffix_223792_DEL',
        'prefix_47704_DEL': 'suffix_24051_DEL',
        'prefix_108297_DEL': 'suffix_155176_DEL',
        'prefix_284632_DEL': 'suffix_155176_DEL',
        'prefix_37083_DUP': 'suffix_246174_DUP',
        'prefix_37090_DUP': 'suffix_246928_DUP',
        'prefix_37105_DUP': 'suffix_247737_DUP',
        'prefix_164627_DEL': 'suffix_308855_DEL',
        'prefix_164630_DUP': 'suffix_309488_DUP',
        'prefix_247841_DUP': 'suffix_310746_DUP',
        'prefix_164644_DUP': 'suffix_311682_DUP',
        'suffix_301772_DUP_2': 'suffix_311682_DUP',
        'prefix_137780_DEL': 'suffix_223761_DEL',
        'prefix_12281_DEL': 'suffix_30168_DEL',
        'suffix_29274_DEL_2': 'suffix_30168_DEL',
        'prefix_202150_DEL': 'suffix_5892_DEL',
        'prefix_249235_DUP': 'suffix_178512_DUP',
        'suffix_173214_DUP_2': 'suffix_178512_DUP',
        'prefix_286336_DUP': 'suffix_137695_DUP',
        'suffix_133674_DUP_2': 'suffix_137695_DUP',
        'prefix_202153_DUP': 'suffix_217142_DUP',
        'suffix_210547_DUP_2': 'suffix_217142_DUP',
        'suffix_101293_DUP_2': 'suffix_104364_DUP',
        'prefix_240446_DUP': 'suffix_104364_DUP',
        'suffix_326211_DEL_2': 'suffix_336972_DEL',
        'suffix_214414_DUP_2': 'suffix_221162_DUP',
        'suffix_264403_DUP_2': 'suffix_273062_DUP',
        'suffix_92903_DEL_2': 'suffix_95683_DEL',
        'suffix_326915_DEL_2': 'suffix_337695_DEL',
        'suffix_432_DEL_2': 'suffix_442_DEL',
        'suffix_96995_DEL_2': 'suffix_99914_DEL',
        'suffix_16343_DEL_2': 'suffix_16857_DEL',
        'suffix_239134_DUP_2': 'suffix_246928_DUP',
        'suffix_239928_DUP_2': 'suffix_247737_DUP',
        'suffix_299627_DUP_2': 'suffix_309488_DUP',
        'suffix_300851_DUP_2': 'suffix_310746_DUP',
        'prefix_100003_DEL': 'suffix_183787_DEL',
        'prefix_101443_DEL': 'suffix_308476_DEL',
        'prefix_10035_DEL': 'suffix_191074_DEL',
        'prefix_102085_DUP': 'suffix_258879_DUP',
        'prefix_102166_DUP': 'suffix_308496_DUP',
        'prefix_102435_DEL': 'suffix_4265_DEL',
        'prefix_102446_DEL': 'suffix_8242_DEL',
        'prefix_102604_DEL': 'suffix_114190_DEL',
        'prefix_10313_DEL': 'suffix_282612_DEL',
        'prefix_10397_DEL': 'suffix_299122_DEL',
        'prefix_104124_DEL': 'suffix_115920_DEL',
        'prefix_104792_DEL': 'suffix_116623_DEL',
        'prefix_105204_DEL': 'suffix_321184_DEL',
        'prefix_10520_DEL': 'suffix_12114_DEL',
        'prefix_105408_DEL': 'suffix_124299_DEL',
        'prefix_105567_DEL': 'suffix_137041_DEL',
        'prefix_105575_DEL': 'suffix_132895_DEL',
        'prefix_105957_DEL': 'suffix_117939_DEL',
        'prefix_106328_DUP': 'suffix_118372_DUP',
        'prefix_10674_DEL': 'suffix_62051_DEL',
        'prefix_106904_DUP': 'suffix_119175_DUP',
        'prefix_10706_DUP': 'suffix_12310_DUP',
        'prefix_107471_DEL': 'suffix_119959_DEL',
        'prefix_107474_DEL': 'suffix_107226_DEL',
        'prefix_107640_DEL': 'suffix_42123_DEL',
        'prefix_107682_DEL': 'suffix_328436_DEL',
        'prefix_107713_DEL': 'suffix_295713_DEL',
        'prefix_107739_DEL': 'suffix_120359_DEL',
        'prefix_108245_DUP': 'suffix_345422_DUP',
        'prefix_108246_DUP': 'suffix_345434_DUP',
        'prefix_108445_DEL': 'suffix_193406_DEL',
        'prefix_108449_DUP': 'suffix_306110_DUP',
        'prefix_108682_DEL': 'suffix_121584_DEL',
        'prefix_108787_DUP': 'suffix_121697_DUP',
        'prefix_109461_DUP': 'suffix_69248_DUP',
        'prefix_109954_DEL': 'suffix_136917_DEL',
        'prefix_11087_DEL': 'suffix_12711_DEL',
        'prefix_111170_DUP': 'suffix_124298_DUP',
        'prefix_111287_DUP': 'suffix_124448_DUP',
        'prefix_111457_DEL': 'suffix_325622_DEL',
        'prefix_112147_DEL': 'suffix_176498_DEL',
        'prefix_112170_DEL': 'suffix_189247_DEL',
        'prefix_112473_DEL': 'suffix_189253_DEL',
        'prefix_112579_DUP': 'suffix_218784_DUP',
        'prefix_112737_DEL': 'suffix_322979_DEL',
        'prefix_113007_DEL': 'suffix_189763_DEL',
        'prefix_113045_DEL': 'suffix_182363_DEL',
        'prefix_113061_DUP': 'suffix_258764_DUP',
        'prefix_113221_DUP': 'suffix_345607_DUP',
        'prefix_113248_DEL': 'suffix_220751_DEL',
        'prefix_113388_DEL': 'suffix_49218_DEL',
        'prefix_114137_DUP': 'suffix_181479_DUP',
        'prefix_114155_DEL': 'suffix_203405_DEL',
        'prefix_114307_DUP': 'suffix_127847_DUP',
        'prefix_114524_DEL': 'suffix_236802_DEL',
        'prefix_115161_DEL': 'suffix_337104_DEL',
        'prefix_115528_DEL': 'suffix_345416_DEL',
        'prefix_115594_DEL': 'suffix_185881_DEL',
        'prefix_1164_DEL': 'suffix_1403_DEL',
        'prefix_116701_DEL': 'suffix_130655_DEL',
        'prefix_11784_DEL': 'suffix_193515_DEL',
        'prefix_11793_DEL': 'suffix_261170_DEL',
        'prefix_118448_DUP': 'suffix_132890_DUP',
        'prefix_118567_DUP': 'suffix_257299_DUP',
        'prefix_118926_DEL': 'suffix_272807_DEL',
        'prefix_119331_DEL': 'suffix_133934_DEL',
        'prefix_119619_DUP': 'suffix_251043_DUP',
        'prefix_12014_DEL': 'suffix_171415_DEL',
        'prefix_120661_DUP': 'suffix_253757_DUP',
        'prefix_120683_DUP': 'suffix_299274_DUP',
        'prefix_121292_DUP': 'suffix_136324_DUP',
        'prefix_122017_DUP': 'suffix_169951_DUP',
        'prefix_122819_DEL': 'suffix_137963_DEL',
        'prefix_122974_DUP': 'suffix_138130_DUP',
        'prefix_123007_DUP': 'suffix_138159_DUP',
        'prefix_123041_DEL': 'suffix_335303_DEL',
        'prefix_123977_DEL': 'suffix_139305_DEL',
        'prefix_12470_DEL': 'suffix_226823_DEL',
        'prefix_124928_DEL': 'suffix_140340_DEL',
        'prefix_12605_DEL': 'suffix_241864_DEL',
        'prefix_127020_DUP': 'suffix_202584_DUP',
        'prefix_127505_DUP': 'suffix_252433_DUP',
        'prefix_12830_DEL': 'suffix_282628_DEL',
        'prefix_13020_DEL': 'suffix_14730_DEL',
        'prefix_13052_DEL': 'suffix_311669_DEL',
        'prefix_131669_DEL': 'suffix_33717_DEL',
        'prefix_131746_DEL': 'suffix_147895_DEL',
        'prefix_131753_DEL': 'suffix_111130_DEL',
        'prefix_13269_DUP': 'suffix_14995_DUP',
        'prefix_133114_DUP': 'suffix_217164_DUP',
        'prefix_133204_DUP': 'suffix_49743_DUP',
        'prefix_133405_DEL': 'suffix_342958_DEL',
        'prefix_13359_DEL': 'suffix_15085_DEL',
        'prefix_13369_DEL': 'suffix_52450_DEL',
        'prefix_133839_DUP': 'suffix_82443_DUP',
        'prefix_134071_DEL': 'suffix_307896_DEL',
        'prefix_134074_DEL': 'suffix_308281_DEL',
        'prefix_134075_DEL': 'suffix_308321_DEL',
        'prefix_134411_DEL': 'suffix_196304_DEL',
        'prefix_134571_DEL': 'suffix_150896_DEL',
        'prefix_134858_DEL': 'suffix_151606_DEL',
        'prefix_135555_DEL': 'suffix_152343_DEL',
        'prefix_136351_DUP': 'suffix_153160_DUP',
        'prefix_137771_DUP': 'suffix_290375_DUP',
        'prefix_138469_DUP': 'suffix_211854_DUP',
        'prefix_138595_DUP': 'suffix_97099_DUP',
        'prefix_138886_DUP': 'suffix_118224_DUP',
        'prefix_139433_DEL': 'suffix_21321_DEL',
        'prefix_139627_DEL': 'suffix_228579_DEL',
        'prefix_141117_DEL': 'suffix_75812_DEL',
        'prefix_141394_DEL': 'suffix_212333_DEL',
        'prefix_141485_DEL': 'suffix_158734_DEL',
        'prefix_141766_DUP': 'suffix_250308_DUP',
        'prefix_142256_DEL': 'suffix_151736_DEL',
        'prefix_142808_DEL': 'suffix_50260_DEL',
        'prefix_143266_DEL': 'suffix_283626_DEL',
        'prefix_143618_DEL': 'suffix_336978_DEL',
        'prefix_144319_DEL': 'suffix_12781_DEL',
        'prefix_144571_DEL': 'suffix_225727_DEL',
        'prefix_144878_DEL': 'suffix_162955_DEL',
        'prefix_144935_DEL': 'suffix_88144_DEL',
        'prefix_14542_DEL': 'suffix_29900_DEL',
        'prefix_145614_DEL': 'suffix_64370_DEL',
        'prefix_145631_DUP': 'suffix_213097_DUP',
        'prefix_145739_DUP': 'suffix_29512_DUP',
        'prefix_145751_DUP': 'suffix_142338_DUP',
        'prefix_145859_DEL': 'suffix_236767_DEL',
        'prefix_146138_DEL': 'suffix_341905_DEL',
        'prefix_146698_DUP': 'suffix_75558_DUP',
        'prefix_146725_DEL': 'suffix_92679_DEL',
        'prefix_146819_DEL': 'suffix_204036_DEL',
        'prefix_146982_DUP': 'suffix_80598_DUP',
        'prefix_147832_DUP': 'suffix_36481_DUP',
        'prefix_147905_DEL': 'suffix_116249_DEL',
        'prefix_14586_DEL': 'suffix_189167_DEL',
        'prefix_150663_DUP': 'suffix_169723_DUP',
        'prefix_150988_DEL': 'suffix_170148_DEL',
        'prefix_151487_DEL': 'suffix_87868_DEL',
        'prefix_151896_DUP': 'suffix_298612_DUP',
        'prefix_151897_DUP': 'suffix_67741_DUP',
        'prefix_151958_DEL': 'suffix_72228_DEL',
        'prefix_152188_DEL': 'suffix_258374_DEL',
        'prefix_152243_DEL': 'suffix_171706_DEL',
        'prefix_152598_DEL': 'suffix_287152_DEL',
        'prefix_153441_DUP': 'suffix_181703_DUP',
        'prefix_15373_DEL': 'suffix_17189_DEL',
        'prefix_155426_DEL': 'suffix_175579_DEL',
        'prefix_156182_DEL': 'suffix_12082_DEL',
        'prefix_157522_DEL': 'suffix_222475_DEL',
        'prefix_157813_DUP': 'suffix_178342_DUP',
        'prefix_158523_DUP': 'suffix_313465_DUP',
        'prefix_158661_DEL': 'suffix_88654_DEL',
        'prefix_160612_DEL': 'suffix_248116_DEL',
        'prefix_163949_DUP': 'suffix_344732_DUP',
        'prefix_164522_DEL': 'suffix_185883_DEL',
        'prefix_164622_DEL': 'suffix_186016_DEL',
        'prefix_164629_DUP': 'suffix_309441_DUP',
        'prefix_164642_DUP': 'suffix_311548_DUP',
        'prefix_164777_DEL': 'suffix_186196_DEL',
        'prefix_165076_DEL': 'suffix_328506_DEL',
        'prefix_165078_DEL': 'suffix_328786_DEL',
        'prefix_1657_DEL': 'suffix_2017_DEL',
        'prefix_167202_DEL': 'suffix_336972_DEL',
        'prefix_168614_DUP': 'suffix_190522_DUP',
        'prefix_168800_DUP': 'suffix_122588_DUP',
        'prefix_169366_DEL': 'suffix_191327_DEL',
        'prefix_170220_DUP': 'suffix_122478_DUP',
        'prefix_170275_DEL': 'suffix_329992_DEL',
        'prefix_170760_DEL': 'suffix_192854_DEL',
        'prefix_171486_DEL': 'suffix_193608_DEL',
        'prefix_17150_DEL': 'suffix_98009_DEL',
        'prefix_17230_DEL': 'suffix_336965_DEL',
        'prefix_17231_DEL': 'suffix_337022_DEL',
        'prefix_172982_DUP': 'suffix_195278_DUP',
        'prefix_17317_DEL': 'suffix_275059_DEL',
        'prefix_173203_DEL': 'suffix_195570_DEL',
        'prefix_173318_DEL': 'suffix_173502_DEL',
        'prefix_173699_DUP': 'suffix_127421_DUP',
        'prefix_173819_DEL': 'suffix_344967_DEL',
        'prefix_174099_DEL': 'suffix_151801_DEL',
        'prefix_174146_DEL': 'suffix_193980_DEL',
        'prefix_174221_DUP': 'suffix_125584_DUP',
        'prefix_174279_DEL': 'suffix_157330_DEL',
        'prefix_174372_DEL': 'suffix_262729_DEL',
        'prefix_174562_DEL': 'suffix_174111_DEL',
        'prefix_174564_DEL': 'suffix_1324_DEL',
        'prefix_175140_DEL': 'suffix_272786_DEL',
        'prefix_175243_DUP': 'suffix_322125_DUP',
        'prefix_175281_DUP': 'suffix_323384_DUP',
        'prefix_175291_DUP': 'suffix_323971_DUP',
        'prefix_176490_DUP': 'suffix_337504_DUP',
        'prefix_176785_DEL': 'suffix_256937_DEL',
        'prefix_177587_DUP': 'suffix_56526_DUP',
        'prefix_177834_DUP': 'suffix_276088_DUP',
        'prefix_178234_DEL': 'suffix_170832_DEL',
        'prefix_178374_DUP': 'suffix_173115_DUP',
        'prefix_178921_DEL': 'suffix_201891_DEL',
        'prefix_179719_DEL': 'suffix_326378_DEL',
        'prefix_179787_DEL': 'suffix_337951_DEL',
        'prefix_179804_DEL': 'suffix_289797_DEL',
        'prefix_180023_DEL': 'suffix_298661_DEL',
        'prefix_180149_DUP': 'suffix_203322_DUP',
        'prefix_180338_DEL': 'suffix_45778_DEL',
        'prefix_180351_DEL': 'suffix_107299_DEL',
        'prefix_180464_DEL': 'suffix_342917_DEL',
        'prefix_180500_DEL': 'suffix_183250_DEL',
        'prefix_180680_DUP': 'suffix_82979_DUP',
        'prefix_180721_DEL': 'suffix_4948_DEL',
        'prefix_181685_DEL': 'suffix_42286_DEL',
        'prefix_181724_DUP': 'suffix_343954_DUP',
        'prefix_18172_DUP': 'suffix_94217_DUP',
        'prefix_182085_DUP': 'suffix_248675_DUP',
        'prefix_182185_DUP': 'suffix_185453_DUP',
        'prefix_182381_DEL': 'suffix_65928_DEL',
        'prefix_182507_DEL': 'suffix_162956_DEL',
        'prefix_182_DEL': 'suffix_106425_DEL',
        'prefix_183723_DUP': 'suffix_207297_DUP',
        'prefix_184282_DUP': 'suffix_301766_DUP',
        'prefix_184370_DEL': 'suffix_156979_DEL',
        'prefix_184996_DUP': 'suffix_328901_DUP',
        'prefix_185023_DEL': 'suffix_15090_DEL',
        'prefix_185054_DEL': 'suffix_280761_DEL',
        'prefix_185055_DEL': 'suffix_132024_DEL',
        'prefix_185138_DEL': 'suffix_127756_DEL',
        'prefix_185141_DEL': 'suffix_134624_DEL',
        'prefix_185531_DEL': 'suffix_132027_DEL',
        'prefix_185615_DEL': 'suffix_217486_DEL',
        'prefix_185627_DEL': 'suffix_224393_DEL',
        'prefix_185677_DEL': 'suffix_173146_DEL',
        'prefix_185750_DUP': 'suffix_102606_DUP',
        'prefix_185860_DEL': 'suffix_241831_DEL',
        'prefix_185877_DEL': 'suffix_302969_DEL',
        'prefix_185935_DEL': 'suffix_173921_DEL',
        'prefix_186018_DEL': 'suffix_217498_DEL',
        'prefix_186031_DEL': 'suffix_44013_DEL',
    },
}
SV_DROPPED_IDS = {
    'cluster_6_last_call_cnv_17479_DUP', 'cluster_1_last_call_cnv_30127_DEL', 'cluster_19_COHORT_cnv_23176_DEL',
    'phase2_DEL_chrX_1149', 'prefix_121357_DUP', 'prefix_73945_DEL', 'phase2_DUP_chr9_1663', 'phase2_CPX_chr20_4',
    'phase2_INV_chr19_1', 'cohort_2911.chr2.final_cleanup_BND_chr2_3805', 'prefix_136453_DEL', 'prefix_283065_DEL',
    'phase2_CPX_chr1_27', 'cohort_2911.chr1.final_cleanup_BND_chr1_3716', 'cohort_2911.chr1.final_cleanup_DEL_chr1_8598',
    'cohort_2911.chr10.final_cleanup_BND_chr10_174', 'cohort_2911.chr10.final_cleanup_DUP_chr10_3475','prefix_100035_DEL',
    'cohort_2911.chr11.final_cleanup_DEL_chr11_885', 'cohort_2911.chr11.final_cleanup_DUP_chr11_2292',
    'cohort_2911.chr12.final_cleanup_DEL_chr12_4527', 'cohort_2911.chr13.final_cleanup_DEL_chr13_2215', 'prefix_100069_DEL',
    'cohort_2911.chr11.final_cleanup_DEL_chr11_8856', 'cohort_2911.chr14.final_cleanup_DEL_chr14_5833',
    'cohort_2911.chr16.final_cleanup_DEL_chr16_3', 'cohort_2911.chr2.final_cleanup_BND_chr2_197',
    'cohort_2911.chr2.final_cleanup_BND_chr2_88',
}


class Command(BaseCommand):

    def handle(self, *args, **options):
        num_updated = SavedVariant.objects.filter(
            genotypes={}, saved_variant_json__genotypes__isnull=False,
        ).exclude(saved_variant_json__genotypes={}).update(genotypes=F('saved_variant_json__genotypes'))
        logger.info(f'Updated genotypes for {num_updated} variants')

        variant_ids = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh38,
            saved_variant_json__populations__isnull=False, # Omit manual variants
        ).values_list('variant_id', flat=True).distinct()
        ids_by_dataset_type = {
            Sample.DATASET_TYPE_VARIANT_CALLS: [], Sample.DATASET_TYPE_MITO_CALLS: [], Sample.DATASET_TYPE_SV_CALLS: [],
        }
        for variant_id in variant_ids:
            parsed_id = parse_variant_id(variant_id)
            if not parsed_id and variant_id.endswith('-'):
                # Some AnVIL data was loaded with "-" as the alt allele
                parsed_id = parse_variant_id(variant_id[:-1])
            if parsed_id:
                is_mito = parsed_id[0].replace('chr', '').startswith('M')
                dataset_type = Sample.DATASET_TYPE_MITO_CALLS if is_mito else Sample.DATASET_TYPE_VARIANT_CALLS
            else:
                dataset_type = Sample.DATASET_TYPE_SV_CALLS
            ids_by_dataset_type[dataset_type].append(variant_id)

        no_key_mito = self._set_variant_keys(ids_by_dataset_type[Sample.DATASET_TYPE_MITO_CALLS], Sample.DATASET_TYPE_MITO_CALLS)

        no_key_snv_indel = self._set_variant_keys(
            ids_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS] + list(no_key_mito), Sample.DATASET_TYPE_VARIANT_CALLS,
        )
        if no_key_snv_indel:
            self._resolve_missing_variants(no_key_snv_indel, GENOME_VERSION_GRCh38)

        no_keys_svs = self._set_variant_keys(
            ids_by_dataset_type[Sample.DATASET_TYPE_SV_CALLS], f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}',
        )
        no_keys_svs = self._set_variant_keys(list(no_keys_svs), f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}')
        if no_keys_svs:
            self._resolve_reloaded_svs(no_keys_svs)

        variant_ids_37 = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh37,
        ).values_list('variant_id', flat=True).distinct()

        no_keys_37 = self._set_variant_keys(variant_ids_37, Sample.DATASET_TYPE_VARIANT_CALLS, genome_version=GENOME_VERSION_GRCh37)
        if no_keys_37:
            self._resolve_missing_variants(no_keys_37, GENOME_VERSION_GRCh37)

        num_updated = SavedVariant.objects.filter(key__isnull=False).update(saved_variant_json={})
        logger.info(f'Cleared saved json for {num_updated} variants with keys')

        logger.info('Done')

    @staticmethod
    def _set_variant_keys(variants_ids, dataset_type, genome_version=GENOME_VERSION_GRCh38, variant_id_updates=None):
        if not variants_ids:
            return
        logger.info(f'Finding keys for {len(variants_ids)} {dataset_type} (GRCh{genome_version}) variant ids')
        variant_key_map = get_clickhouse_key_lookup(genome_version, dataset_type, variants_ids)
        logger.info(f'Found {len(variant_key_map)} keys')
        if not variant_key_map:
            return set(variants_ids)

        mapped_variant_ids = variant_key_map.keys()
        if variant_id_updates:
            reverse_lookup = {v: k for k, v in variant_id_updates.items()}
            mapped_variant_ids = [reverse_lookup[vid] for vid in mapped_variant_ids]
        saved_variants = SavedVariant.objects.filter(
            family__project__genome_version=genome_version, variant_id__in=mapped_variant_ids,
        )
        for variant in saved_variants:
            if variant_id_updates:
                variant.variant_id = variant_id_updates[variant.variant_id]
            variant.key = variant_key_map[variant.variant_id]
            variant.dataset_type = dataset_type
        update_fields = ['key', 'dataset_type']
        if variant_id_updates:
            update_fields.append('variant_id')
        num_updated = SavedVariant.objects.bulk_update(saved_variants, update_fields, batch_size=10000)
        logger.info(f'Updated keys for {num_updated} {dataset_type} (GRCh{genome_version}) variants')

        no_key = set(variants_ids) - set(variant_key_map.keys())
        if no_key:
            logger.info(f'No key found for {len(no_key)} variants')
        return no_key

    @classmethod
    def _query_missing_variants(cls, variant_ids, variant_fields, genome_version=GENOME_VERSION_GRCh38, exclude_project=None):
        missing_variants = SavedVariant.objects.filter(
            variant_id__in=variant_ids, family__project__genome_version=genome_version,
        )
        num_missing = missing_variants.count()
        missing_with_data_qs = missing_variants.filter(family__individual__sample__is_active=True).distinct()
        if exclude_project:
            num_missing = (num_missing, missing_with_data_qs.count())
            missing_with_data_qs = missing_with_data_qs.exclude(family__project__guid=exclude_project)
        missing_with_search_data = missing_with_data_qs.values(
            'variant_id', *variant_fields,
        ).annotate(family_ids=ArrayAgg('family__family_id', distinct=True)).order_by('variant_id')
        return missing_with_search_data, num_missing

    @classmethod
    def _resolve_missing_variants(cls, variant_ids, genome_version):
        missing_with_search_data, num_missing = cls._query_missing_variants(
            variant_ids, ['saved_variant_json__populations__seqr__ac'], genome_version,
        )
        num_data= len(missing_with_search_data)
        in_backend = [
            f"{var['variant_id']} - {'; '.join(var['family_ids'])}"
            for var in missing_with_search_data if var['saved_variant_json__populations__seqr__ac']
        ]
        logger.info(
            f'{num_missing} variants have no key, {num_missing - num_data} of which have no search data, {num_data - len(in_backend)} of which are absent from the hail backend.'
        )
        if in_backend:
            logger.info(f'{len(in_backend)} remaining variants: {", ".join(in_backend)}')

    @classmethod
    def _resolve_reloaded_svs(cls, variant_ids):
        num_known_dropped = len(SV_DROPPED_IDS.intersection(variant_ids))
        # The CMG_gCNV project was an old project created before SV data was widely available, and keeping it up to date is less crucial
        valid_project_data, (num_missing, num_data) = cls._query_missing_variants(
            list(set(variant_ids) - SV_DROPPED_IDS), ['family__individual__sample__sample_type'], exclude_project='R0486_cmg_gcnv',
        )
        logger.info(
            f'{num_missing + num_known_dropped} variants have no key, {num_known_dropped} of which are known to have dropped out of the callset, {num_missing - num_data} of which have no search data, {num_data - len(valid_project_data)} of which are in a skippable project.'
        )
        if not valid_project_data:
            return

        gcnv_id_map = cls._load_gcnv_id_map()
        missing_by_sample_type = defaultdict(list)
        update_variants_by_sample_type = defaultdict(dict)
        for variant in valid_project_data:
            variant_id = variant['variant_id']
            sample_type = variant['family__individual__sample__sample_type']
            update_id = SV_ID_UPDATE_MAP[sample_type].get(variant_id)
            if not update_id and sample_type == 'WES' :
                suffix = next((suff for suff in ['_DEL', '_DUP'] if variant_id.endswith(suff)), None)
                if suffix:
                    base_id = gcnv_id_map.get(variant_id.rsplit(suffix)[0])
                    if base_id:
                        update_id = f'{base_id}{suffix}'
            if update_id:
                update_variants_by_sample_type[sample_type][variant_id] = update_id
            elif re.match(r'.*_(DEL|DUP)_\d+', variant_id):
                update_variants_by_sample_type[sample_type][variant_id] = variant_id.rsplit('_', 1)[0]
            else:
                missing_by_sample_type[sample_type].append(f"{variant_id} - {'; '.join(variant['family_ids'])}" )

        for sample_type, variant_id_updates in update_variants_by_sample_type.items():
            logger.info(f'Mapping reloaded SV_{sample_type} IDs to latest version')
            failed_mapping = cls._set_variant_keys(
                list(variant_id_updates.values()), f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}',
                genome_version=GENOME_VERSION_GRCh38, variant_id_updates=variant_id_updates,
            )
            if failed_mapping:
                logger.info(f'{len(failed_mapping)} variants failed ID mapping: {list(failed_mapping)[:10]}...')

        for sample_type, variants in missing_by_sample_type.items():
            logger.info(f'{len(variants)} remaining SV {sample_type} variants: {", ".join(variants[:10])}...')

    @staticmethod
    def _load_gcnv_id_map():
        file_content = file_iter(GCNV_CALLSET_PATH)
        header = next(file_content).split('\t')
        variant_name_idx = header.index('variant_name')
        old_id_idx = header.index('any_ovl')
        id_map = {}
        for raw_row in file_content:
            row = raw_row.split('\t')
            for old_id in row[old_id_idx].split(';'):
                id_map[old_id.strip()] = row[variant_name_idx].strip()
        return id_map
