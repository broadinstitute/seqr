import datetime
import gzip
import mock
import responses
from django.core.management import call_command
from django.core.management.base import CommandError
from django.forms.models import model_to_dict
from django.test import TestCase
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

from clickhouse_search.models import (
    ClinvarSnvIndel, ClinvarGRCh37SnvIndel, ClinvarAllVariantsSnvIndel,
    ClinvarAllVariantsGRCh37SnvIndel, ClinvarAllVariantsMito,
)
from reference_data.models import DataVersions
from seqr.management.commands.reload_clinvar_all_variants import BATCH_SIZE, WEEKLY_XML_RELEASE

WEEKLY_XML_RELEASE_HEADER = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ClinVarVariationRelease xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/ClinVar_VCV_2.4.xsd" ReleaseDate="2025-06-30">'''
WEEKLY_XML_RELEASE_DATA = WEEKLY_XML_RELEASE_HEADER + '''
    <VariationArchive>
        <ClassifiedRecord>
            <SimpleAllele AlleleID="20642" VariationID="5603">
                <Location>
                    <SequenceLocation Assembly="GRCh38" AssemblyAccessionVersion="GCF_000001405.38" forDisplay="true" AssemblyStatus="current" Chr="22" Accession="NC_000022.11" start="28695219" stop="28695219" display_start="28695219" display_stop="28695219" variantLength="1" positionVCF="28695219" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                    <SequenceLocation Assembly="GRCh37" AssemblyAccessionVersion="GCF_000001405.25" AssemblyStatus="previous" Chr="22" Accession="NC_000022.10" start="29091207" stop="29091207" display_start="29091207" display_stop="29091207" variantLength="1" positionVCF="29091207" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                </Location>
            </SimpleAllele>
            <Classifications>
                <GermlineClassification>
                    <ReviewStatus>criteria provided, conflicting classifications</ReviewStatus>
                    <Description>Conflicting classifications of pathogenicity; association; risk factor</Description>
                    <Explanation DataSource="ClinVar" Type="public">Pathogenic(18); Likely pathogenic(9); Pathogenic, low penetrance(1); Established risk allele(1); Likely risk allele(1); Uncertain significance(1)</Explanation>
                </GermlineClassification>
            </Classifications>
            <ClinicalAssertionList>
                <ClinicalAssertion>
                    <ClinVarAccession SubmitterName="University of Washington Department of Laboratory Medicine, University of Washington" OrgID="506834" OrganizationCategory="laboratory"/>
                </ClinicalAssertion>
                <ClinicalAssertion>
                    <ClinVarAccession SubmitterName="Fulgent Genetics, Fulgent Genetics" OrgID="500105" OrganizationCategory="laboratory"/>
                </ClinicalAssertion>
                <ClinicalAssertion>
                    <ClinVarAccession SubmitterName="Revvity Omics, Revvity" OrgID="167595" OrganizationCategory="laboratory"/>
                </ClinicalAssertion>
                <TraitMappingList>
                    <TraitMapping>
                        <MedGen CUI="C3661900" Name="not provided"/>
                    </TraitMapping>
                    <TraitMapping>
                        <MedGen CUI="C0678222" Name="Breast carcinoma"/>
                    </TraitMapping>
                    <TraitMapping>
                        <MedGen CUI="None" Name="CHEK2-related disorder"/>
                    </TraitMapping>
                    <TraitMapping>
                        <MedGen CUI="C5882668" Name="CHEK2-related cancer predisposition"/>
                    </TraitMapping>
                    <TraitMapping>
                        <MedGen CUI="C0027672" Name="Hereditary cancer-predisposing syndrome"/>
                    </TraitMapping>
                </TraitMappingList>
            </ClinicalAssertionList>
        </ClassifiedRecord>
    </VariationArchive>
    <VariationArchive VariationID="5603" RecordType="classified" NumberOfSubmissions="38" NumberOfSubmitters="36" DateLastUpdated="2025-06-29" DateCreated="2016-03-20" MostRecentSubmission="2025-06-29">
        <ClassifiedRecord>
            <SimpleAllele AlleleID="20642" VariationID="5603">
                <Location>
                    <SequenceLocation Assembly="GRCh38" Chr="MT" Accession="NC_000022.11" start="123" stop="123" display_start="123" display_stop="28695219" variantLength="1" positionVCF="123" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                </Location>
            </SimpleAllele>
            <Classifications>
                <GermlineClassification>
                    <Description>Pathogenic/Likely pathogenic/Pathogenic, low penetrance/Established risk allele</Description>
                </GermlineClassification>
            </Classifications>
        </ClassifiedRecord>
    </VariationArchive>
</ClinVarVariationRelease>
'''


@mock.patch('seqr.management.commands.reload_clinvar_all_variants.safe_post_to_slack')
@mock.patch('seqr.management.commands.reload_clinvar_all_variants.logger.info')
class ReloadClinvarAllVariantsTest(TestCase):
    databases = '__all__'
    fixtures = ['clinvar_all_variants']

    @responses.activate
    def test_update_with_no_previous_version(self, mock_logger, mock_safe_post_to_slack):
        DataVersions.objects.all().delete()
        ClinvarAllVariantsSnvIndel.objects.using('clickhouse_write').all().delete()
        responses.add(responses.GET, WEEKLY_XML_RELEASE, status=200, body=gzip.compress(WEEKLY_XML_RELEASE_DATA.encode()), stream=True)
        call_command('reload_clinvar_all_variants')
        mock_logger.assert_called_with('Updating Clinvar ClickHouse tables to 2025-06-30 from None.')
        self.assertEqual(ClinvarAllVariantsSnvIndel.objects.count(), 1)

    @responses.activate
    def test_new_version_already_exists(self, mock_logger, mock_safe_post_to_slack):
        version_obj = DataVersions.objects.filter(data_model_name='Clinvar').first()
        version_obj.version = '2025-06-30'
        version_obj.save()
        responses.add(responses.GET, WEEKLY_XML_RELEASE, status=200, body=gzip.compress(WEEKLY_XML_RELEASE_DATA.encode()), stream=True)
        call_command('reload_clinvar_all_variants')
        mock_logger.assert_called_with('Clinvar ClickHouse tables already successfully updated to 2025-06-30, gracefully exiting.')

    @responses.activate
    def test_parse_variants_all_types(self, mock_logger, mock_safe_post_to_slack):
        responses.add(responses.GET, WEEKLY_XML_RELEASE, status=200, body=gzip.compress(WEEKLY_XML_RELEASE_DATA.encode()), stream=True)
        call_command('reload_clinvar_all_variants')
        mock_logger.assert_called_with('Updating Clinvar ClickHouse tables to 2025-06-30 from 2025-06-23.')
        seqr_clinvar_snv_indel_models = ClinvarSnvIndel.objects.all()
        self.assertEqual(seqr_clinvar_snv_indel_models.count(), 1)
        self.assertDictEqual(
            model_to_dict(seqr_clinvar_snv_indel_models.first()),
            {
                'allele_id': 20642,
                'assertions': ['association', 'risk_factor'],
                'conditions': [
                    'Breast carcinoma',
                    'CHEK2-related cancer predisposition',
                    'CHEK2-related disorder',
                    'Hereditary cancer-predisposing syndrome',
                ],
                'conflicting_pathogenicities': [
                    {'pathogenicity': 'Pathogenic', 'count': 19},
                    {'pathogenicity': 'Likely_pathogenic', 'count': 9},
                    {'pathogenicity': 'Established_risk_allele', 'count': 1},
                    {'pathogenicity': 'Likely_risk_allele', 'count': 1},
                    {'pathogenicity': 'Uncertain_significance', 'count': 1},
                ],
                'gold_stars': 1,
                'key': 12,
                'pathogenicity': 'Conflicting_classifications_of_pathogenicity',
                'submitters': [
                    'Fulgent Genetics, Fulgent Genetics',
                    'Revvity Omics, Revvity',
                    'University of Washington Department of Laboratory Medicine, University of Washington'
                ]
            },
        )

        seqr_clinvar_grch37_snv_indel_models = ClinvarGRCh37SnvIndel.objects.all()
        self.assertEqual(seqr_clinvar_grch37_snv_indel_models.count(), 0)
        clinvar_all_variants_grch37_snv_indel_models = ClinvarAllVariantsGRCh37SnvIndel.objects.all()
        self.assertEqual(clinvar_all_variants_grch37_snv_indel_models.count(), 1)
        clinvar_all_variants_mito_models = ClinvarAllVariantsMito.objects.all()
        self.assertDictEqual(
            model_to_dict(clinvar_all_variants_mito_models.first()),
            {
                'allele_id': 20642,
                'assertions': ['low_penetrance'],
                'conditions': [],
                'conflicting_pathogenicities': None,
                'gold_stars': None,
                'pathogenicity': 'Pathogenic/Likely_pathogenic/Established_risk_allele',
                'submitters': [],
                'variant_id': 'M-123-G-A',
                'version': datetime.date(2025, 6, 30)
            }
        )
    
        # Version in Postgres.
        dv = DataVersions.objects.get(data_model_name='Clinvar')
        self.assertEqual(dv.version, '2025-06-30')
        mock_safe_post_to_slack.assert_called_with(
            SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            'Successfully updated Clinvar ClickHouse tables to 2025-06-30.',
        )
    
    
    @responses.activate
    def test_batching(self, mock_logger, mock_safe_post_to_slack):
        # Dynamically build many variants
        data = WEEKLY_XML_RELEASE_HEADER
        for i in range(BATCH_SIZE * 2 + 10):
            data += f'''
            <VariationArchive RecordType="classified" NumberOfSubmissions="38" NumberOfSubmitters="36" DateLastUpdated="2025-06-29" DateCreated="2016-03-20" MostRecentSubmission="2025-06-29">
                <ClassifiedRecord>
                    <SimpleAllele AlleleID="{i}" VariationID="5603">
                        <Location>
                            <SequenceLocation Assembly="GRCh38" Chr="1" variantLength="1" positionVCF="{i}" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                        </Location>
                    </SimpleAllele>
                    <Classifications>
                        <GermlineClassification>
                            <!-- Note no description & no review status here -->
                        </GermlineClassification>
                    </Classifications>
                </ClassifiedRecord>
            </VariationArchive>
            '''
        data += '</ClinVarVariationRelease>'
        responses.add(responses.GET, WEEKLY_XML_RELEASE, status=200, body=gzip.compress(data.encode()), stream=True)
        call_command('reload_clinvar_all_variants')
        mock_logger.assert_called_with('Updating Clinvar ClickHouse tables to 2025-06-30 from 2025-06-23.')
        self.assertEqual(ClinvarAllVariantsSnvIndel.objects.all().count(), BATCH_SIZE * 2 + 10)
        self.assertEqual(ClinvarAllVariantsSnvIndel.objects.first().pathogenicity, ClinvarAllVariantsSnvIndel.CLINVAR_DEFAULT_PATHOGENICITY)
        self.assertIsNone(ClinvarAllVariantsSnvIndel.objects.first().gold_stars)

    @responses.activate
    def test_malformed_variants(self, mock_logger, mock_safe_post_to_slack):
        for description, review_status, conflicting_pathogenicities, error_message in [
            ("Pathogenic-ey", None, None, 'Found an un-enumerated clinvar assertion: Pathogenic-ey'),
            ("Pathogenic; but unknown assertion", None, None, 'Found an un-enumerated clinvar assertion: but unknown assertion'),
            ("Pathogenic", "unhandled", None, 'Found unexpected review status unhandled'),
            ("Conflicting classifications of pathogenicity", None, "Pathogenic;", 'Failed to correctly parse conflicting pathogenicity counts: Pathogenic;'),
            ("Conflicting classifications of pathogenicity", None, "Pathogenic(18); unhandled(1)", 'Found an un-enumerated conflicting pathogenicity: unhandled'),
            ("Conflicting classifications of pathogenicity", None, None, 'Failed to find the conflicting pathogenicities node'),
        ]:
            data = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <ClinVarVariationRelease xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                     xsi:noNamespaceSchemaLocation="http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/ClinVar_VCV_2.4.xsd"
                                     ReleaseDate="2025-06-30">
                <VariationArchive>
                    <ClassifiedRecord>
                        <SimpleAllele AlleleID="1" VariationID="5603">
                            <Location>
                                <SequenceLocation Assembly="GRCh38" Chr="1" positionVCF="1" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                            </Location>
                        </SimpleAllele>
                        <Classifications>
                            <GermlineClassification>
                                <Description>{description}</Description>
                                {f"<ReviewStatus>{review_status}</ReviewStatus>" if review_status else ""}
                                {f"<Explanation>{conflicting_pathogenicities}</Explanation>" if conflicting_pathogenicities else ""}
                            </GermlineClassification>
                        </Classifications>
                    </ClassifiedRecord>
                </VariationArchive>
            </ClinVarVariationRelease>'''
            responses.add(
                responses.GET,
                WEEKLY_XML_RELEASE,
                status=200,
                body=gzip.compress(data.encode()),
                stream=True,
            )
            with self.assertRaisesMessage(CommandError, error_message):
                call_command('reload_clinvar_all_variants')

        # Variants with missing alleles and positions are skipped
        for simple_allele_attrs, sequence_location_attrs in [
            # Case 1: Missing AlleleId in <SimpleAllele>
            ("", 'Assembly="GRCh38" Chr="1" positionVCF="1" referenceAlleleVCF="G" alternateAlleleVCF="A"'),

            # Case 2: Missing alternateAlleleVCF in <SequenceLocation>
            ('AlleleID="5603"', 'Assembly="GRCh38" Chr="1" positionVCF="1" referenceAlleleVCF="G"'),
        ]:
            data = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <ClinVarVariationRelease xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                     xsi:noNamespaceSchemaLocation="http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/ClinVar_VCV_2.4.xsd"
                                     ReleaseDate="2025-06-30">
                <VariationArchive></VariationArchive>
                <VariationArchive>
                    <ClassifiedRecord>
                        <SimpleAllele {simple_allele_attrs}>
                        </SimpleAllele>
                    </ClassifiedRecord>
                </VariationArchive>
                <VariationArchive>
                    <ClassifiedRecord>
                        <SimpleAllele {simple_allele_attrs}>
                            <Location>
                                <SequenceLocation {sequence_location_attrs}/>
                            </Location>
                        </SimpleAllele>
                        <Classifications>
                            <GermlineClassification>
                                <Description>Pathogenic</Description>
                                <ReviewStatus>criteria provided, conflicting classifications</ReviewStatus>
                            </GermlineClassification>
                        </Classifications>
                    </ClassifiedRecord>
                </VariationArchive>
            </ClinVarVariationRelease>'''
            responses.add(
                responses.GET,
                WEEKLY_XML_RELEASE,
                status=200,
                body=gzip.compress(data.encode()),
                stream=True,
            )
            DataVersions.objects.all().delete()
            ClinvarAllVariantsSnvIndel.objects.using('clickhouse_write').all().delete()
            call_command('reload_clinvar_all_variants')
            self.assertEqual(ClinvarAllVariantsSnvIndel.objects.count(), 0)
            self.assertEqual(ClinvarAllVariantsGRCh37SnvIndel.objects.count(), 0)
            mock_safe_post_to_slack.assert_called_with(
                SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
                'Successfully updated Clinvar ClickHouse tables to 2025-06-30.',
            )

    @responses.activate
    def test_conflicting_data_from_submitters(self, mock_logger, mock_safe_post_to_slack):
        missing_conflicting_pathogenicities = WEEKLY_XML_RELEASE_HEADER + '''
            <VariationArchive >
                <ClassifiedRecord>
                    <SimpleAllele AlleleID="1">
                        <Location>
                            <SequenceLocation Assembly="GRCh38" Chr="1" variantLength="1" positionVCF="1" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                        </Location>
                    </SimpleAllele>
                    <Classifications>
                        <GermlineClassification>
                            <Description>conflicting data from submitters</Description>
                        </GermlineClassification>
                    </Classifications>
                </ClassifiedRecord>
            </VariationArchive>
        </ClinVarVariationRelease>
        '''
        responses.add(
            responses.GET,
            WEEKLY_XML_RELEASE,
            status=200,
            body=gzip.compress(missing_conflicting_pathogenicities.encode()),
            stream=True,
        )
        with self.assertRaisesMessage(CommandError, 'Failed to find the conflicting pathogenicities node'):
            call_command('reload_clinvar_all_variants')

        conflicting_pathogenicities = WEEKLY_XML_RELEASE_HEADER + '''
            <VariationArchive>
                <ClassifiedRecord>
                    <SimpleAllele AlleleID="1">
                        <Location>
                            <SequenceLocation Assembly="GRCh38" Chr="1" variantLength="1" positionVCF="1" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                        </Location>
                    </SimpleAllele>
                    <Classifications>
                        <GermlineClassification>
                            <Description>conflicting data from submitters</Description>
                        </GermlineClassification>
                    </Classifications>
                    <ClinicalAssertionList>
                        <ClinicalAssertion>
                            <Classification>
                                <Comment>Uncertain significance(1), Likely benign (1)</Comment>
                            </Classification>
                        </ClinicalAssertion>
                        <ClinicalAssertion></ClinicalAssertion>
                    </ClinicalAssertionList>
                </ClassifiedRecord>
            </VariationArchive>
        </ClinVarVariationRelease>
        '''
        responses.add(
            responses.GET,
            WEEKLY_XML_RELEASE,
            status=200,
            body=gzip.compress(conflicting_pathogenicities.encode()),
            stream=True,
        )
        call_command('reload_clinvar_all_variants')
        self.assertEqual(ClinvarAllVariantsSnvIndel.objects.count(), 1)
        mock_safe_post_to_slack.assert_called_with(
            SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            'Successfully updated Clinvar ClickHouse tables to 2025-06-30.',
        )