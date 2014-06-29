import unittest
import os

from xbrowse_server.base.models import Individual, VCFFile


def get_vcfs_path_does_not_exist():
    return [vcf for vcf in VCFFile.objects.all() if not os.path.exists(vcf.path())]

def get_vcfs_without_unannotated_version():
    ret = []
    for vcf in VCFFile.objects.all():
        raw_path = vcf.path()[:-8] + '.vcf'
        if not os.path.exists(raw_path):
            ret.append(vcf)
    return ret

def get_individuals_not_actually_in_vcf():
    ret = []
    for individual in Individual.objects.all():
        for vcf in individual.vcf_files.all():
            if individual.indiv_id not in vcf.sample_id_list():
                ret.append( (individual, vcf) )
    return ret

class VCFFilesActuallyExist(unittest.TestCase):
    def runTest(self):
        x = get_vcfs_path_does_not_exist()
        self.assertEqual(x, [])

class VCFFilesHaveUnAnnotatedVersion(unittest.TestCase):
    def runTest(self):
        x = get_vcfs_without_unannotated_version()
        self.assertEqual(x, [])

class IndividualActuallyInVCFFile(unittest.TestCase):
    def runTest(self):
        x = get_individuals_not_actually_in_vcf()
        self.assertEqual(x, [])

