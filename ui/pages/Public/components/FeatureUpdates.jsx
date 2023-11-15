import React, { useEffect, useState } from 'react'
import { Feed, Header } from 'semantic-ui-react'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const FeatureUpdates = () => {
  const [feedEntries, setFeedEntries] = useState([])

  useEffect(() => {
    new HttpRequestHelper('/api/feature_updates',
      (responseJson) => {
        setFeedEntries(responseJson.entries)
      }).get()
  }, [])

  const createMarkdownObject = markdown => ({ markdown })

  const getDateFromDateStr = dateStr => (
    new Date(dateStr).toLocaleDateString(
      'en-us', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' },
    ))

  return (
    <div>
      <Header dividing size="huge">
        Feature Updates
        <Header.Subheader>
          This page serves as an announcement hub for new seqr functionality, sourced from this
          {' '}
          <a href="https://github.com/broadinstitute/seqr/discussions/categories/feature-updates">GitHub Discussion</a>
          .
        </Header.Subheader>
      </Header>
      <Feed size="large">
        {feedEntries.map(entry => (
          <Feed.Event key={entry.link}>
            <Feed.Content>
              <Feed.Summary>
                <a href={entry.link}>{entry.title}</a>
                {' '}
                by
                {' '}
                <a href={entry.author_link}>{entry.author}</a>
                <Feed.Date>
                  <div>{getDateFromDateStr(entry.published_datestr)}</div>
                </Feed.Date>
              </Feed.Summary>
              <Feed.Extra>
                <TextFieldView
                  field="markdown"
                  isEditable={false}
                  initialValues={createMarkdownObject(entry.markdown)}
                />
              </Feed.Extra>
            </Feed.Content>
          </Feed.Event>
        ))}
      </Feed>
    </div>
  )
}

export default FeatureUpdates
