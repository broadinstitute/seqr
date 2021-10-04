import React from 'react'
import { Header, Table, List, Label } from 'semantic-ui-react'

const tableCellsWithSingleValue = (values, alignment = 'center') => {
  return (
    <Table.Row textAlign={alignment}>
      { values.map(value => <Table.Cell>{ value }</Table.Cell>) }
    </Table.Row>
  )
}

const tableCellsWithListItemLink = (items) => {
  return (
    <List bulleted>
      { items.map(item => <List.Item key={item.key}>{ item.value }: <a href={item.href} target="_blank">{ item.href }</a></List.Item>) }
    </List>
  )
}

const tableCellsWithOptionalListItems = (items, labelColor = null) => {
  return (
    <Table.Row textAlign="center">
      { items.map((item) => {
        return !item.isList ? <Table.Cell color={labelColor}>{ item.value }</Table.Cell> :
        <Table.Cell textAlign="left">
          { item.description }:
          <List bulleted>
            { item.listItems.map(listItem => <List.Item key={listItem.key}>{ listItem.value }</List.Item>) }
          </List>
        </Table.Cell>
      }) }
    </Table.Row>
  )
}

const tableCellsWithLabelAndOptionalListItems = (items, labelColor = null) => {
  return (
    <Table.Row>
      <Table.Cell>
        { items.map((item) => {
          return !item.isList ? <Label color={labelColor}>{ item.value }</Label> :
          <List bulleted>
            { item.listItems.map(listItem => <List.Item key={listItem.key}>{ listItem.value }</List.Item>) }
          </List>
        }) }
      </Table.Cell>
    </Table.Row>
  )
}

const tableListItemsForCriteria = (items, criteria) => {
  return (
    <Table.Row>
      <Table.Cell textAlign="center">{ criteria }</Table.Cell>
      <Table.Cell colSpan="2">
        <List bulleted>
          { items.map(item => <List.Item key={item.key}>{ item.value }</List.Item>) }
        </List>
      </Table.Cell>
    </Table.Row>
  )
}

const AcmgRuleSpecification = () => {
  return (
    <div>
      <Header>Rule Specification</Header>

      <Table celled structured padded>
        <Table.Body>
          { tableListItemsForCriteria([
            { key: 'rs_hcm_dcm_01', value: 'HCM/DCM: >= 0.1%' },
            { key: 'rs_noonan_005', value: 'Noonan: >= 0.05%' },
            { key: 'rs_default_06', value: 'Default: >= 0.6%' },
            { key: 'rs_autosomal_recessive_05', value: 'HL (Autosomal recessive): >= 0.5%' },
            { key: 'hl_autosomal_dominan_01', value: 'HL (Autosomal dominant): >= 0.1%' },
          ], 'BA1') }

          { tableListItemsForCriteria([
            { key: 'rs_hcm_dcm_02', value: 'HCM/DCM: >= 0.2%' },
            { key: 'rs_noonan_0025', value: 'Noonan: >= 0.025%' },
            { key: 'rs_default_03', value: 'Default: >= 0.3%' },
            { key: 'rs_autosomal_recessive_03', value: 'HL (Autosomal recessive): >= 0.3%' },
            { key: 'hl_autosomal_dominan_02', value: 'HL (Autosomal dominant): >= 0.02%' },
          ], 'BS1') }

          { tableListItemsForCriteria([
            { key: 'rs_autosomal_recessive_0703', value: 'HL (Autosomal recessive): 0.07-0.3%' },
          ], 'BS1_P') }

          { tableListItemsForCriteria([
            { key: 'rs_autosomal_recessive_007', value: 'HL (Autosomal recessive): <= 0.007%' },
            { key: 'hl_autosomal_dominan_002', value: 'HL (Autosomal dominant): <= 0.002%' },
          ], 'PM2_P') }

          <Table.Row>
            <Table.Cell textAlign="center">Proband Count (PS4)</Table.Cell>
            <Table.Cell>
              <Table>
                <Table.Body>
                  { [['Noonan', '#'], ['Strong', '5'], ['Moderate', '3'], ['Supporting', 1]].map(row => tableCellsWithSingleValue(row, null)) }
                </Table.Body>
              </Table>
            </Table.Cell>

            <Table.Cell>
              <Table>
                <Table.Body>
                  { [['Cardio', '#'], ['Strong', '15'], ['Moderate', '6'], ['Supporting', '2']].map(row => tableCellsWithSingleValue(row, null)) }
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">In Trans (PM3)</Table.Cell>

            <Table.Cell>
              <Table>
                <Table.Body>
                  { tableCellsWithLabelAndOptionalListItems([
                    { value: 'Increase to PM3_Strong if observed in trans' },
                    {
                      isList: true,
                      listItems: [
                        { key: 'rs_2x_and_1_variant_path', value: '2x and >= 1 variant in PATH' },
                        { key: 'rs_3x_other_variants_lp', value: '3x if other variants are LP' },
                      ],
                    },
                  ], 'blue') }
                </Table.Body>
              </Table>
            </Table.Cell>

            <Table.Cell>
              <Table>
                <Table.Body>
                  { tableCellsWithLabelAndOptionalListItems([
                    { value: 'Increase to VeryStrong if observed in trans' },
                    {
                      isList: true,
                      listItems: [
                        { key: 'rs_4x_and_2_variant_path', value: '4x and >= 2 variant in PATH (can be same variant)' },
                        { key: 'rs_4x_lpp_different', value: '4x if LP/P variants are all different' },
                      ],
                    },
                  ], 'blue') }
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">BP7</Table.Cell>
            <Table.Cell colSpan="2">Nonconserved splice is for variants at positions: -4, +7 to +15<br />AND<br />{'-5 to -15 positions with changes >T or >C'}</Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">PP1 (Hearing loss)</Table.Cell>
            <Table.Cell colSpan="2">
              <Table color="blue">
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell rowSpan="2"></Table.HeaderCell>
                    <Table.HeaderCell colSpan="3" textAlign="center">General Recommendations (Phenocopy not an issue)</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>

                <Table.Body>
                  { [
                    ['', 'Supporting', 'Moderate', 'Strong'],
                    ['Likelihood', '4:1', '16:1', '32:1'],
                    ['LOD Score', '0.6', '1.2', '1.5'],
                    ['Autosomal dominant threshold', '2 affected segregations', '4 affected segregations', '5 affected segregations<'],
                    ['Autosomal recessive threshold', 'See Table 2', 'See Table 2', 'See Table 2'],
                  ].map(row => tableCellsWithSingleValue(row)) }
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">Affected Segregations</Table.Cell>
            <Table.Cell colSpan="2">
              <Table color="blue">
                <Table.Header>
                  <Table.Row textAlign="center">
                    <Table.HeaderCell colSpan="12">General Recommendations (Phenocopy not an issue)</Table.HeaderCell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.HeaderCell colSpan="12">Unaffected Segregations</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>

                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell></Table.Cell>
                    {(Array.from(Array(11).keys())).map(number => <Table.Cell>{number}</Table.Cell>)}
                  </Table.Row>

                  {
                    [
                      [0, 0, 0.12, 0.25, 0.37, 0.5, 0.62, 0.75, 0.87, 1, 1.2, 1.25],
                      [1, 0.6, 0.73, 0.85, 0.98, 1.1, 1.23, 1.35, 1.48, 1.6, 1.73, 1.85],
                      [2, 1.2, 1.33, 1.45, 1.58, 1.7, 1.83, 1.95, 2.08, 2.2, 2.33, 2.45],
                      [3, 1.81, 1.83, 2.06, 2.18, 2.31, 2.43, 2.56, 2.68, 2.81, 2.93, 3.06],
                      [4, 2.41, 2.53, 2.66, 2.78, 2.91, 3.03, 3.16, 3.28, 3.41, 3.53, 3.06],
                      [5, 3.01, 3.14, 3.26, 3.39, 3.51, 3.63, 3.76, 3.88, 4.01, 4.13, 4.26],
                      [6, 3.61, 3.74, 3.86, 3.99, 4.11, 4.24, 4.36, 4.49, 4.61, 4.74, 4.86],
                      [7, 4.21, 4.34, 4.46, 4.59, 4.71, 4.84, 4.96, 5.09, 5.21, 5.34, 5.46],
                      [8, 4.82, 4.94, 5.07, 5.19, 5.32, 5.44, 5.57, 5.69, 5.82, 5.94, 6.07],
                      [9, 5.42, 5.54, 5.67, 5.79, 5.92, 6.04, 6.17, 6.29, 6.42, 6.54, 6.67],
                      [10, 6.02, 6.15, 6.27, 6.4, 6.52, 6.65, 6.77, 6.9, 7.02, 7.15, 7.27],
                    ].map(row => tableCellsWithSingleValue(row))
                  }
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">PM3 (Hearing Loss)</Table.Cell>
            <Table.Cell colSpan="2">
              <Table color="blue">
                <Table.Header>
                  <Table.Row textAlign="center">
                    <Table.HeaderCell>Classification/zygosity of other variant</Table.HeaderCell>
                    <Table.HeaderCell>Known in trans</Table.HeaderCell>
                    <Table.HeaderCell>Phase unknown</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>

                <Table.Body>
                  { [
                    ['Pathogenic/Likely pathogenic', '1.0', '0.5'],
                    ['Homozygous occurrence (Max points from homozygotes 1)', '0.5', 'N/A'],
                    ['Homozygous occurrence due to consanguinity, rare uncertain significance (confirmed in trans) (Max point 0.5)', '0.25', '0'],
                  ].map(row => tableCellsWithSingleValue(row)) }
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">Disease-based Criteria Specifications- curated by ClinGen</Table.Cell>
            <Table.Cell colSpan="2">
              <Table>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell>
                      { tableCellsWithListItemLink([
                        { key: 'cardiomyopathy', value: 'Cardiomyopathy', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN002' },
                        { key: 'rasopathy', value: 'RASopathy', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN004' },
                        { key: 'hearing-loss', value: 'Hearing Loss', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN005' },
                        { key: 'rett-angelman-disorders', value: 'Rett and Angelman-like Disorders', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN016' },
                        { key: 'mitochondrial-disease-mitochondrial', value: 'Mitochondrial Disease Mitochondrial', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN015' },
                        { key: 'mitochondrial-disease-nuclear', value: 'Mitochondrial Disease Nuclear', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN014' },
                        { key: 'hypercholesterolemia', value: 'Hypercholesterolemia', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN013' },
                        { key: 'hyperthermia-susceptibility', value: 'Hyperthermia Susceptibility', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN012' },
                        { key: 'platelet-discorders', value: 'Platelet Disorders', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN011' },
                        { key: 'lysosmal-storage-disorders', value: 'Lysosomal Storage Disorders', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN010' },
                        { key: 'pten', value: 'PTEN', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN003' },
                        { key: 'myeloid-malignancy', value: 'Myeloid Malignancy', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN008' },
                        { key: 'cdh1', value: 'CDH1', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN008' },
                        { key: 'tps3', value: 'TPS3', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN009' },
                        { key: 'pah', value: 'PAH', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN006' },
                      ]) }
                    </Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>ClinGen Registry: <a href="https://cspec.genome.network/cspec/ui/svi/" target="_blank">https://cspec.genome.network/cspec/ui/svi/</a></Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell colSpan="3">
              <Table color="blue">
                <Table.Header>
                  <Table.HeaderCell textAlign="center"></Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Comp Het Only</Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Hom only</Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Comp Het + Hom</Table.HeaderCell>
                </Table.Header>

                { tableCellsWithOptionalListItems([
                  { value: 'Supporting (PM3_Supporting) (total 0.5 points)' },
                  { value: '1 observation with LP/P but phase unknown or 2 VUS co-occurrences (exception: large genes)' },
                  { value: '1 with ADO rules out' },
                  { value: 'N/A' },
                ]) }

                { tableCellsWithOptionalListItems([
                  { value: 'Moderate (PM3) (total 1.0 points)' },
                  { value: '1 comp het  with LP/P 2 observations with different LP/P but phase unknown' },
                  { value: '2 difference families and use of exome data to rule out consanguinity' },
                  {
                    description: 'A combination of the following adding to 1 point',
                    isList: true,
                    listItems: [
                      { key: 'rs_observations_with_lpp', value: 'Observations with LP/P but phase unknown' },
                      { key: 'rs_compund_rare_vus', value: 'Compound het with rare VUS' },
                      { key: 'rs_hom_ado_rules_out', value: 'Hom w/ ADO rules out' },
                    ],
                  },
                ]) }

                { tableCellsWithOptionalListItems([
                  { value: 'Strong (PM3_Strong) (total 2.0 points)' },
                  { value: '2 comp het' },
                  { value: 'N/A' },
                  {
                    desription: 'A combination of the following adding to 2 points',
                    isList: true,
                    listItems: [
                      { key: 'rs_comp_lpp', value: 'Comp het with LP/P' },
                      { key: 'rs_hom_ado_rules_out_2', value: 'Hom w/ ADO rules out' },
                      { key: 'rs_observations_lpp_phase_unknown', value: 'Observations with different LP/P but phase unknown' },
                      { key: 'rs_compund_rare_vus_2', value: 'Compund het with rare VUS' },
                    ],
                  },
                ]) }

                { tableCellsWithOptionalListItems([
                  { value: 'Very Strong (PM3_VeryStrong) (total 4.0 points)' },
                  { value: '4 comp het' },
                  { value: 'N/A' },
                  {
                    description: 'A combination of the following adding to 4 points',
                    isList: true,
                    listItems: [
                      { key: 'rs_comp_lpp_2', value: 'Comp hets with LP/P' },
                      { key: 'rs_different_observations_lpp_phase_unknown', value: 'Different observations with LP/P but phase unknown' },
                      { key: 'rs_compund_rare_vus_3', value: 'Compound het with rare VUS' },
                      { key: 'rs_hom_ado_rules_out_3', value: 'How w/ ADO ruled out' },
                    ],
                  },
                ]) }
              </Table>
            </Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
    </div>
  )
}

export default AcmgRuleSpecification
