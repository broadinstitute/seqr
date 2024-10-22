import React from 'react'
import { BrowserRouter as Router } from 'react-router-dom'
import { Provider } from 'react-redux'
import configureStore from 'redux-mock-store'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

import IndividualMetadata from './IndividualMetadata'

configure({ adapter: new Adapter() })

const DATA = [
  {
    projectGuid: 'R0003_test',
    num_saved_variants: 2,
    solve_status: 'Tier 1',
    'gene_known_for_phenotype-1': 'Candidate',
    'gene_known_for_phenotype-2': 'Candidate',
    'variant_inheritance-1': 'unknown',
    'variant_inheritance-2': 'unknown',
    hpo_absent: '',
    'genetic_findings_id-1': 'NA20889_1_248367227',
    'genetic_findings_id-2': 'NA20889_1_249045487_DEL',
    'hgvsc-1': 'c.3955G>A',
    date_data_generation: '2017-02-05',
    'copy_number-1': null,
    'copy_number-2': 1,
    'zygosity-1': 'Heterozygous',
    'zygosity-2': 'Heterozygous',
    'ref-1': 'TC',
    'sv_type-2': 'Deletion',
    'sv_name-2': 'DEL:chr12:49045487-49045898',
    'validated_name-2': 'DEL:chr12:49045123-49045456',
    'chrom-2': '12',
    'chrom_end-2': null,
    'pos-2': '49045487',
    'pos_end-2': '49045898',
    maternal_id: '',
    paternal_id: '',
    maternal_guid: '',
    paternal_guid: '',
    'hgvsp-1': 'c.1586-17C>G',
    internal_project_id: 'Test Reprocessed Project',
    'chrom_end-1': null,
    'pos-1': 248367227,
    'pos_end-1': null,
    data_type: 'WES',
    familyGuid: 'F000012_12',
    family_history: 'Yes',
    hpo_present: 'HP:0011675 (Arrhythmia)|HP:0001509 ()',
    'transcript-1': 'ENST00000505820',
    'seqr_chosen_consequence-1': 'intron_variant',
    ancestry: 'Ashkenazi Jewish',
    sex: 'Female',
    sex_detail: 'XXX',
    'chrom-1': '1',
    'alt-1': 'T',
    'gene_of_interest-1': 'OR4G11P',
    'gene_id-1': 'ENSG00000240361',
    pmid_id: null,
    phenotype_description: null,
    affected_status: 'Affected',
    analysisStatus: 'Q',
    filter_flags: '',
    disorders: null,
    family_id: '12',
    displayName: '12',
    MME: 'Yes',
    participant_id: 'NA20889',
    individual_guid: 'I000017_na20889',
    proband_relationship: 'Self',
    condition_id: 'OMIM:616126',
    condition_inheritance: 'Autosomal recessive',
    known_condition_name: 'Immunodeficiency 38',
    'phenotype_contribution-1': 'Partial',
    'phenotype_contribution-2': 'Full',
    'partial_contribution_explained-1': 'HP:0000501|HP:0000365',
    'partial_contribution_explained-2': '',
    'ClinGen_allele_ID-1': 'CA1501729',
    'ClinGen_allele_ID-2': null,
  },
]

test('IndividualMetadata render and export', () => {
  const store = configureStore()({ user: {} })
  const sampleMetadata = mount(<Provider store={store}><Router><IndividualMetadata projectGuid="all" data={DATA} match={{params: {}}} /></Router></Provider>)
  const exportConfig = sampleMetadata.find('DataTable').instance().exportConfig(DATA)[0]
  expect(exportConfig.headers).toEqual([
    'project_id', 'projectGuid', 'family_id', 'familyGuid', 'participant_id', 'individual_guid', 'paternal_id',
    'paternal_guid', 'maternal_id', 'maternal_guid', 'proband_relationship', 'sex', 'ancestry', 'affected_status',
    'hpo_present', 'hpo_absent', 'MME', 'pmid_id', 'condition_id', 'known_condition_name', 'condition_inheritance', 'disorders',
    'phenotype_description', 'analysis_groups', 'analysis_status', 'solve_status', 'data_type', 'date_data_generation',
    'filter_flags', 'consanguinity', 'family_history', 'genetic_findings_id-1', 'variant_reference_assembly-1',
    'chrom-1', 'pos-1', 'chrom_end-1', 'pos_end-1', 'ref-1', 'alt-1', 'gene_of_interest-1', 'gene_id-1', 'seqr_chosen_consequence-1', 'transcript-1',
    'hgvsc-1', 'hgvsp-1', 'zygosity-1', 'copy_number-1', 'sv_name-1', 'validated_name-1', 'sv_type-1', 'variant_inheritance-1', 'gene_known_for_phenotype-1',
    'phenotype_contribution-1', 'partial_contribution_explained-1', 'notes-1', 'ClinGen_allele_ID-1',
    'genetic_findings_id-2', 'variant_reference_assembly-2', 'chrom-2', 'pos-2', 'chrom_end-2', 'pos_end-2',
    'ref-2', 'alt-2', 'gene_of_interest-2', 'gene_id-2', 'seqr_chosen_consequence-2', 'transcript-2', 'hgvsc-2', 'hgvsp-2',
    'zygosity-2', 'copy_number-2', 'sv_name-2', 'validated_name-2', 'sv_type-2', 'variant_inheritance-2', 'gene_known_for_phenotype-2',
    'phenotype_contribution-2', 'partial_contribution_explained-2', 'notes-2', 'ClinGen_allele_ID-2'])
  expect(exportConfig.processRow(DATA[0])).toEqual([
    'Test Reprocessed Project', 'R0003_test', '12', 'F000012_12', 'NA20889', 'I000017_na20889', '', '', '', '',
    'Self', 'Female (XXX)', 'Ashkenazi Jewish', 'Affected', 'HP:0011675 (Arrhythmia)|HP:0001509 ()', '', 'Yes', null,
    'OMIM:616126', 'Immunodeficiency 38', 'Autosomal recessive', null, null, undefined, 'Waiting for data', 'Tier 1',
    'WES', '2017-02-05', '', undefined, 'Yes', 'NA20889_1_248367227', undefined, '1', 248367227, null, null, 'TC', 'T',
    'OR4G11P', 'ENSG00000240361', 'intron_variant', 'ENST00000505820', 'c.3955G>A', 'c.1586-17C>G', 'Heterozygous', null, undefined, undefined, undefined,
    'unknown', 'Candidate', 'Partial', 'HP:0000501|HP:0000365', undefined, 'CA1501729', 'NA20889_1_249045487_DEL', undefined,
    '12', '49045487', null, '49045898', undefined, undefined, undefined, undefined, undefined,
    undefined, undefined, undefined, 'Heterozygous', 1, 'DEL:chr12:49045487-49045898', 'DEL:chr12:49045123-49045456', 'Deletion',
    'unknown', 'Candidate', 'Full', '', undefined, null])
})
