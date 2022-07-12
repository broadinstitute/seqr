import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import { Multiselect } from 'shared/components/form/Inputs'
import { semanticShouldUpdate } from 'shared/utils/semanticUtils'
import { LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { moiToMoiInitials } from 'shared/utils/panelAppUtils'
import { PANEL_APP_MOI_OPTIONS } from 'shared/utils/constants'

import { getSearchedProjectsLocusListOptions } from '../../selectors'

class BasePaMoiDropdown extends React.Component {

  static propTypes = {
    locus: PropTypes.object,
    selectedMOIs: PropTypes.arrayOf(PropTypes.string),
    onChange: PropTypes.func,
  }

  shouldComponentUpdate(nextProps, nextState) {
    return semanticShouldUpdate(this, nextProps, nextState)
  }

  // Add logic to componentDidUpdate
  componentDidUpdate(prevProps) {
    console.log('running componentDidUpdate', prevProps)
    console.log(this.props)
    const { selectedMOIs, locus, onChange } = this.props
    const { locusList } = locus
    // const { panelAppItems } = locusList

    // const panelAppItems = locusList.items?.filter((item) => {
    //   let result = true
    //   if (selectedMOIs && selectedMOIs.length !== 0) {
    //     const initials = moiToMoiInitials(item.pagene?.modeOfInheritance)
    //     if (initials.length === 0) initials.push('other')
    //     result = selectedMOIs.filter(moi => initials.includes(moi)).length !== 0
    //   }
    //   return result
    // }).reduce((acc, item) => {
    console.log(selectedMOIs)
    console.log(locusList)

    const panelAppItems = {
      red: '',
      green: '',
      amber: '',
    }
    locusList.panelAppItems = panelAppItems

    if (prevProps.selectedMOIs !== selectedMOIs) {
      console.log("something's different, push an update")
      onChange({ selectedMOIs, panelAppItems })
      // this.handleMOIselect(selectedMOIs)
    } else {
      console.log('nothing changed. no update.')
    }
  }

  handleMOIselect = (selectedMOIs) => {
    const { onChange } = this.props
    onChange({ selectedMOIs })
  }

  moiOptions = () => {
    const { locus } = this.props
    const { locusList } = locus

    const initials = locusList.items?.reduce((acc, gene) => {
      moiToMoiInitials(gene.pagene?.modeOfInheritance).forEach((initial) => {
        acc[initial] = true
      })
      if (moiToMoiInitials(gene.pagene?.modeOfInheritance).length === 0) {
        acc.other = true
      }
      return acc
    }, {}) || {}

    return PANEL_APP_MOI_OPTIONS.map(moi => ({
      ...moi,
      disabled: !initials[moi.value],
    }))
  }

  render() {
    const { selectedMOIs } = this.props || []
    console.log('all values?', this.props)
    // selectedMOIs = selectedMOIs || []

    return (
      <Multiselect
        className="inline six wide field"
        label="Modes of Inheritance"
        value={selectedMOIs}
        onChange={this.handleMOIselect}
        placeholder="Showing all MOIs as listed in Panel App"
        options={this.moiOptions()}
        color="violet"
      />
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  projectLocusListOptions: getSearchedProjectsLocusListOptions(state, ownProps),
})

const PaMoiDropdown = connect(mapStateToProps)(BasePaMoiDropdown)

const PaMoiSelector = React.memo(({ value, ...props }) => (
  <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
    <PaMoiDropdown selectedMOIs={value.selectedMOIs} {...props} />
  </LocusListItemsLoader>
))

PaMoiSelector.propTypes = {
  value: PropTypes.object,
}

const SUBSCRIPTION = {
  values: true,
}

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => {
      console.log('values', values)
      return (
        <PaMoiSelector
          {...props}
          locus={values.search?.locus}
          projectFamilies={values.projectFamilies}
          inline
        />
      )
    }}
  </FormSpy>
)
