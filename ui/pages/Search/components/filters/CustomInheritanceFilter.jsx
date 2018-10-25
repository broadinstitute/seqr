import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { formValueSelector } from 'redux-form'
import { Form, Table } from 'semantic-ui-react'

import { getFamiliesByGuid, getIndividualsByGuid } from 'redux/selectors'
import { Select } from 'shared/components/form/Inputs'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { AFFECTED, UNAFFECTED } from 'shared/utils/constants'
import { NUM_ALT_OPTIONS } from '../../constants'


const NUM_ALT_SELECT_PROPS = {
  control: Select,
  options: NUM_ALT_OPTIONS,
}

const CustomInheritanceFilter = ({ value, onChange, familyGuid, familiesByGuid, individualsByGuid }) => {
  const family = familiesByGuid[familyGuid]
  if (!family) {
    return null
  }
  const individuals = family.individualGuids.map(individualGuid => individualsByGuid[individualGuid])

  const parentGenotypes = {}
  if (value.mother || value.father) {
    individuals.forEach((individual) => {
      if (individual.affected === AFFECTED) {
        parentGenotypes[individual.maternalId] = value.mother
        parentGenotypes[individual.paternalId] = value.father
      }
    })
  }

  const individualValuesByStatus = individuals.reduce((acc, ind) => ({
    ...acc,
    [ind.affected]: {
      ...acc[ind.affected],
      [ind.individualId]:
        (value[ind.affected] || {}).genotype || ((value[ind.affected] || {}).individuals || {})[ind.individualId],
    },
  }), {})

  individualValuesByStatus[UNAFFECTED] = Object.entries(individualValuesByStatus[UNAFFECTED] || {}).reduce(
    (acc, [individualId, val]) => (
      { ...acc, [individualId]: val || parentGenotypes[individualId] || value.otherUnaffected }
    ), {},
  )

  const handleChange = individual => (val) => {
    individualValuesByStatus[individual.affected][individual.individualId] = val
    onChange(Object.entries(individualValuesByStatus).reduce((acc, [affected, indivs]) => ({
      ...acc,
      [affected]: Object.values(indivs).every(ac => ac === Object.values(indivs)[0]) ?
        { genotype: Object.values(indivs)[0] } : { individuals: indivs },
    }), {}))
  }

  return (
    <Table basic="very" compact>
      <Table.Body>
        {individuals.map((individual, i) =>
          <Table.Row key={individual.individualGuid}>
            <Table.Cell collapsing key={`${individual.individualGuid}-pedigree`}>
              <PedigreeIcon sex={individual.sex} affected={individual.affected} />
              &nbsp;
              {individual.displayName || individual.individualId}
              {individual.displayName && individual.displayName !== individual.individualId ? `(${individual.individualId})` : null}
            </Table.Cell>
            <Table.Cell>
              <Form.Field
                {...NUM_ALT_SELECT_PROPS}
                value={individualValuesByStatus[individual.affected][individual.individualId]}
                onChange={handleChange(individual)}
              />
            </Table.Cell>
            {i === 0 ?
              <Table.Cell collapsing rowSpan={individuals.length}>
                <PedigreeImagePanel key="pedigree" family={family} />
              </Table.Cell> : <Table.Cell collapsing />
            }
          </Table.Row>,
      )}
      </Table.Body>
    </Table>
  )
}


const mapStateToProps = (state, ownProps) => ({
  familyGuid: formValueSelector(ownProps.meta.form)(state, 'familyGuid'),
  familiesByGuid: getFamiliesByGuid(state),
  individualsByGuid: getIndividualsByGuid(state),
})

CustomInheritanceFilter.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
  familyGuid: PropTypes.string,
  familiesByGuid: PropTypes.object,
  individualsByGuid: PropTypes.object,
}

export default connect(mapStateToProps)(CustomInheritanceFilter)
