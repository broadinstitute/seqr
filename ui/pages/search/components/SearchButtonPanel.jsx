import React from 'react'
import { connect } from 'react-redux'
import { startSearch, cancelSearch } from '../actions/searchStatus'
import { getSearchParams } from '../reducers/rootReducer'
import { getSearchInProgressId, getSearchErrorMessage } from '../reducers/searchStatus'

// define presentational component
const SearchButton = ({searchInProgress, startSearch, searchParams}) =>
    <input type="button" value="Search" onClick={ () => startSearch(searchParams) } disabled={ searchInProgress } />


const LoadingMessage = ({searchInProgress, cancelSearch}) =>
    <div style={{ visibility: searchInProgress ? "visible" : "hidden"}} >Loading ...
        <a onClick={ () => cancelSearch() } style={{ visibility: searchInProgress ? "visible" : "hidden" }} >Cancel Search</a><br/>
    </div>


const ErrorMessage = ({errorMessage}) =>
    <div style={{ visibility: errorMessage ? "visible" : "hidden"}} >{errorMessage}</div>



// wrap presentational components in a container
const mapStateToProps = (state) => ({
    searchParams: getSearchParams(state),
    searchInProgress: getSearchInProgressId(state),
    errorMessage: getSearchErrorMessage(state)
});

const mapDispatchToProps = {startSearch, cancelSearch}


let SearchButtonPanel = (props) => <div>
    <SearchButton {...props}/><br/>
    {
        props.searchInProgress ?
            <LoadingMessage {...props} /> :
            <ErrorMessage {...props} />
    }
    <br/>
</div>



SearchButtonPanel = connect(mapStateToProps, mapDispatchToProps)(SearchButtonPanel)

export default SearchButtonPanel
