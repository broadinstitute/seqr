import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import SortableTable from 'shared/components/table/SortableTable'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'
import { SUCCESS_STORY_COLUMNS } from '../constants'
import { loadSuccessStory } from '../reducers'
import { getDiscoverySheetLoading, getDiscoverySheetLoadingError, getDiscoverySheetRows } from '../selectors'
// import TagFieldView from '../../../shared/components/panel/view-fields/TagFieldView'
// import {
//   FAMILY_SUCCESS_STORY_TYPE_OPTIONS,
//   FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP,
// } from '/shared/utils/constants'

const getDownloadFilename = projectGuid => `success_story_${projectGuid}`

// eslint-disable-next-line camelcase
const getFamilyFilterVal = ({ success_story }) => `${success_story}`

const LOADING_PROPS = { inline: true }

// const EMPTY_SELECTION = { test: ['O', 'D', 'T', 'C', 'A', 'N'] }

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const getResultHref = page => result => `/staff/${page}/${result.key}`

const DiscoverySheet = ({ match, data, loading, loadingError, load, filters }) =>
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref('success_story')}
    />
    {/*<TagFieldView*/}
    {/*  field="selectedSuccessStoryTypes"*/}
    {/*  idField="test"*/}
    {/*  initialValues={EMPTY_SELECTION}*/}
    {/*  tagOptions={FAMILY_SUCCESS_STORY_TYPE_OPTIONS}*/}
    {/*  onSubmit={values => load(match.params.projectGuid, values)} // TODO change this*/}
    {/*  showIconOnly*/}
    {/*  simplifiedValue*/}
    {/*  fieldDisplay={value => value.map(tag =>*/}
    {/*    <div>*/}
    {/*      <ColoredIcon name="stop" color={FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP[tag].color} />*/}
    {/*      {FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP[tag].name}*/}
    {/*    </div>)}*/}
    {/*/>*/}
    {/*or <NavLink to="/staff/discovery_sheet/all" activeStyle={ACTIVE_LINK_STYLE}>view all success stories</NavLink>*/}
    or <NavLink to="/staff/success_story/all" activeStyle={ACTIVE_LINK_STYLE}>view all success stories</NavLink>
    <HorizontalSpacer width={20} />
    {filters}
    <VerticalSpacer height={15} />
    <SortableTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={getDownloadFilename(match.params.projectGuid, data)}
      idField="row_id"
      defaultSortColumn="family_id"
      emptyContent={loadingError || (match.params.projectGuid ? '0 cases found' : 'Select a project to view data')}
      loading={loading}
      data={data}
      columns={SUCCESS_STORY_COLUMNS}
      loadingProps={LOADING_PROPS}
      getRowFilterVal={getFamilyFilterVal}
    />
  </DataLoader>

DiscoverySheet.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
  filters: PropTypes.node,
}

const mapStateToProps = state => ({
  data: getDiscoverySheetRows(state),
  loading: getDiscoverySheetLoading(state),
  loadingError: getDiscoverySheetLoadingError(state),
})

const mapDispatchToProps = {
  load: loadSuccessStory,
}

export default connect(mapStateToProps, mapDispatchToProps)(DiscoverySheet)
