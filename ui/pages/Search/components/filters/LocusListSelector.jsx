import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import { Dropdown, Multiselect } from 'shared/components/form/Inputs'
import { LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { PANEL_APP_CONFIDENCE_LEVELS, PANEL_APP_MOI_OPTIONS } from 'shared/utils/constants'
import { moiToMoiInitials } from 'shared/utils/panelAppUtils'
import { getSearchedProjectsLocusListOptions } from '../../selectors'

class BaseLocusListDropdown extends React.Component {

  static propTypes = {
    locusList: PropTypes.object,
    projectLocusListOptions: PropTypes.arrayOf(PropTypes.object),
    onChange: PropTypes.func,
    selectedMOIs: PropTypes.arrayOf(PropTypes.string),
  }

  shouldComponentUpdate(nextProps) {
    const { locusList, selectedMOIs, projectLocusListOptions, onChange } = this.props

    return nextProps.projectLocusListOptions !== projectLocusListOptions ||
      nextProps.selectedMOIs !== selectedMOIs ||
      nextProps.onChange !== onChange ||
      nextProps.locusList.locusListGuid !== locusList.locusListGuid ||
      (!!locusList.locusListGuid && nextProps.locusList.rawItems !== locusList.rawItems)
  }

  componentDidUpdate(prevProps) {
    const { locusList, onChange, selectedMOIs } = this.props
    if (prevProps.locusList.rawItems !== locusList.rawItems || prevProps.selectedMOIs !== selectedMOIs) {
      const { locusListGuid } = locusList

      if (locusList.paLocusList) {
        const panelAppItems = locusList.items?.filter((item) => {
          let result = true
          if (selectedMOIs && selectedMOIs.length !== 0) {
            const initials = moiToMoiInitials(item.pagene.modeOfInheritance)
            result = selectedMOIs.filter(moi => initials.includes(moi)).length !== 0
          }
          return result
        }).reduce((acc, item) => {
          const color = PANEL_APP_CONFIDENCE_LEVELS[item.pagene?.confidenceLevel] || PANEL_APP_CONFIDENCE_LEVELS[0]
          return { ...acc, [color]: [acc[color], item.display].filter(val => val).join(', ') }
        }, {})
        onChange({ locusListGuid, panelAppItems, selectedMOIs })
      } else {
        const { rawItems } = locusList
        onChange({ locusListGuid, rawItems, selectedMOIs })
      }
    }
  }

  handleDropdown = (locusListGuid) => {
    const { onChange } = this.props
    onChange({ locusListGuid, selectedMOIs: [] })
  }

  handleMOIselect = (selectedMOIs) => {
    const { locusList, onChange } = this.props
    onChange({ locusListGuid: locusList.locusListGuid, selectedMOIs })
  }

  render() {
    const { locusList, projectLocusListOptions, selectedMOIs } = this.props
    const locusListGuid = locusList.locusListGuid || ''

    const GeneListDropdown = (
      <Dropdown
        inline
        selection
        search
        label="Gene List"
        value={locusListGuid}
        onChange={this.handleDropdown}
        options={projectLocusListOptions}
      />
    )

    const rightJustify = {
      justifyContent: 'right',
    }

    if (locusList.paLocusList) {
      return (
        <div className="inline fields" style={rightJustify}>
          <Multiselect
            className="wide eight"
            label="Modes of Inheritance"
            value={selectedMOIs}
            onChange={this.handleMOIselect}
            placeholder="Showing All MOIs"
            options={PANEL_APP_MOI_OPTIONS}
            color="violet"
          />
          { GeneListDropdown }
        </div>
      )
    }

    return (
      <div>
        { GeneListDropdown }
      </div>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  projectLocusListOptions: getSearchedProjectsLocusListOptions(state, ownProps),
})

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const SUBSCRIPTION = { values: true }

const LocusListSelector = React.memo(({ value, ...props }) => (
  <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
    <LocusListDropdown selectedMOIs={value.selectedMOIs} {...props} />
  </LocusListItemsLoader>
))

LocusListSelector.propTypes = {
  value: PropTypes.object,
}

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => <LocusListSelector {...props} projectFamilies={values.projectFamilies} />}
  </FormSpy>
)
