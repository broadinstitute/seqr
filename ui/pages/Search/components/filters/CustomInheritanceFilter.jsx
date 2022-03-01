import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import { Table, Header, Popup, Loader } from 'semantic-ui-react'

import { loadFamilyDetails } from 'redux/rootReducer'
import { getFamiliesByGuid, getIndividualsByGuid, getFamilyDetailsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { Select } from 'shared/components/form/Inputs'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { AFFECTED, UNAFFECTED, AFFECTED_OPTIONS } from 'shared/utils/constants'
import { NUM_ALT_OPTIONS } from '../../constants'

const CUSTOM_FILTERS = [
  { filterField: 'affected', options: AFFECTED_OPTIONS },
  { filterField: 'genotype', options: NUM_ALT_OPTIONS, placeholder: 'Allele count' },
]

const CustomInheritanceFilterContent = React.memo(({ value, onChange, family, individualsByGuid }) => {
  const individuals = (family.individualGuids || []).map(individualGuid => individualsByGuid[individualGuid]).filter(
    individual => individual,
  )

  if (!family.individualGuids || family.individualGuids.length !== individuals.length) {
    return <Loader />
  }

  const parentGenotypes = {}
  if (value.father) {
    individuals.forEach((individual) => {
      if (individual.affected === AFFECTED) {
        parentGenotypes[individual.paternalId] = value.father
      }
    })
  }

  const individualFilters = individuals.reduce((acc, ind) => {
    const affected = (value.affected || {})[ind.individualGuid] || ind.affected
    let genotype = (value.genotype || {})[ind.individualGuid]
    if (!genotype) {
      if (affected === UNAFFECTED && parentGenotypes[ind.individualId]) {
        genotype = parentGenotypes[ind.individualId]
      } else {
        genotype = value[affected]
      }
    }
    return { ...acc, [ind.individualGuid]: { affected, genotype } }
  }, {})

  const handleChange = (individual, filterField) => (val) => {
    onChange({ ...value, [filterField]: { ...value[filterField], [individual.individualGuid]: val } })
  }

  return (
    <Table basic="very" compact>
      <Table.Body>
        {individuals.map((individual, i) => {
          const row = (
            <Table.Row key={individual.individualGuid}>
              <Table.Cell collapsing key={`${individual.individualGuid}-pedigree`}>
                <PedigreeIcon sex={individual.sex} affected={individual.affected} />
                &nbsp;
                {individual.displayName || individual.individualId}
                {individual.displayName && individual.displayName !== individual.individualId ? `(${individual.individualId})` : null}
              </Table.Cell>
              {CUSTOM_FILTERS.map(({ filterField, ...fieldProps }) => (
                <Table.Cell key={filterField}>
                  <Select
                    {...fieldProps}
                    disabled={!individual.sampleGuids.length}
                    value={individualFilters[individual.individualGuid][filterField]}
                    onChange={handleChange(individual, filterField)}
                  />
                </Table.Cell>
              ))}
              {i === 0 ? (
                <Table.Cell collapsing rowSpan={individuals.length}>
                  <PedigreeImagePanel key="pedigree" family={family} />
                </Table.Cell>

              ) : <Table.Cell collapsing />}
            </Table.Row>
          )
          return individual.sampleGuids.length ? row : (
            <Popup
              key={individual.individualGuid}
              trigger={row}
              content="Inheritance search is disabled for individuals with no loaded data"
            />
          )
        })}
      </Table.Body>
    </Table>
  )
})

CustomInheritanceFilterContent.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
  family: PropTypes.object,
  individualsByGuid: PropTypes.object,
}

const CustomInheritanceFilter = React.memo(({ load, loading, family, ...props }) => {
  if (!family) {
    return <Header disabled content="Custom inheritance search is disabled for multi-family searches" />
  }
  return (
    <DataLoader load={load} contentId={family.familyGuid} content={family && family.detailsLoaded} loading={loading}>
      <CustomInheritanceFilterContent family={family} {...props} />
    </DataLoader>
  )
})

const mapStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.familyGuid],
  individualsByGuid: getIndividualsByGuid(state),
  loading: !!getFamilyDetailsLoading(state)[ownProps.familyGuid],
})

const mapDispatchToProps = {
  load: loadFamilyDetails,
}

CustomInheritanceFilter.propTypes = {
  load: PropTypes.func,
  family: PropTypes.object,
  loading: PropTypes.bool,
}

const ConnectedCustomInheritanceFilter = connect(mapStateToProps, mapDispatchToProps)(CustomInheritanceFilter)

const SUBSCRIPTION = { values: true }

const getSingleFamlilyGuid = projectFamilies => (
  (projectFamilies && projectFamilies.length === 1 && (projectFamilies[0].familyGuids || []).length === 1) ?
    projectFamilies[0].familyGuids[0] : null
)

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <ConnectedCustomInheritanceFilter {...props} familyGuid={getSingleFamlilyGuid(values.projectFamilies)} />
    )}
  </FormSpy>
)
