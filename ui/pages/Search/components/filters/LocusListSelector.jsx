/* eslint-disable react-perf/jsx-no-new-array-as-prop */
import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import { Dropdown, Multiselect } from 'shared/components/form/Inputs'
import { LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { PANEL_APP_CONFIDENCE_LEVELS } from 'shared/utils/constants'
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
          if (prevProps.selectedMOIs) {
            const initials = moiToMoiInitials(item.pagene.modeOfInheritance)
            result = prevProps.selectedMOIs.filter(moi => initials.includes(moi)).length
          }
          return result
        }).reduce((acc, item) => {
          const color = PANEL_APP_CONFIDENCE_LEVELS[item.pagene?.confidenceLevel] || PANEL_APP_CONFIDENCE_LEVELS[0]
          return { ...acc, [color]: [acc[color], item.display].filter(val => val).join(', ') }
        }, {})
        onChange({ locusListGuid, panelAppItems })
      } else {
        const { rawItems } = locusList
        onChange({ locusListGuid, rawItems })
      }
    }
  }

  // ignore all other properties on wrapperObject, except locusListGuid
  handleDropdown = (locusListGuid) => {
    const { onChange } = this.props
    onChange({ locusListGuid })
  }

  handleMOIselect = (selectedMOIs) => {
    const { locusList, onChange } = this.props
    onChange({ locusListGuid: locusList.locusListGuid, selectedMOIs })
  }

  render() {
    const { locusList, projectLocusListOptions, selectedMOIs } = this.props
    const locusListGuid = locusList.locusListGuid || ''

    const options = [{
      text: 'Autosomal Dominant',
      value: 'AD',
    },
    {
      text: 'Autosomal Recessive',
      value: 'AR',
    },
    {
      text: 'X-Linked Dominant',
      value: 'XD',
    },
    {
      text: 'X-Linked Recessive',
      value: 'XR',
    },
    {
      text: 'Other Mode of Inheritance',
      value: 'other',
    }]

    if (projectLocusListOptions.find(option => option.value === locusListGuid)?.description === 'PanelApp') {
      return (
        <div>
          <Multiselect
            label="Modes of Inheritance"
            value={selectedMOIs}
            onChange={this.handleMOIselect}
            placeholder="Showing All MOIs"
            options={options}
            color="violet"
            // allowAdditions
          />
          <Dropdown
            inline
            selection
            search
            label="Gene List"
            value={locusListGuid}
            onChange={this.handleDropdown}
            options={projectLocusListOptions}
          />
        </div>
      )
    }

    return (
      <div>
        <Dropdown
          inline
          selection
          search
          label="Gene List"
          value={locusListGuid}
          onChange={this.handleDropdown}
          options={projectLocusListOptions}
        />
      </div>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  projectLocusListOptions: getSearchedProjectsLocusListOptions(state, ownProps),
})

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const SUBSCRIPTION = { values: true }

// When onChange is called, this selector will be called again to get the new value of the locusList
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
