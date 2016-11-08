import React from 'react';
import { Provider } from 'react-redux'

import BaseLayout from '../../../components/BaseLayout'
import BreadCrumbs from '../../../components/BreadCrumbs';

import InheritanceModeFilters from './InheritanceModeFilters'
import SearchButtonPanel from './SearchButtonPanel'


const Root = ({store}) => {
    return <Provider store={store}>
        <BaseLayout>
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
        </BaseLayout>
    </Provider>
}

export default Root;