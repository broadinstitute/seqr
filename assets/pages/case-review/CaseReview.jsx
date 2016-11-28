import React from 'react'
import ReactDOM from 'react-dom'

import InitialSettingsProvider from '../../shared/components/InitialSettingsProvider'
import BaseLayout from '../../shared/components/BaseLayout'
import PageHeader from './components/PageHeader'
import CaseReviewTable from './components/CaseReviewTable'


class CaseReview extends React.Component
{

  static propTypes = {
    initialSettings: React.PropTypes.object,
  }


  render = () =>
    <BaseLayout {...this.props.initialSettings}>
      <span>
        <PageHeader {...this.props.initialSettings} />
        <CaseReviewTable {...this.props.initialSettings} />
      </span>
    </BaseLayout>
}


ReactDOM.render(
  <InitialSettingsProvider>
    <CaseReview />
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)
