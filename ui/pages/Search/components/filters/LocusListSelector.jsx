import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
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
        const grouped = locusList.items?.reduce((acc, item) => {
          const confidence = item.pagene?.confidenceLevel || 0
          const group = acc[confidence] || []
          group.push(item.display)
          acc[confidence] = group
          return acc
        }, {})
        if (grouped) {
          rawItems = {
            green: grouped['3']?.concat(grouped['4'])?.join(', ') || '',
            amber: grouped['2']?.join(', ') || '',
            red: grouped['1']?.join(', ') || '',
          }
        } else {
          rawItems = {
            green: '',
            amber: '',
            red: '',
          }
        }
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
    return (
      <div>
        <Dropdown
          inline
          selection
          label="Gene List"
          value={locusList.locusListGuid}
          onChange={this.onChange}
          options={projectLocusListOptions}
        />
      </div>
    )
  }

}

const mapStateToProps = state => ({
  projectLocusListOptions: getSearchedProjectsLocusListOptions(state),
})

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const LocusListSelector = React.memo(({ value, ...props }) => (
  <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
    <LocusListDropdown {...props} />
  </LocusListItemsLoader>
))

LocusListSelector.propTypes = {
  value: PropTypes.object,
}

export default LocusListSelector
