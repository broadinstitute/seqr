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
    ClinvarAllVariantsGRCh37SnvIndel, ClinvarAllVariantsMito, KeyLookupSnvIndel, KeyLookupMito,
)
from reference_data.models import DataVersions
from seqr.management.commands.reload_clinvar_all_variants import BATCH_SIZE, WEEKLY_XML_RELEASE

WEEKLY_XML_RELEASE_DATA = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ClinVarVariationRelease
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/ClinVar_VCV_2.4.xsd" ReleaseDate="2025-06-30">
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
                <ClinicalAssertion ID="498361" SubmissionDate="2016-03-03" ContributesToAggregateClassification="true" DateLastUpdated="2016-03-20" DateCreated="2016-03-20">
                    <ClinVarAccession SubmitterName="University of Washington Department of Laboratory Medicine, University of Washington" OrgID="506834" OrganizationCategory="laboratory"/>
                </ClinicalAssertion>
                <ClinicalAssertion ID="1193578" SubmissionDate="2017-05-23" ContributesToAggregateClassification="true" DateLastUpdated="2017-11-11" DateCreated="2017-11-11">
                    <ClinVarAccession SubmitterName="Fulgent Genetics, Fulgent Genetics" OrgID="500105" OrganizationCategory="laboratory"/>
                </ClinicalAssertion>
                <ClinicalAssertion ID="3962971" SubmissionDate="2023-03-01" ContributesToAggregateClassification="true" DateLastUpdated="2023-03-11" DateCreated="2021-11-29">
                    <ClinVarAccession SubmitterName="Revvity Omics, Revvity" OrgID="167595" OrganizationCategory="laboratory"/>
                </ClinicalAssertion>
                <TraitMappingList>
                    <TraitMapping ClinicalAssertionID="7894954" TraitType="Disease" MappingType="Name" MappingValue="Not provided" MappingRef="Preferred">
                        <MedGen CUI="C3661900" Name="not provided"/>
                    </TraitMapping>
                    <TraitMapping ClinicalAssertionID="3442426" TraitType="Finding" MappingType="XRef" MappingValue="HP:0003002" MappingRef="HP">
                        <MedGen CUI="C0678222" Name="Breast carcinoma"/>
                    </TraitMapping>
                    <TraitMapping ClinicalAssertionID="8838596" TraitType="Disease" MappingType="Name" MappingValue="CHEK2-related condition" MappingRef="Preferred">
                        <MedGen CUI="None" Name="CHEK2-related disorder"/>
                    </TraitMapping>
                    <TraitMapping ClinicalAssertionID="1790057" TraitType="Disease" MappingType="Name" MappingValue="CHEK2-Related Cancer Susceptibility" MappingRef="Preferred">
                        <MedGen CUI="C5882668" Name="CHEK2-related cancer predisposition"/>
                    </TraitMapping>
                    <TraitMapping ClinicalAssertionID="4961845" TraitType="Disease" MappingType="XRef" MappingValue="C0027672" MappingRef="MedGen">
                        <MedGen CUI="C0027672" Name="Hereditary cancer-predisposing syndrome"/>
                    </TraitMapping>
                </TraitMappingList>
            </ClinicalAssertionList>
        </ClassifiedRecord>
    </VariationArchive>
    <VariationArchive VariationID="5603" VariationName="NM_007194.4(CHEK2):c.1283C>T (p.Ser428Phe)" VariationType="single nucleotide variant" Accession="VCV000005603" Version="104" RecordType="classified" NumberOfSubmissions="38" NumberOfSubmitters="36" DateLastUpdated="2025-06-29" DateCreated="2016-03-20" MostRecentSubmission="2025-06-29">
        <ClassifiedRecord>
            <SimpleAllele AlleleID="20642" VariationID="5603">
                <Location>
                    <SequenceLocation Assembly="GRCh38" Chr="MT" Accession="NC_000022.11" start="123" stop="123" display_start="123" display_stop="28695219" variantLength="1" positionVCF="123" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                </Location>
            </SimpleAllele>
            <Classifications>
                <GermlineClassification DateLastEvaluated="2025-04-01" NumberOfSubmissions="38" NumberOfSubmitters="36" DateCreated="2016-03-20" MostRecentSubmission="2025-06-29">
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

    @responses.activate
    def test_new_version_already_exists(self, mock_logger, mock_safe_post_to_slack):
        DataVersions('Clinvar', '2025-06-30').save()
        responses.add(responses.GET, WEEKLY_XML_RELEASE, status=200, body=gzip.compress(WEEKLY_XML_RELEASE_DATA.encode()), stream=True)
        call_command('reload_clinvar_all_variants')
        mock_logger.assert_called_with('Clinvar ClickHouse tables already successfully updated to 2025-06-30, gracefully exiting.')

    @responses.activate
    def test_parse_variants_all_types(self, mock_logger, mock_safe_post_to_slack):
        KeyLookupSnvIndel.objects.using('clickhouse_write').create(
            variant_id='22-28695219-G-A',
            key_id=12,
        )
        KeyLookupMito.objects.using('clickhouse_write').create(
            variant_id='M-123-GA',
            key_id=8,
        )
        ClinvarAllVariantsSnvIndel.objects.using('clickhouse_write').create(
            version='2025-06-23',
            variant_id='22-28695219-G-A',
            allele_id=20642,
            pathogenicity='Likely_pathogenic',
            assertions=[],
            conflicting_pathogenicities=[],
            gold_stars=2,
            submitters=[],
            conditions=[]
        )
        DataVersions('Clinvar', '2025-06-23').save()
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
        self.assertEqual(
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
        data = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ClinVarVariationRelease xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/ClinVar_VCV_2.4.xsd" ReleaseDate="2025-06-30">'
        for i in range(BATCH_SIZE * 2 + 10):
            data += f'''
            <VariationArchive VariationID="5603" VariationName="NM_007194.4(CHEK2):c.1283C>T (p.Ser428Phe)" VariationType="single nucleotide variant" Accession="VCV000005603" Version="104" RecordType="classified" NumberOfSubmissions="38" NumberOfSubmitters="36" DateLastUpdated="2025-06-29" DateCreated="2016-03-20" MostRecentSubmission="2025-06-29">
                <ClassifiedRecord>
                    <SimpleAllele AlleleID="{i}" VariationID="5603">
                        <Location>
                            <SequenceLocation Assembly="GRCh38" Chr="1" variantLength="1" positionVCF="{i}" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
                        </Location>
                    </SimpleAllele>
                    <Classifications>
                        <GermlineClassification>
                            <Description>Pathogenic</Description>
                        </GermlineClassification>
                    </Classifications>
                </ClassifiedRecord>
            </VariationArchive>
            '''
        data += '</ClinVarVariationRelease>'
        responses.add(responses.GET, WEEKLY_XML_RELEASE, status=200, body=gzip.compress(data.encode()), stream=True)
        call_command('reload_clinvar_all_variants')
        mock_logger.assert_called_with('Updating Clinvar ClickHouse tables to 2025-06-30 from None.')
        self.assertEqual(ClinvarAllVariantsSnvIndel.objects.all().count(), BATCH_SIZE * 2 + 10)

    @responses.activate
    def test_malformed_variants(self, mock_logger, mock_safe_post_to_slack):
        for description, review_status, conflicting_pathogenicities in [
            ("Pathogenic-ey", None, None),  # Unhandled Pathogenicity
            ("Pathogenic; but unknown assertion", None, None),  # Unhandled Assertion
            ("Pathogenic", "unhandled", None),  # Unhandled Review Status
            ("Conflicting classifications of pathogenicity", None, "Pathogenic(18); unhandled")
        ]:
            data = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <ClinVarVariationRelease xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                     xsi:noNamespaceSchemaLocation="http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/ClinVar_VCV_2.4.xsd"
                                     ReleaseDate="2025-06-30">
                <VariationArchive>
                    <ClassifiedRecord>
                        <SimpleAllele AlleleID="1" VariationID="5603">
                            <Location>
                                <SequenceLocation Assembly="GRCh38" Chr="1" variantLength="1"
                                                  positionVCF="1" referenceAlleleVCF="G" alternateAlleleVCF="A"/>
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

            with self.assertRaises(CommandError):
                call_command('reload_clinvar_all_variants')



        # Variants with missing alleles and positions are skipped
        for simple_allele_attrs, sequence_location_attrs in [
            # Case 1: Missing VariationID in <SimpleAllele>
            ("", 'Assembly="GRCh38" Chr="1" variantLength="1" positionVCF="1" referenceAlleleVCF="G" alternateAlleleVCF="A"'),

            # Case 2: Missing alternateAlleleVCF in <SequenceLocation>
            ('VariationID="5603"', 'Assembly="GRCh38" Chr="1" variantLength="1" positionVCF="1" referenceAlleleVCF="G"'),
        ]:
            data = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <ClinVarVariationRelease xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                     xsi:noNamespaceSchemaLocation="http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/ClinVar_VCV_2.4.xsd"
                                     ReleaseDate="2025-06-30">
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
            call_command('reload_clinvar_all_variants')




