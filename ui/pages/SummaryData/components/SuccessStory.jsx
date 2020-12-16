import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'
import {
  FAMILY_SUCCESS_STORY_TYPE_OPTIONS,
  FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP,
  successStoryTypeDisplay,
} from '../../../shared/utils/constants'
import { SUCCESS_STORY_COLUMNS } from '../constants'
import { loadSuccessStory } from '../reducers'
import { getSuccessStoryLoading, getSuccessStoryLoadingError, getSuccessStoryRows } from '../selectors'
import TagFieldView from '../../../shared/components/panel/view-fields/TagFieldView'

const getDownloadFilename = successStoryTypes => `success_story_${successStoryTypes}`

// eslint-disable-next-line camelcase
const getFamilyFilterVal = ({ success_story }) => `${success_story}`

const LOADING_PROPS = { inline: true }

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const formatInitialValue = (match) => {
  const query = match.params.successStoryTypes
  let queryToArr = []
  if (query === 'all') {
    queryToArr = Object.keys(FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP)
  }
  else if (query) {
    queryToArr = query.split(',')
  }
  return { successStoryTypes: queryToArr }
}

const SuccessStory = React.memo(({ match, data, loading, loadingError, load, history }) =>
  <DataLoader contentId={match.params.successStoryTypes} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Types:" />
    <TagFieldView
      isEditable
      editLabel="choose success story types"
      field="successStoryTypes"
      idField="row_id"
      initialValues={formatInitialValue(match)}
      tagOptions={FAMILY_SUCCESS_STORY_TYPE_OPTIONS}
      onSubmit={value => history.push(`/summary_data/success_story/${value.successStoryTypes}`)}
      showIconOnly
      simplifiedValue
      fieldDisplay={value => value.map(tag =>
        <span>
          {successStoryTypeDisplay(tag)}
          <HorizontalSpacer width={4} />
        </span>)}
    />
    or <NavLink to="/summary_data/success_story/all" activeStyle={ACTIVE_LINK_STYLE}>view all success stories</NavLink>
    <VerticalSpacer height={15} />
    <DataTable
      downloadFileName={getDownloadFilename(match.params.successStoryTypes, data)}
      idField="row_id"
      defaultSortColumn="family_id"
      emptyContent={loadingError || (match.params.successStoryTypes ? '0 cases found' : 'Select success story types to view data')}
      loading={loading}
      data={data}
      columns={SUCCESS_STORY_COLUMNS}
      loadingProps={LOADING_PROPS}
      getRowFilterVal={getFamilyFilterVal}
    />
  </DataLoader>,
)

SuccessStory.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
  history: PropTypes.object,
}

const mapStateToProps = state => ({
  data: getSuccessStoryRows(state),
  loading: getSuccessStoryLoading(state),
  loadingError: getSuccessStoryLoadingError(state),
})

const mapDispatchToProps = {
  load: loadSuccessStory,
}

export default connect(mapStateToProps, mapDispatchToProps)(SuccessStory)
