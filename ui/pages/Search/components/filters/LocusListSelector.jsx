import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import { Form } from 'semantic-ui-react'
import styled from 'styled-components'

import { getLocusListsIsLoading } from 'redux/selectors'
import { Dropdown } from 'shared/components/form/Inputs'
import { formatPanelAppItems } from 'shared/utils/panelAppUtils'
import { LocusListsLoader, LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { getLocusListOptions } from '../../selectors'

const DropdownInput = styled(Dropdown).attrs({
  inline: true,
  selection: true,
  search: true,
  includeCategories: true,
  clearable: true,
  fluid: true,
  labeled: true,
  width: 16,
})`
  label {
    white-space: nowrap;
  }
`

class BaseLocusListDropdown extends React.Component {

  static propTypes = {
    locusList: PropTypes.object,
    locusListOptions: PropTypes.arrayOf(PropTypes.object),
    loading: PropTypes.bool,
    onChange: PropTypes.func,
  }

  shouldComponentUpdate(nextProps) {
    const { locusList, locusListOptions, onChange, loading } = this.props
    return nextProps.locusListOptions !== locusListOptions ||
      nextProps.onChange !== onChange ||
      nextProps.loading !== loading ||
      nextProps.locusList.locusListGuid !== locusList.locusListGuid ||
      (!!locusList.locusListGuid && nextProps.locusList.rawItems !== locusList.rawItems)
  }

  componentDidUpdate(prevProps) {
    const { locusList, onChange } = this.props

    if (prevProps.locusList.rawItems !== locusList.rawItems) {
      const { locusListGuid } = locusList

      if (locusList.paLocusList) {
        const panelAppItems = formatPanelAppItems(locusList.items)
        onChange({ locusListGuid, panelAppItems })
      } else {
        const { rawItems } = locusList
        onChange({ locusListGuid, rawItems })
      }
    }
  }

  onChange = (locusListGuid) => {
    const { onChange } = this.props
    onChange({ locusListGuid })
  }

  render() {
    const { locusList, locusListOptions, loading } = this.props
    const locusListGuid = locusList.locusListGuid || ''
    return (
      <Form.Group inline>
        <DropdownInput
          label="Gene List"
          value={locusListGuid}
          loading={loading}
          disabled={loading}
          onChange={this.onChange}
          options={locusListOptions}
        />
      </Form.Group>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  locusListOptions: getLocusListOptions(state, ownProps),
  loading: getLocusListsIsLoading(state),
})

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const SUBSCRIPTION = { values: true }

const LocusListSelector = React.memo(({ value, ...props }) => (
  <LocusListsLoader allProjectLists hideLoading>
    <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
      <LocusListDropdown {...props} />
    </LocusListItemsLoader>
  </LocusListsLoader>
))

LocusListSelector.propTypes = {
  value: PropTypes.object,
}

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => <LocusListSelector {...props} projectFamilies={values.projectFamilies} />}
  </FormSpy>
)
