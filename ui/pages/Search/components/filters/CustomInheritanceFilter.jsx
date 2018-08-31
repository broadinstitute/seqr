import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { formValueSelector } from 'redux-form'
import { Form, Table } from 'semantic-ui-react'

import { getFamiliesByGuid, getIndividualsByGuid } from 'redux/selectors'
import { Select } from 'shared/components/form/Inputs'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { NUM_ALT_OPTIONS } from '../../constants'


const NUM_ALT_SELECT_PROPS = {
  control: Select,
  options: NUM_ALT_OPTIONS,
}

const CustomInheritanceFilter = ({ value, onChange, familyGuid, familiesByGuid, individualsByGuid }) => {
  const family = familiesByGuid[familyGuid]
  const individuals = family.individualGuids.map(individualGuid => individualsByGuid[individualGuid])

  const individualValues = value.individuals || individuals.reduce((acc, individual) => ({
    ...acc,
    [individual.individualId]: individual.affected === 'A' ? value.affected : (value.unaffected || value.otherUnaffected),
  }), {})
  if (!value.individuals && (value.mother || value.father)) {
    // Handle default values for parents of affected individuals
    individuals.forEach((individual) => {
      if (individual.affected === 'A') {
        individualValues[individual.maternalId] = value.mother
        individualValues[individual.paternalId] = value.father
      }
    })
  }

  const handleChange = individual => (val) => {
    const acForStatus = individuals.filter(
      ind => ind.individualId !== individual.individualId && individual.affected === ind.affected,
    ).reduce(
      (ac, ind) => (individualValues[ind.individualId] !== ac ? null : ac), val,
    )
    onChange({
      ...value,
      [individual.affected === 'A' ? 'affected' : 'unaffected']: acForStatus,
      individuals: { ...individualValues, [individual.individualId]: val },
    })
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
                value={individualValues[individual.individualId]}
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
