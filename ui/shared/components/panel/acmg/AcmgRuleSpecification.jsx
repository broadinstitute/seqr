import React from 'react'
import { Header, Table, List, Label } from 'semantic-ui-react'
import { ACMG_RULE_SPECIFICATION_CATEGORY_CRITERIA, ACMG_RULE_SPECIFICATION_COMP_HET, ACMG_RULE_SPECIFICATION_DISEASE_BASED_CRITERIA, ACMG_RULE_SPECIFICATION_GENERAL_RECOMMENDATIONS, ACMG_RULE_SPECIFICATION_IN_TRANS, ACMG_RULE_SPECIFICATION_LEVELS_TABLE, ACMG_RULE_SPECIFICATION_PM3, ACMG_RULE_SPECIFICATION_PROBAND } from '../../../utils/constants'

const tableCellsWithSingleValue = (values, alignment = 'center') => {
  const row = (
    <Table.Row textAlign={alignment}>
      {values.map(value => <Table.Cell>{value}</Table.Cell>)}
    </Table.Row>
  )

  return row
}

const tableCellsWithListItemLink = (items) => {
  const list = (
    <List bulleted>
      {items.map(item => (
        <List.Item
          key={item.key}
        >
          {/* eslint-disable react/jsx-one-expression-per-line */}
          {item.value}: <a href={item.href} target="_blank" rel="noreferrer">{item.href}</a>
        </List.Item>
      ))}
    </List>
  )

  return list
}

const tableCellsWithOptionalListItems = (items, labelColor = null) => {
  const row = (
    <Table.Row textAlign="center">
      {items.map((item) => {
        const cell = (
          !item.isList ? <Table.Cell color={labelColor}>{item.value}</Table.Cell> : (
            <Table.Cell textAlign="left">
              {item.description}:
              <List bulleted>
                {item.listItems.map(listItem => <List.Item key={listItem.key}>{listItem.value}</List.Item>)}
              </List>
            </Table.Cell>
          )
        )

        return cell
      })}
    </Table.Row>
  )

  return row
}

const tableCellsWithLabelAndOptionalListItems = (items, labelColor = null) => {
  const cell = (
    <Table.Cell>
      {items.map((item) => {
        const labelOrListItem = (
          !item.isList ? <Label color={labelColor}>{item.value}</Label> : (
            <List bulleted>
              {item.listItems.map(listItem => <List.Item key={listItem.key}>{listItem.value}</List.Item>)}
            </List>
          )
        )

        return labelOrListItem
      })}
    </Table.Cell>
  )

  return cell
}

const tableListItemsForCriteria = (items, criteria) => {
  const row = (
    <Table.Row>
      <Table.Cell textAlign="center">{criteria}</Table.Cell>
      <Table.Cell colSpan="2">
        <List bulleted>
          {items.map(item => <List.Item key={item.key}>{item.value}</List.Item>)}
        </List>
      </Table.Cell>
    </Table.Row>
  )

  return row
}

const tableRowWithTableCells = (items, description, cellsWithList = false, color = 'blue') => {
  const row = (
    <Table.Row>
      <Table.Cell textAlign="center">{description}</Table.Cell>
      {items.map((item) => {
        const cell = (
          <Table.Cell>
            <Table>
              <Table.Body>
                {cellsWithList ?
                  tableCellsWithLabelAndOptionalListItems(item, color) :
                  item.map(rule => tableCellsWithSingleValue(rule, null))}
              </Table.Body>
            </Table>
          </Table.Cell>
        )

        return cell
      })}
    </Table.Row>
  )

  return row
}

const AcmgRuleSpecification = () => {
  const ruleSpecification = (
    <div>
      <Header>Rule Specification</Header>

      <Table celled structured padded>
        <Table.Body>
          {ACMG_RULE_SPECIFICATION_CATEGORY_CRITERIA.map(c => tableListItemsForCriteria(c.rules, c.name))}

          {tableRowWithTableCells(ACMG_RULE_SPECIFICATION_PROBAND, 'Proband Count (PS4)')}

          {tableRowWithTableCells(ACMG_RULE_SPECIFICATION_IN_TRANS, 'In Trans (PM3)', true)}

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
                    <Table.HeaderCell rowSpan="2" />
                    <Table.HeaderCell colSpan="3" textAlign="center">General Recommendations (Phenocopy not an issue)</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>

                <Table.Body>
                  {ACMG_RULE_SPECIFICATION_LEVELS_TABLE.map(row => tableCellsWithSingleValue(row))}
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
                    <Table.Cell />
                    {(Array.from(Array(11).keys())).map(number => <Table.Cell>{number}</Table.Cell>)}
                  </Table.Row>

                  {
                    ACMG_RULE_SPECIFICATION_GENERAL_RECOMMENDATIONS.map(row => tableCellsWithSingleValue(row))
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
                  {ACMG_RULE_SPECIFICATION_PM3.map(row => tableCellsWithSingleValue(row))}
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
                      {tableCellsWithListItemLink(ACMG_RULE_SPECIFICATION_DISEASE_BASED_CRITERIA)}
                    </Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>
                      ClinGen Registry: <a href="https://cspec.genome.network/cspec/ui/svi/" target="_blank" rel="noreferrer">https://cspec.genome.network/cspec/ui/svi/</a>
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell colSpan="3">
              <Table color="blue">
                <Table.Header>
                  <Table.HeaderCell textAlign="center" />
                  <Table.HeaderCell textAlign="center">Comp Het Only</Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Hom only</Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Comp Het + Hom</Table.HeaderCell>
                </Table.Header>

                {ACMG_RULE_SPECIFICATION_COMP_HET.map(row => tableCellsWithOptionalListItems(row))}
              </Table>
            </Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
    </div>
  )

  return ruleSpecification
}

export default AcmgRuleSpecification
