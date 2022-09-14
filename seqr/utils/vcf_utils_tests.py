import mock

from unittest import TestCase

from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.vcf_utils import validate_vcf_and_get_samples

BASIC_META = [
    '##fileformat=VCFv4.3\n'
    '##source=myImputationProgramV3.1\n',
    '##FILTER=<ID=q10,Description="Quality below 10">',
    '##FILTER=<ID=s50,Description="Less than 50% of samples have data">',
]

PARTIAL_INFO_META = [
    '##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral Allele">',
    '##INFO=<ID=DB,Number=0,Type=Flag,Description="dbSNP membership, build 129">',
    '##INFO=<ID=H2,Number=0,Type=Flag,Description="HapMap2 membership">',
]

INFO_META = PARTIAL_INFO_META + [
    '##INFO=<ID=AC,Number=A,Type=Integer,Description="Allele count in genotypes, for each ALT allele, in the same order as listed">\n',
    '##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency, for each ALT allele, in the same order as listed">\n',
    '##INFO=<ID=AN,Number=1,Type=Integer,Description="Total number of alleles in called genotypes">\n',
]

PARTIAL_FORMAT_META = [
    '##FORMAT=<ID=AD,Number=.,Type=Integer,Description="Allelic depths for the ref and alt alleles in the order listed">\n',
    '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Approximate read depth (reads with MQ=255 or with bad mates are filtered)">\n',
]

FORMAT_META = PARTIAL_FORMAT_META + [
    '##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype Quality">\n',
    '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n',
]

HEADER_LINE = [
    '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSample1\tSample2\n',
]

DATA_LINES = [
    'chr1\t10333\t.\tCT\tC\t1895\tPASS\tAC=5;AF=0.045;AN=112;DP=22546\tGT:AD:DP:GQ\t./.:63,0:63\t./.:44,0:44'
]


class VcfUtilsTest(TestCase):

    @mock.patch('seqr.utils.vcf_utils.file_iter')
    def test_validate_vcf_and_get_samples(self, mock_file_iter):
        mock_file_iter.return_value = ['']
        with self.assertRaises(ErrorsWarningsException) as ee:
            validate_vcf_and_get_samples('/temp_path/test.vcf')
        self.assertEqual(ee.exception.errors[0],  'Missing required VCF header field(s) #CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT.')
        mock_file_iter.assert_called_with('/temp_path/test.vcf', byte_range=None)

        mock_file_iter.return_value = ['#CHROM\tPOS\tID\tREF\tALT\n']
        with self.assertRaises(ErrorsWarningsException) as ee:
            validate_vcf_and_get_samples('/temp_path/test.vcf.bgz')
        self.assertEqual(ee.exception.errors[0],  'Missing required VCF header field(s) QUAL, FILTER, INFO, FORMAT.')
        mock_file_iter.assert_called_with('/temp_path/test.vcf.bgz', byte_range=(0, 65536))

        mock_file_iter.return_value = BASIC_META + PARTIAL_INFO_META + FORMAT_META + HEADER_LINE + DATA_LINES
        with self.assertRaises(ErrorsWarningsException) as ee:
            validate_vcf_and_get_samples('gs://my_bucket/temp_path/test.vcf.gz')
        self.assertEqual(ee.exception.errors[0],  'VCF header field INFO.AC and meta information Type=Integer is expected.')
        mock_file_iter.assert_called_with('gs://my_bucket/temp_path/test.vcf.gz', byte_range=(0, 65536))

        mock_file_iter.return_value = BASIC_META + INFO_META + PARTIAL_FORMAT_META + HEADER_LINE + DATA_LINES
        with self.assertRaises(ErrorsWarningsException) as ee:
            validate_vcf_and_get_samples('gs://my_bucket/temp_path/test.vcf.gz')
        self.assertEqual(ee.exception.errors[0],  'VCF header field FORMAT.GQ and meta information Type=Integer is expected.')
        mock_file_iter.assert_called_with('gs://my_bucket/temp_path/test.vcf.gz', byte_range=(0, 65536))

        mock_file_iter.return_value = BASIC_META + INFO_META + FORMAT_META + HEADER_LINE + DATA_LINES
        self.assertEqual(validate_vcf_and_get_samples('gs://my_bucket/temp_path/test.vcf.gz'), {'Sample1', 'Sample2'})
        mock_file_iter.assert_called_with('gs://my_bucket/temp_path/test.vcf.gz', byte_range=(0, 65536))
