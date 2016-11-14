import React from 'react';
import ReactDOM from 'react-dom';

import InitialSettingsProvider from '../../shared/components/InitialSettingsProvider'
import BaseLayout from '../../shared/components/BaseLayout'
import PageHeader from './components/PageHeader'
import CaseReviewTable from './components/CaseReviewTable'


class CaseReview extends React.Component
{
    constructor(props) {
        super(props)

        this.defaultSettings = {
            user: {},
            project: {},
            families_by_id: {},
            individuals_by_id: {},
            family_id_to_indiv_ids: {},
        }
    }

    render() {
        const currentSettings = {
            ...this.defaultSettings,
            ...this.props.initialSettings,
        }

        console.log("currentSettings", currentSettings)
        return <BaseLayout {...currentSettings}>
            <PageHeader {...currentSettings} />
            <CaseReviewTable {...currentSettings} />
        </BaseLayout>
    }
}


ReactDOM.render(
    <InitialSettingsProvider>
        <CaseReview />
    </InitialSettingsProvider>,
    document.getElementById('reactjs-root')
)







/*
const storedReducer = (state = {
    'user': {},
    'project': {},
    'family_id_to_indiv_ids': {},
    'families_by_id': {},
    'individuals_by_id': {},
}, action) => {
    return state;
}
*/