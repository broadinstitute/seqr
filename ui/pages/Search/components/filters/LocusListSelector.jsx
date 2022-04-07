import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import { Dropdown } from 'shared/components/form/Inputs'
import { LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { getSearchedProjectsLocusListOptions } from '../../selectors'

class BaseLocusListDropdown extends React.Component {

  static propTypes = {
    locusList: PropTypes.object,
    projectLocusListOptions: PropTypes.arrayOf(PropTypes.object),
    onChange: PropTypes.func,
  }

  shouldComponentUpdate(nextProps) {
    const { locusList, projectLocusListOptions, onChange } = this.props
    return nextProps.projectLocusListOptions !== projectLocusListOptions ||
      nextProps.onChange !== onChange ||
      nextProps.locusList.locusListGuid !== locusList.locusListGuid ||
      (!!locusList.locusListGuid && nextProps.locusList.rawItems !== locusList.rawItems)
  }

  componentDidUpdate(prevProps) {
    const { locusList, onChange } = this.props

    if (prevProps.locusList.rawItems !== locusList.rawItems) {
      const { locusListGuid } = locusList
      let { rawItems } = locusList

      if (locusList.paLocusList) {
        const CONFIDENCE_COLORS = { 0: 'none', 1: 'red', 2: 'amber', 3: 'green', 4: 'green' }
        rawItems = locusList.items?.reduce((acc, item) => {
          const color = CONFIDENCE_COLORS[item.pagene?.confidenceLevel || 0]
          if (color in acc) {
            acc[color] = [acc[color], item.display].filter(val => val).join(', ')
          }

          return acc
        }, { green: '', amber: '', red: '', none: '' })
      }

      onChange({ locusListGuid, rawItems })
    }
  }

  onChange = (locusListGuid) => {
    const { onChange } = this.props
    onChange({ locusListGuid })
  }

  render() {
    const { locusList, projectLocusListOptions } = this.props
    const locusListGuid = locusList.locusListGuid || ''
    return (
      <div>
        <Dropdown
          inline
          selection
          label="Gene List"
          value={locusListGuid}
          onChange={this.onChange}
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

const LocusListSelector = React.memo(({ value, ...props }) => (
  <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
    <LocusListDropdown {...props} />
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
