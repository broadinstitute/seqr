from django.test import TestCase

from seqr.views.utils.anvil_metadata_utils import _get_inheritance_model


class VariantUtilsTest(TestCase):

    PROBAND = 'I000001_na19675'
    DAD = 'I000002_na19678'
    MOM = 'I000003_na19679'

    def _assert_expected_inheritance(self, genotype_zygosity, expected_inheritance, mom_affected=False, is_x_linked=False, potential_comp_het=False):
        affected_individual_guids = {self.PROBAND}
        unaffected_individual_guids = {self.DAD}
        mom_group = affected_individual_guids if mom_affected else unaffected_individual_guids
        mom_group.add(self.MOM)
        self.assertEqual(
            _get_inheritance_model(
                genotype_zygosity,
                affected_individual_guids=affected_individual_guids,
                unaffected_individual_guids=unaffected_individual_guids,
                parent_guid_map={self.PROBAND: [self.DAD, self.MOM], self.DAD: [], self.MOM: []},
                is_x_linked=is_x_linked,
            ),
            (expected_inheritance, potential_comp_het),
        )

    def test_get_inheritance_model(self):
        # No known inheritance
        self._assert_expected_inheritance({}, '')
        genotype_zygosity = {self.PROBAND: 'Homozygous', self.DAD: 'Homozygous', self.MOM: 'Heterozygous'}
        self._assert_expected_inheritance(genotype_zygosity, '')

        # Recessive inheritances
        genotype_zygosity[self.DAD] = None
        self._assert_expected_inheritance(genotype_zygosity, 'Autosomal recessive (homozygous)')
        self._assert_expected_inheritance(genotype_zygosity, 'X - linked', is_x_linked=True)
        genotype_zygosity[self.PROBAND] = 'Hemizygous'
        self._assert_expected_inheritance(genotype_zygosity, 'X - linked', is_x_linked=True)

        # Heterozygous proband inheritances
        genotype_zygosity[self.PROBAND] = 'Heterozygous'
        self._assert_expected_inheritance(genotype_zygosity, '', potential_comp_het=True)
        self._assert_expected_inheritance(
            genotype_zygosity, 'Autosomal dominant', mom_affected=True, potential_comp_het=True,
        )
        genotype_zygosity[self.MOM] = None
        self._assert_expected_inheritance(genotype_zygosity, 'de novo')
        self._assert_expected_inheritance(
            genotype_zygosity, 'de novo', mom_affected=True, potential_comp_het=True,
        )
