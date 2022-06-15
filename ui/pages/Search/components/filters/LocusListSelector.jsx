/* eslint-disable react-perf/jsx-no-new-array-as-prop */
import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import { Form } from 'semantic-ui-react'
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

  // selectedMOIs = []

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

    console.log('running Component Did Update')
    console.log(this.props)
    console.log(prevProps)

    if (prevProps.locusList.rawItems !== locusList.rawItems || prevProps.selectedMOIs !== selectedMOIs) {
      const { locusListGuid } = locusList

      if (locusList.paLocusList) {
        console.log('hey, I guess you picked a PanelApp list')
        console.log('locusList', locusList)
        console.log('the rest of the props', this.props)
        console.log('selectedMOIs are:', selectedMOIs)
        console.log('prevProps.selectedMOIs', prevProps.selectedMOIs)

        const panelAppItems = locusList.items?.filter((item) => {
          let result = true
          if (prevProps.selectedMOIs) {
            const initials = moiToMoiInitials(item.pagene.modeOfInheritance)
            console.log(prevProps.selectedMOIs)
            console.log('initials: ', initials)
            result = prevProps.selectedMOIs.filter(moi => initials.includes(moi)).length
          }
          return result
        }).reduce((acc, item) => {
          console.log('item', item)

          const color = PANEL_APP_CONFIDENCE_LEVELS[item.pagene?.confidenceLevel] || PANEL_APP_CONFIDENCE_LEVELS[0]
          return { ...acc, [color]: [acc[color], item.display].filter(val => val).join(', ') }
        }, {})
        console.log('about to run onChange', locusListGuid)
        console.log('panelAppItems', panelAppItems)
        console.log(this.props)

        onChange({ locusListGuid, panelAppItems })
      } else {
        const { rawItems } = locusList
        onChange({ locusListGuid, rawItems })
      }
    }
  }

  // ignore all other properties on wrapperObject, except locusListGuid
  handleDropdown = (locusListGuid) => {
    console.log('this gets called first')
    console.log('running onChange in LocusListSelector', this.props)
    console.log('locusListGuid', locusListGuid)
    const { onChange } = this.props

    console.log('search.locus stuff:', this.props)
    onChange({ locusListGuid })
  }

  handleMOIselect = (selectedMOIs) => {
    console.log('handleMOIselect', selectedMOIs)
    console.log(this.props)
    // const { onChange } = this.props
    // onChange({ modesOfInheritance: payload })
    // this.selectedMOIs = selectedMOIs
    const { locusList, onChange } = this.props
    onChange({ locusListGuid: locusList.locusListGuid, selectedMOIs })
  }

  render() {
    const { locusList, projectLocusListOptions, selectedMOIs } = this.props
    const locusListGuid = locusList.locusListGuid || ''
    // const selectedMOIs = this.selectedMOIs || []

    // const selectedMOIs = this.props.selectedMOIs || 'g'.split()
    // console.log('modesOfInheritance', modesOfInheritance)
    // console.log('render props:', this.props)

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
          // {...this.props}
            // width={15}
            label="Modes of Inheritance"
            value={selectedMOIs}
            onChange={this.handleMOIselect}
            placeholder="Showing All MOIs"
          // disabled={false}
            options={options}
            color="violet"
            allowAdditions
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
      <Form.Group inline widths="equal">
        <Dropdown
          inline
          selection
          search
          label="Gene List"
          value={locusListGuid}
          onChange={this.handleDropdown}
          options={projectLocusListOptions}
        />
      </Form.Group>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  projectLocusListOptions: getSearchedProjectsLocusListOptions(state, ownProps),
})

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const SUBSCRIPTION = { values: true }

// When onChange is called, this is the function that is called.
// Values are passed here.
const LocusListSelector = React.memo(({ value, ...props }) => {
  console.log('selecting stuff')
  console.log(value)
  console.log(props)
  return (
    <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
      <LocusListDropdown selectedMOIs={value.selectedMOIs} {...props} />
    </LocusListItemsLoader>
  )
})

LocusListSelector.propTypes = {
  value: PropTypes.object,
}

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => <LocusListSelector {...props} projectFamilies={values.projectFamilies} />}
  </FormSpy>
)
