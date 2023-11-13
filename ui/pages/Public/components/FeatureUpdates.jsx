import React, { useEffect, useState } from 'react'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { Feed, Header } from 'semantic-ui-react'
import parse from 'html-react-parser'

const FeatureUpdates = () => {
  const [feedLink, setFeedLink] = useState([])
  const [feedEntries, setFeedEntries] = useState([])

  useEffect(() => {
    new HttpRequestHelper('/api/feature_updates',
      (responseJson) => {
        setFeedLink(responseJson.link)
        setFeedEntries(responseJson.entries)
      }).get()
  }, [])

  return (
    <div>
      <Header dividing size="huge">
        Feature Updates
        <Header.Subheader>
          Recent discussions in
          {' '}
          <a href={feedLink}>broadinstitute/seqr, category: feature-updates</a>
        </Header.Subheader>
      </Header>
      <Feed>
        {feedEntries.map(entry => (
          <Feed.Event key={entry.id}>
            <Feed.Content>
              <Feed.Summary>
                <a href={entry.link}>{entry.title}</a>
                {' '}
                posted by
                {' '}
                <a href={entry.href}>{entry.author}</a>
                <Feed.Date>
                  <div>{new Date(entry.published).toLocaleDateString('en-us', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}</div>
                </Feed.Date>
              </Feed.Summary>
              <Feed.Extra text>
                {/* TODO: parse is not xss-attack safe. however, html from entry.summary is sanitized by backend
                https://feedparser.readthedocs.io/en/latest/reference-entry-summary.html */}
                {parse(entry.summary)}
              </Feed.Extra>
            </Feed.Content>
          </Feed.Event>
        ))}
      </Feed>
    </div>
  )
}

export default FeatureUpdates
