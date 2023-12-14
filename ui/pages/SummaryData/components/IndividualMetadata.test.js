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
    solve_state: 'Tier 1',
    sample_id: 'NA20889',
    'Gene_Class-1': 'Tier 1 - Candidate',
    'Gene_Class-2': 'Tier 1 - Candidate',
    'inheritance_description-1': 'Autosomal recessive (compound heterozygous)',
    'inheritance_description-2': 'Autosomal recessive (compound heterozygous)',
    hpo_absent: '',
    'novel_mendelian_gene-1': 'Y',
    'novel_mendelian_gene-2': 'Y',
    'hgvsc-1': 'c.3955G>A',
    date_data_generation: '2017-02-05',
    'Zygosity-1': 'Heterozygous',
    'Zygosity-2': 'Heterozygous',
    'Ref-1': 'TC',
    'sv_type-2': 'Deletion',
    'sv_name-2': 'DEL:chr12:49045487-49045898',
    'Chrom-2': '12',
    'Pos-2': '49045487',
    maternal_id: '',
    paternal_id: '',
    maternal_guid: '',
    paternal_guid: '',
    'hgvsp-1': 'c.1586-17C>G',
    project_id: 'Test Reprocessed Project',
    'Pos-1': '248367227',
    data_type: 'WES',
    familyGuid: 'F000012_12',
    congenital_status: 'Unknown',
    family_history: 'Yes',
    hpo_present: 'HP:0011675 (Arrhythmia)|HP:0001509 ()',
    'Transcript-1': 'ENST00000505820',
    ancestry: 'Ashkenazi Jewish',
    phenotype_group: '',
    sex: 'Female',
    'Chrom-1': '1',
    'Alt-1': 'T',
    'Gene-1': 'OR4G11P',
    'gene_id-1': 'ENSG00000240361',
    pmid_id: null,
    phenotype_description: null,
    affected_status: 'Affected',
    analysisStatus: 'Q',
    filter_flags: '',
    disorders: null,
    family_id: '12',
    displayName: '12',
    MME: 'Y',
    subject_id: 'NA20889',
    individual_guid: 'I000017_na20889',
    proband_relationship: 'Self',
    consanguinity: 'None suspected',
  },
]

test('IndividualMetadata render and export', () => {
  const store = configureStore()({ user: {} })
  const sampleMetadata = mount(<Provider store={store}><Router><IndividualMetadata projectGuid="all" data={DATA} match={{params: {}}} /></Router></Provider>)
  const exportConfig = sampleMetadata.find('DataTable').instance().exportConfig(DATA)[0]
  expect(exportConfig.headers).toEqual([
    'project_id', 'projectGuid', 'family_id', 'familyGuid', 'subject_id', 'individual_guid', 'pmid_id', 'paternal_id',
    'paternal_guid', 'maternal_id', 'maternal_guid', 'proband_relationship', 'sex', 'ancestry', 'phenotype_group',
    'disease_id', 'disease_description', 'disorders', 'affected_status', 'congenital_status', 'hpo_present', 'hpo_absent',
    'phenotype_description', 'solve_state', 'analysisStatus', 'MME', 'sample_id', 'data_type', 'date_data_generation',
    'filter_flags', 'consanguinity', 'family_history', 'Gene-1', 'gene_id-1', 'Gene_Class-1', 'novel_mendelian_gene-1',
    'phenotype_class-1', 'inheritance_description-1', 'Zygosity-1', 'Chrom-1', 'Pos-1', 'Ref-1', 'Alt-1', 'hgvsc-1',
    'hgvsp-1', 'Transcript-1', 'sv_name-1', 'sv_type-1', 'discovery_notes-1', 'Gene-2', 'gene_id-2', 'Gene_Class-2',
    'novel_mendelian_gene-2', 'phenotype_class-2', 'inheritance_description-2', 'Zygosity-2', 'Chrom-2', 'Pos-2',
    'Ref-2', 'Alt-2', 'hgvsc-2', 'hgvsp-2', 'Transcript-2', 'sv_name-2', 'sv_type-2', 'discovery_notes-2'])
  expect(exportConfig.processRow(DATA[0])).toEqual([
    'Test Reprocessed Project', 'R0003_test', '12', 'F000012_12', 'NA20889', 'I000017_na20889', null, '', '', '', '',
    'Self', 'Female', 'Ashkenazi Jewish', '', undefined, undefined, null, 'Affected', 'Unknown',
    'HP:0011675 (Arrhythmia)|HP:0001509 ()', '', null, 'Tier 1', 'Q', 'Y', 'NA20889', 'WES', '2017-02-05', '',
    'None suspected', 'Yes', 'OR4G11P', 'ENSG00000240361', 'Tier 1 - Candidate', 'Y', undefined,
    'Autosomal recessive (compound heterozygous)', 'Heterozygous', '1', '248367227', 'TC', 'T', 'c.3955G>A',
    'c.1586-17C>G', 'ENST00000505820', undefined, undefined, undefined, undefined, undefined, 'Tier 1 - Candidate', 'Y',
    undefined, 'Autosomal recessive (compound heterozygous)', 'Heterozygous', '12', '49045487', undefined, undefined,
    undefined, undefined, undefined, 'DEL:chr12:49045487-49045898', 'Deletion', undefined])
})
