import React from 'react'
import PropTypes from 'prop-types'

import { Feed, Header } from 'semantic-ui-react'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import StateDataLoader from 'shared/components/StateDataLoader'

const getDateFromDateStr = dateStr => (
  new Date(dateStr).toLocaleDateString(
    'en-us', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' },
  ))

const FeatureUpdatesFeed = ({ entries }) => (
  <div>
    <Header key="header" dividing size="huge">
      Feature Updates
      <Header.Subheader>
        This page serves as an announcement hub for new seqr functionality, sourced from this
        &nbsp;
        <a href="https://github.com/broadinstitute/seqr/discussions/categories/feature-updates">GitHub Discussion</a>
        .
      </Header.Subheader>
    </Header>
    <Feed key="feed" size="large">
      {entries.map(entry => (
        <Feed.Event key={entry.link}>
          <Feed.Content>
            <Feed.Summary>
              <a href={entry.link}>{entry.title}</a>
              &nbsp;by&nbsp;
              <a href={entry.author_link}>{entry.author}</a>
              <Feed.Date>
                <div>{getDateFromDateStr(entry.published_datestr)}</div>
              </Feed.Date>
            </Feed.Summary>
            <Feed.Extra>
              <TextFieldView
                field="markdown"
                isEditable={false}
                initialValues={entry}
              />
            </Feed.Extra>
          </Feed.Content>
        </Feed.Event>
      ))}
    </Feed>
  </div>
)

FeatureUpdatesFeed.propTypes = {
  entries: PropTypes.arrayOf(PropTypes.object),
}

const URL = '/api/feature_updates'

const parseResponse = responseJson => (
  { entries: responseJson.entries }
)

const FeatureUpdates = () => (
  <StateDataLoader
    url={URL}
    childComponent={FeatureUpdatesFeed}
    parseResponse={parseResponse}
    errorHeader="Unable to fetch."
  />
)

export default FeatureUpdates
