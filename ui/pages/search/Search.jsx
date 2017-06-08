import React from 'react';
import PropTypes from 'prop-types'

import ReactDOM from 'react-dom';

import Root from 'shared/components/Root'
import BreadCrumbs from 'shared/components/BreadCrumbs';

import rootReducer, {getSearchParams} from './reducers/rootReducer'



import { configureStore } from 'shared/utils/configureStore'
import InheritanceModeFilters from './components/InheritanceModeFilters'
import SearchButtonPanel from './components/SearchButtonPanel'

const store = configureStore("Search", rootReducer,
    (state) => ({searchParams: getSearchParams(state)})
)

ReactDOM.render(
    <Root store={store} >
        <div className="ui grid">
            <div className="row" style={{padding:"0px"}}>
                <div className="sixteen wide column">
                    <BreadCrumbs breadcrumbs={["Search"]} />
                </div>
            </div>
            <div className="row">
                <div className="six wide column"><InheritanceModeFilters /></div>
                <div className="six wide column"><SearchButtonPanel /></div>
            </div>
        </div>
    </Root>,
    document.getElementById('reactjs-root')
)


/*

 import React from 'react';

 // regular 2-state checkbox
 let Checkbox = ({initialState, onClick, ...props}) => {
 return <input type="checkbox" onClick = { onClick } checked= { initialState == 1 ? "checked" : null } {...props} />
 }

 export default Checkbox;

 */