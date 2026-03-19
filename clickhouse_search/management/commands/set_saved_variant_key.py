from collections import defaultdict

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand
from django.db.models import F
import logging

from clickhouse_search.search import get_clickhouse_key_lookup
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import SavedVariant, Sample
from seqr.utils.search.utils import parse_variant_id

logger = logging.getLogger(__name__)

BATCH_SIZE = 10000

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
    'cohort_2911.chr2.final_cleanup_BND_chr2_88', 'cohort_2911.chr4.final_cleanup_BND_chr4_1988', 'phase2_BND_chr4_1503',
    'prefix_187707_DUP', 'phase2_DEL_chrX_1156', 'phase2_INV_chr13_1', 'prefix_104037_DUP', 'prefix_101570_DEL',
    'prefix_107442_DEL', 'prefix_110663_DUP', 'prefix_116075_DEL', 'prefix_116353_DEL', 'prefix_131840_DEL',
    'prefix_158993_DUP', 'prefix_15755_DEL', 'prefix_176502_DUP', 'prefix_186412_DUP', 'prefix_186413_DUP',
    'prefix_232873_DUP', 'prefix_232874_DUP', 'prefix_232877_DUP', 'prefix_28289_DUP', 'prefix_31304_DUP',
    'prefix_51597_DUP', 'prefix_190102_DEL', 'prefix_51608_DUP', 'prefix_221407_DEL', 'prefix_221408_DEL',
    'prefix_255688_DUP', 'prefix_37290_DEL', 'prefix_260433_DEL', 'prefix_72862_DEL', 'prefix_98188_DEL',
    'prefix_90352_DUP', 'prefix_107497_DUP', 'phase2_DEL_chr1_6031', 'prefix_121381_DEL', 'prefix_202121_DUP',
    'cohort_2911.chr2.final_cleanup_BND_chr2_889', 'cohort_2911.chr2.final_cleanup_DUP_chr2_3932',
    'cohort_2911.chr2.final_cleanup_DUP_chr2_7490', 'cohort_2911.chr2.final_cleanup_INS_chr2_1130',
    'cohort_2911.chr22.final_cleanup_DUP_chr22_1511', 'cohort_2911.chr3.final_cleanup_BND_chr3_268',
    'cohort_2911.chr3.final_cleanup_DEL_chr3_10060', 'cohort_2911.chr3.final_cleanup_DUP_chr3_2896',
    'cohort_2911.chr5.final_cleanup_BND_chr5_884', 'cohort_2911.chr5.final_cleanup_DEL_chr5_5718',
    'cohort_2911.chr6.final_cleanup_BND_chr6_2309', 'cohort_2911.chr6.final_cleanup_CPX_chr6_38',
    'cohort_2911.chr7.final_cleanup_BND_chr7_1589', 'cohort_2911.chr7.final_cleanup_BND_chr7_1731',
    'cohort_2911.chr7.final_cleanup_BND_chr7_1751', 'cohort_2911.chr7.final_cleanup_DEL_chr7_9736',
    'cohort_2911.chr7.final_cleanup_DUP_chr7_5963', 'cohort_2911.chr9.final_cleanup_BND_chr9_1042',
    'cohort_2911.chrX.final_cleanup_BND_chrX_236', 'cohort_2911.chrX.final_cleanup_BND_chrX_370',
    'cohort_2911.chrX.final_cleanup_BND_chrX_482', 'cohort_2911.chrX.final_cleanup_BND_chrX_501',
    'cohort_2911.chrX.final_cleanup_BND_chrX_569', 'cohort_2911.chrX.final_cleanup_DEL_chrX_1911',
    'cohort_2911.chrX.final_cleanup_DEL_chrX_1912', 'cohort_2911.chrX.final_cleanup_DEL_chrX_1916',
    'cohort_2911.chrX.final_cleanup_DEL_chrX_1958', 'cohort_2911.chrX.final_cleanup_DEL_chrX_4003',
    'cohort_2911.chrX.final_cleanup_DEL_chrX_4372', 'cohort_2911.chrX.final_cleanup_DUP_chrX_2709',
    'cohort_2911.chrX.final_cleanup_DUP_chrX_631', 'phase2_BND_chr11_47', 'phase2_BND_chr11_810', 'phase2_BND_chr1_1064',
    'phase2_BND_chr1_143', 'phase2_BND_chr1_28', 'phase2_BND_chr2_2776', 'phase2_BND_chr3_2305', 'phase2_BND_chr4_1271',
    'phase2_BND_chr7_987', 'phase2_BND_chrX_310', 'phase2_CPX_chr11_67', 'phase2_CPX_chr1_191', 'phase2_CPX_chr20_50',
    'phase2_CPX_chr2_178', 'phase2_CPX_chr3_12', 'phase2_CPX_chrX_49', 'phase2_CTX_chr3_1', 'phase2_DEL_chr11_6013',
    'phase2_DEL_chr11_61', 'phase2_DEL_chr11_64', 'phase2_DEL_chr11_6470', 'phase2_DEL_chr11_70', 'phase2_DEL_chr11_72',
    'phase2_DEL_chr12_1092', 'phase2_DEL_chr12_5745', 'phase2_DEL_chr14_304', 'phase2_DEL_chr14_4456',
    'phase2_DEL_chr16_3480', 'phase2_DEL_chr17_2166', 'phase2_DEL_chr19_3', 'phase2_DEL_chr19_3801', 'phase2_DEL_chr19_4089',
    'phase2_DEL_chr1_10289', 'phase2_DEL_chr1_1859', 'phase2_DEL_chr1_564', 'phase2_DEL_chr1_6442', 'phase2_DEL_chr1_702',
    'phase2_DEL_chr1_825', 'phase2_DEL_chr1_8985', 'phase2_DEL_chr20_3055', 'phase2_DEL_chr2_11622', 'phase2_DEL_chr2_246',
    'phase2_DEL_chr2_6560', 'phase2_DEL_chr2_8969', 'phase2_DEL_chr3_3865', 'phase2_DEL_chr5_3479', 'phase2_DEL_chr5_3841',
    'phase2_DEL_chr5_5773', 'phase2_DEL_chr5_837', 'phase2_DEL_chr5_8866', 'phase2_DEL_chr5_9284', 'phase2_DEL_chr5_940',
    'phase2_DEL_chr6_3310', 'phase2_DEL_chr6_3783', 'phase2_DEL_chr7_3994', 'phase2_DEL_chr7_7308', 'phase2_DEL_chr7_8285',
    'phase2_DEL_chr8_7050', 'phase2_DEL_chrX_1692', 'phase2_DEL_chrX_1711', 'phase2_DEL_chrX_2006', 'phase2_DEL_chrX_2570',
    'phase2_DEL_chrX_4225', 'phase2_DUP_chr11_2031', 'phase2_DUP_chr13_2894', 'phase2_DUP_chr15_1044', 'phase2_DUP_chr16_56',
    'phase2_DUP_chr1_4', 'phase2_DUP_chr1_4156', 'phase2_DUP_chr2_8878', 'phase2_DUP_chr4_2375', 'phase2_DUP_chr4_486',
    'phase2_DUP_chr5_1272', 'phase2_DUP_chr5_6239', 'phase2_DUP_chr6_12', 'phase2_DUP_chr7_235', 'phase2_DUP_chr7_2872',
    'phase2_DUP_chr7_6068', 'phase2_DUP_chr7_6226', 'phase2_DUP_chrX_1009', 'phase2_DUP_chrX_1597', 'phase2_DUP_chrX_3449',
    'phase2_INS_chr11_1083', 'phase2_INS_chr14_995', 'phase2_INS_chr15_462', 'phase2_INS_chr17_887', 'phase2_INS_chr18_112',
    'phase2_INS_chr4_8', 'phase2_INS_chr5_14', 'phase2_INS_chr7_8', 'phase2_INS_chr7_985', 'phase2_INS_chrX_634',
    'prefix_101656_DUP', 'prefix_103772_DUP', 'prefix_104848_DUP', 'prefix_104955_DEL', 'prefix_105106_DEL',
    'prefix_10566_DEL', 'prefix_105762_DEL', 'prefix_105767_DUP', 'prefix_106133_DEL', 'prefix_106350_DUP',
    'prefix_107375_DUP', 'prefix_107449_DEL', 'prefix_107998_DEL', 'prefix_108257_DEL', 'prefix_109835_DEL',
    'prefix_11007_DEL', 'prefix_110195_DUP', 'prefix_112228_DEL', 'prefix_113169_DUP', 'prefix_114542_DEL',
    'prefix_116109_DUP', 'prefix_116684_DEL', 'prefix_11729_DUP', 'prefix_118876_DUP', 'prefix_120303_DEL',
    'prefix_120655_DEL', 'prefix_120715_DUP', 'prefix_120732_DUP', 'prefix_120770_DEL', 'prefix_121356_DEL',
    'prefix_122104_DUP', 'prefix_122891_DEL', 'prefix_123043_DEL', 'prefix_123043_DEL', 'prefix_123043_DEL',
    'prefix_12347_DEL', 'prefix_1243_DUP', 'prefix_124627_DEL', 'prefix_1250_DUP', 'prefix_125972_DEL', 'prefix_127583_DEL',
    'prefix_127702_DEL', 'prefix_13002_DEL', 'prefix_131133_DUP', 'prefix_131619_DUP', 'prefix_131832_DEL',
    'prefix_132292_DUP', 'prefix_132327_DEL', 'prefix_132903_DUP', 'prefix_133314_DEL', 'prefix_133771_DEL',
    'prefix_133965_DEL', 'prefix_133974_DEL', 'prefix_134970_DUP', 'prefix_134975_DUP', 'prefix_134982_DUP',
    'prefix_137070_DEL', 'prefix_137352_DUP', 'prefix_137515_DUP', 'prefix_137824_DEL', 'prefix_141384_DUP',
    'prefix_141673_DEL', 'prefix_142235_DUP', 'prefix_14236_DUP', 'prefix_142_DUP', 'prefix_143105_DUP', 'prefix_144640_DEL',
    'prefix_145910_DEL', 'prefix_146365_DEL', 'prefix_146774_DUP', 'prefix_146964_DUP', 'prefix_147003_DUP',
    'prefix_150029_DUP', 'prefix_15016_DEL', 'prefix_151274_DEL', 'prefix_153605_DEL', 'prefix_155212_DUP',
    'prefix_156514_DUP', 'prefix_158384_DUP', 'prefix_158650_DEL', 'prefix_158664_DEL', 'prefix_160277_DUP',
    'prefix_161748_DEL', 'prefix_162169_DEL', 'prefix_162239_DEL', 'prefix_162270_DEL', 'prefix_162738_DEL',
    'prefix_162951_DUP', 'prefix_163088_DEL', 'prefix_163102_DEL', 'prefix_163246_DEL', 'prefix_163355_DEL',
    'prefix_163854_DEL', 'prefix_164063_DUP', 'prefix_164549_DEL', 'prefix_164556_DEL', 'prefix_164633_DUP',
    'prefix_165128_DUP', 'prefix_168109_DUP', 'prefix_168895_DUP', 'prefix_168897_DEL', 'prefix_169791_DUP',
    'prefix_170374_DUP', 'prefix_170705_DEL', 'prefix_172571_DUP', 'prefix_172946_DEL', 'prefix_17321_DUP',
    'prefix_173394_DEL', 'prefix_173845_DUP', 'prefix_174288_DUP', 'prefix_174291_DUP', 'prefix_174292_DUP',
    'prefix_17444_DEL', 'prefix_17444_DEL', 'prefix_174517_DUP', 'prefix_175277_DUP', 'prefix_177361_DEL', 'prefix_17764_DEL',
    'prefix_177659_DEL', 'prefix_177950_DEL', 'prefix_178465_DEL', 'prefix_178540_DUP', 'prefix_179099_DUP',
    'prefix_180040_DEL', 'prefix_180738_DEL', 'prefix_180819_DEL', 'prefix_181154_DUP', 'prefix_182745_DEL',
    'prefix_182778_DUP', 'prefix_183768_DUP', 'prefix_184019_DEL', 'prefix_184139_DUP', 'prefix_184140_DUP',
    'prefix_184914_DUP', 'prefix_185204_DEL', 'prefix_185484_DUP', 'prefix_185763_DUP', 'prefix_190154_DUP',
    'prefix_191534_DUP', 'prefix_191897_DEL', 'prefix_191899_DEL', 'prefix_192723_DEL', 'prefix_192753_DEL',
    'prefix_192789_DEL', 'prefix_192810_DUP', 'prefix_192814_DEL', 'prefix_192815_DUP', 'prefix_192893_DEL',
    'prefix_193101_DUP', 'prefix_19341_DUP', 'prefix_19359_DUP', 'prefix_19494_DEL', 'prefix_19514_DEL', 'prefix_195407_DUP',
    'prefix_195410_DUP', 'prefix_196172_DUP', 'prefix_196462_DEL', 'prefix_196930_DUP', 'prefix_198944_DEL',
    'prefix_199367_DEL', 'prefix_200326_DEL', 'prefix_201581_DUP', 'prefix_202196_DEL', 'prefix_203149_DUP',
    'prefix_204824_DUP', 'prefix_206046_DUP', 'prefix_20681_DUP', 'prefix_207500_DEL', 'prefix_210512_DEL',
    'prefix_21173_DUP', 'prefix_212735_DUP', 'prefix_215162_DUP', 'prefix_21548_DUP', 'prefix_215773_DEL', 'prefix_2163_DUP',
    'prefix_217013_DEL', 'prefix_217024_DUP', 'prefix_217326_DUP', 'prefix_217327_DUP', 'prefix_21741_DEL',
    'prefix_222096_DUP', 'prefix_22259_DUP', 'prefix_223605_DUP', 'prefix_225452_DUP', 'prefix_22721_DEL', 'prefix_228404_DEL',
    'prefix_22880_DEL', 'prefix_230711_DEL', 'prefix_232671_DUP', 'prefix_232878_DUP', 'prefix_232948_DEL', 'prefix_234881_DEL',
    'prefix_235365_DUP', 'prefix_236208_DUP', 'prefix_237157_DEL', 'prefix_237619_DUP', 'prefix_237805_DEL',
    'prefix_237917_DUP', 'prefix_23794_DEL', 'prefix_238329_DUP', 'prefix_23844_DEL', 'prefix_238575_DEL', 'prefix_238946_DEL',
    'prefix_238949_DEL', 'prefix_239129_DEL', 'prefix_23925_DEL', 'prefix_240064_DUP', 'prefix_240065_DUP', 'prefix_240066_DUP',
    'prefix_240067_DUP', 'prefix_240075_DUP', 'prefix_240077_DUP', 'prefix_240079_DUP', 'prefix_240080_DUP', 'prefix_240082_DUP',
    'prefix_240084_DUP', 'prefix_240087_DUP', 'prefix_240088_DUP', 'prefix_240090_DUP', 'prefix_240091_DUP', 'prefix_240098_DUP',
    'prefix_240102_DUP', 'prefix_240103_DUP', 'prefix_240104_DUP', 'prefix_240107_DUP', 'prefix_240110_DUP', 'prefix_240116_DUP',
    'prefix_240168_DEL', 'prefix_240306_DUP', 'prefix_242363_DUP', 'prefix_242364_DUP', 'prefix_242485_DUP', 'prefix_24445_DEL',
    'prefix_244719_DEL', 'prefix_244925_DUP', 'prefix_245163_DUP', 'prefix_245178_DEL', 'prefix_245675_DUP', 'prefix_245708_DUP',
    'prefix_245785_DUP', 'prefix_246638_DEL', 'prefix_246946_DUP', 'prefix_247619_DUP', 'prefix_247835_DEL', 'prefix_249326_DUP',
    'prefix_250124_DEL', 'prefix_251066_DEL', 'prefix_251476_DUP', 'prefix_251879_DEL', 'prefix_252006_DEL', 'prefix_25227_DUP',
    'prefix_253446_DEL', 'prefix_254368_DEL', 'prefix_254594_DUP', 'prefix_25463_DEL', 'prefix_254654_DUP', 'prefix_255337_DEL',
    'prefix_255338_DEL', 'prefix_255699_DEL', 'prefix_255947_DEL', 'prefix_257636_DEL', 'prefix_260980_DEL', 'prefix_261010_DEL',
    'prefix_262712_DEL', 'prefix_263578_DUP', 'prefix_263619_DEL', 'prefix_263637_DUP', 'prefix_263641_DUP', 'prefix_263645_DUP',
    'prefix_263647_DUP', 'prefix_264278_DUP', 'prefix_26438_DEL', 'prefix_264706_DUP', 'prefix_264786_DEL', 'prefix_264797_DEL',
    'prefix_266509_DEL', 'prefix_266705_DEL', 'prefix_26790_DEL', 'prefix_27178_DEL', 'prefix_272072_DUP', 'prefix_27418_DUP',
    'prefix_277330_DEL', 'prefix_277330_DEL', 'prefix_278495_DUP', 'prefix_281404_DEL', 'prefix_28173_DUP', 'prefix_283002_DUP',
    'prefix_28329_DUP', 'prefix_283636_DUP', 'prefix_284375_DEL', 'prefix_284482_DEL', 'prefix_284499_DEL', 'prefix_284666_DUP',
    'prefix_284724_DEL', 'prefix_28564_DEL', 'prefix_28677_DEL', 'prefix_287359_DEL', 'prefix_28768_DEL', 'prefix_28815_DEL',
    'prefix_28955_DEL', 'prefix_29050_DEL', 'prefix_29052_DEL', 'prefix_290_DUP', 'prefix_29115_DEL', 'prefix_29132_DEL',
    'prefix_291814_DUP', 'prefix_29319_DEL', 'prefix_29359_DEL', 'prefix_29409_DEL', 'prefix_29465_DEL', 'prefix_296068_DEL',
    'prefix_296070_DEL', 'prefix_296071_DEL', 'prefix_296072_DEL', 'prefix_297161_DUP', 'prefix_297163_DUP', 'prefix_297193_DUP',
    'prefix_297203_DUP', 'prefix_297244_DEL', 'prefix_297325_DUP', 'prefix_298246_DEL', 'prefix_299171_DEL', 'prefix_299729_DUP',
    'prefix_30029_DEL', 'prefix_301500_DEL', 'prefix_301521_DEL', 'prefix_303270_DEL', 'prefix_31042_DEL', 'prefix_31146_DUP',
    'prefix_31636_DUP', 'prefix_32411_DEL', 'prefix_32572_DEL', 'prefix_32817_DEL', 'prefix_32938_DEL', 'prefix_32943_DEL',
    'prefix_33036_DEL', 'prefix_33259_DEL', 'prefix_33269_DEL', 'prefix_35408_DUP', 'prefix_36013_DUP', 'prefix_3660_DEL',
    'prefix_37114_DUP', 'prefix_37120_DUP', 'prefix_37284_DEL', 'prefix_37542_DEL', 'prefix_37710_DUP', 'prefix_37751_DEL',
    'prefix_38251_DUP', 'prefix_38525_DEL', 'prefix_40157_DEL', 'prefix_40443_DEL', 'prefix_41131_DEL', 'prefix_42483_DUP',
    'prefix_42564_DUP', 'prefix_43104_DEL', 'prefix_46281_DUP', 'prefix_46357_DEL', 'prefix_46467_DUP', 'prefix_46483_DEL',
    'prefix_46566_DEL', 'prefix_46681_DEL', 'prefix_47968_DUP', 'prefix_49538_DEL', 'prefix_4996_DEL', 'prefix_50673_DUP',
    'prefix_50678_DEL', 'prefix_518_DEL', 'prefix_52282_DUP', 'prefix_5289_DEL', 'prefix_54347_DUP', 'prefix_54569_DUP',
    'prefix_55426_DEL', 'prefix_56509_DUP', 'prefix_56903_DUP', 'prefix_58485_DEL', 'prefix_5932_DUP', 'prefix_6262_DEL',
    'prefix_63135_DUP', 'prefix_6344_DEL', 'prefix_64090_DEL', 'prefix_64813_DUP', 'prefix_65486_DEL', 'prefix_66447_DEL',
    'prefix_67003_DEL', 'prefix_7120_DEL', 'prefix_71708_DEL', 'prefix_72647_DUP', 'prefix_75175_DEL', 'prefix_75176_DEL',
    'prefix_75177_DEL', 'prefix_75180_DEL', 'prefix_75506_DUP', 'prefix_75843_DUP', 'prefix_76309_DUP', 'prefix_7665_DUP',
    'prefix_76693_DEL', 'prefix_7802_DUP', 'prefix_78417_DEL', 'prefix_78921_DUP', 'prefix_78943_DUP', 'prefix_78963_DUP',
    'prefix_78971_DUP', 'prefix_78976_DUP', 'prefix_78978_DUP', 'prefix_78980_DUP', 'prefix_78982_DUP', 'prefix_78988_DUP',
    'prefix_78994_DUP', 'prefix_79001_DUP', 'prefix_7962_DEL', 'prefix_796_DUP', 'prefix_79989_DUP', 'prefix_82092_DEL',
    'prefix_83579_DEL', 'prefix_83600_DUP', 'prefix_83786_DEL', 'prefix_83974_DEL', 'prefix_84263_DUP', 'prefix_84718_DEL',
    'prefix_86064_DUP', 'prefix_86065_DUP', 'prefix_89136_DEL', 'prefix_895_DUP', 'prefix_90181_DUP', 'prefix_91282_DEL',
    'prefix_91373_DUP', 'prefix_91952_DEL', 'prefix_91952_DEL', 'prefix_92457_DUP', 'prefix_92756_DUP', 'prefix_93796_DEL',
    'prefix_94231_DUP', 'prefix_943_DUP', 'prefix_94660_DEL', 'prefix_96293_DEL', 'prefix_97207_DUP', 'prefix_9762_DUP',
    'prefix_98217_DUP', 'prefix_98339_DUP', 'prefix_98578_DUP', 'prefix_98763_DUP', 'prefix_98910_DEL', 'prefix_99458_DEL',
    'suffix_20012_DEL_2', 'suffix_231565_DUP_2', 'suffix_264599_DEL_2', 'suffix_54380_DEL_2', 'suffix_69178_DEL_2',
    'CMG.phase1_CMG_DEL_chr15_535', 'CMG.phase1_CMG_DEL_chr15_748', 'CMG.phase1_CMG_DEL_chr16_1524',
    'CMG.phase1_CMG_DEL_chr16_1529', 'CMG.phase1_CMG_DEL_chr16_1842', 'CMG.phase1_CMG_DEL_chr17_398',
    'CMG.phase1_CMG_DEL_chr17_908', 'CMG.phase1_CMG_DEL_chr1_3107', 'CMG.phase1_CMG_DEL_chr1_4610',
    'CMG.phase1_CMG_DEL_chr2_5843', 'CMG.phase1_CMG_DEL_chr3_168', 'CMG.phase1_CMG_DEL_chr3_174', 'CMG.phase1_CMG_DEL_chr3_175',
    'CMG.phase1_CMG_DEL_chr3_744', 'CMG.phase1_CMG_DEL_chr5_1661', 'CMG.phase1_CMG_DEL_chr5_1936',
    'CMG.phase1_CMG_DEL_chr7_3298', 'CMG.phase1_CMG_DEL_chrX_1942', 'CMG.phase1_CMG_DEL_chrX_521', 'CMG.phase1_CMG_DEL_chrX_524',
    'CMG.phase1_CMG_DEL_chrX_544', 'phase2_DEL_chr16_4247',
}


class Command(BaseCommand):

    def handle(self, *args, **options):
        # TODO
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

        num_updated = SavedVariant.objects.filter(key__isnull=False).exclude(saved_variant_json={}).update(
            saved_variant_json={},
        )
        logger.info(f'Cleared saved json for {num_updated} variants with keys')

        logger.info('Done')

    @staticmethod
    def _set_variant_keys(variants_ids, dataset_type, genome_version=GENOME_VERSION_GRCh38):
        if not variants_ids:
            return set()
        logger.info(f'Finding keys for {len(variants_ids)} {dataset_type} (GRCh{genome_version}) variant ids')
        variant_key_map = get_clickhouse_key_lookup(genome_version, dataset_type, variants_ids)
        logger.info(f'Found {len(variant_key_map)} keys')
        if not variant_key_map:
            return set(variants_ids)

        mapped_variant_ids = list(variant_key_map.keys())

        update_fields = ['key', 'dataset_type']
        total_num_updated = 0
        for i in range(0, len(mapped_variant_ids), BATCH_SIZE):
            batch_ids = mapped_variant_ids[i:i + BATCH_SIZE]
            saved_variants = SavedVariant.objects.filter(
                family__project__genome_version=genome_version, variant_id__in=batch_ids,
            )
            for variant in saved_variants:
                variant.key = variant_key_map[variant.variant_id]
                variant.dataset_type = dataset_type
            num_updated = SavedVariant.objects.bulk_update(saved_variants, update_fields)
            logger.info(f'Updated batch of {num_updated}')
            total_num_updated += num_updated

        logger.info(f'Updated keys for {total_num_updated} {dataset_type} (GRCh{genome_version}) variants')

        no_key = set(variants_ids) - set(variant_key_map.keys())
        if no_key:
            logger.info(f'No key found for {len(no_key)} variants')
        return no_key

    @classmethod
    def _query_missing_variants(cls, variant_ids, variant_fields, genome_version=GENOME_VERSION_GRCh38):
        missing_variants = SavedVariant.objects.filter(
            variant_id__in=variant_ids, family__project__genome_version=genome_version,
        )
        num_missing = missing_variants.count()
        missing_with_data_qs = missing_variants.filter(family__individual__sample__is_active=True).distinct()
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
        missing_with_search_data, num_missing = cls._query_missing_variants(
            list(set(variant_ids) - SV_DROPPED_IDS), ['family__individual__sample__sample_type'],
        )
        logger.info(
            f'{num_missing + num_known_dropped} SV variants have no key, {num_missing - len(missing_with_search_data)} of which have no search data, {num_known_dropped} of which are known to have dropped out of the callset.'
        )
        if not missing_with_search_data:
            return

        missing_by_sample_type = defaultdict(list)
        for variant in missing_with_search_data:
            variant_id = variant['variant_id']
            sample_type = variant['family__individual__sample__sample_type']
            missing_by_sample_type[sample_type].append(f"{variant_id} - {'; '.join(variant['family_ids'])}" )

        for sample_type, variants in missing_by_sample_type.items():
            logger.info(f'{len(variants)} remaining SV {sample_type} variants {", ".join(variants)}')
