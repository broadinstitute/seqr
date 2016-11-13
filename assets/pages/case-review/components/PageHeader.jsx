import React from 'react'
import { connect } from 'react-redux'

import BreadCrumbs from '../../../shared/components/BreadCrumbs'
import { getProject } from '../reducers/rootReducer'

let PageHeader = ({
    project
}) => <div>
    <BreadCrumbs breadcrumbs={[
        <span>{'Project: '}<a href={"/project/"+project.project_id}>{project.project_id}</a></span>,
        "Case Review"
    ]} /> <br/>

</div>


import { bindActionCreators } from 'redux'

//import { startSearch, cancelSearch } from '../actions/searchStatus'

//import { getSearchInProgressId, getSearchErrorMessage } from '../reducers/searchStatus'

// define presentational component
//const SearchButton = ({searchInProgress, startSearch, searchParams}) =>
//    <input type="button" value="Search" onClick={ () => startSearch(searchParams) } disabled={ searchInProgress } />



// wrap presentational components in a container
const mapStateToProps = (state) => ({
    project: getProject(state),
 });

PageHeader = connect(mapStateToProps)(PageHeader);

export default PageHeader
