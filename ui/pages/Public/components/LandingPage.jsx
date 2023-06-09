import React from 'react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Segment, Header, Grid, Button, List } from 'semantic-ui-react'

import { getGoogleLoginEnabled } from 'redux/selectors'
import { VerticalSpacer } from 'shared/components/Spacers'
import { SeqrPaperLink } from 'shared/components/page/Footer'
import { LOCAL_LOGIN_URL, GOOGLE_LOGIN_URL } from 'shared/utils/constants'

const PageSegment = styled(Segment).attrs({ padded: 'very' })`
  padding-left: 20% !important;
  padding-right: 20% !important;
`

const Anchor = styled.a.attrs({ target: '_blank' })`
  font-weight: 400;
`

const LOGIN_BUTTON_PROPS = {
  label: 'Already a seqr user?', content: 'Sign In', primary: true, size: 'big', labelPosition: 'left',
}

export const SeqrAvailability = ({ hasFootnote }) => (
  <List ordered>
    <List.Item>
      Through the &nbsp;
      <Anchor href="https://anvilproject.org">AnVIL platform</Anchor>
      {hasFootnote && '*'}
      &nbsp; where requests can be placed for loading a joint called vcf into seqr
    </List.Item>
    <List.Item>
      As a collaborator providing samples for sequencing within the &nbsp;
      <Anchor href="https://cmg.broadinstitute.org">Broad Institute Center for Mendelian Genomics</Anchor>
      , part of the &nbsp;
      <Anchor href="https://gregorconsortium.org" target="blank">GREGoR consortium</Anchor>
    </List.Item>
    <List.Item>
      On GitHub as an &nbsp;
      <Anchor href="http://github.com/broadinstitute/seqr">open source project</Anchor>
      &nbsp;for download and local installation
    </List.Item>
  </List>
)

SeqrAvailability.propTypes = {
  hasFootnote: PropTypes.bool,
}

const LandingPage = ({ googleLoginEnabled }) => (
  <Segment.Group>
    <PageSegment textAlign="center" size="massive" secondary>
      <Header size="huge" content={<i>seqr</i>} />
      <VerticalSpacer height={20} />
      An open source software platform for rare disease genomics
      <VerticalSpacer height={40} />
      {googleLoginEnabled ?
        <Button as="a" href={GOOGLE_LOGIN_URL} {...LOGIN_BUTTON_PROPS} /> :
        <Button as={Link} to={LOCAL_LOGIN_URL} {...LOGIN_BUTTON_PROPS} />}
    </PageSegment>
    <Segment padded>
      <Grid columns="equal">
        <Grid.Column width={3} />
        <Grid.Column>
          <img src="/static/images/landing_page_icon1.png" alt="Identify disease causing variants" width="100%" />
        </Grid.Column>
        <Grid.Column>
          <img src="/static/images/landing_page_icon3.png" alt="Integrate data sources" width="100%" />
        </Grid.Column>
        <Grid.Column>
          <img src="/static/images/landing_page_icon2.png" alt="Collaborate" width="100%" />
        </Grid.Column>
        <Grid.Column width={3} />
      </Grid>
    </Segment>
    <PageSegment textAlign="center" size="big" secondary>
      <Header size="medium">
        About &nbsp;
        <i>seqr</i>
      </Header>
      <VerticalSpacer height={10} />
      Next Generation Sequencing (NGS) is a powerful diagnostic and research tool for Mendelian disease, but without
      proper tools, this data can be inaccessible to researchers. We have developed seqr as an open source web interface
      to make research productive, accessible, and user-friendly while leveraging resources and infrastructure at the
      Broad Institute.
      <Header size="small">
        {/* eslint-disable-next-line react/jsx-one-expression-per-line */}
        View the <SeqrPaperLink content={<span><i>seqr</i> paper</span>} />
      </Header>
    </PageSegment>
    <PageSegment size="large">
      <Header textAlign="center" size="large">
        <i>seqr</i>
        &nbsp; is available through three methods:
      </Header>
      <VerticalSpacer height={10} />
      <SeqrAvailability />
    </PageSegment>
    <PageSegment secondary>
      <List bulleted>
        <List.Item>
          If you are interested in collaborating with our group, please &nbsp;
          <Anchor href="mailto:seqr@broadinstitute.org">contact us</Anchor>
        </List.Item>
        <List.Item>
          Please use the &nbsp;
          <Anchor href="http://github.com/broadinstitute/seqr/issues">github issues page</Anchor>
          &nbsp; to submit bug reports or feature requests
        </List.Item>
        <List.Item>
          Training videos for use of seqr are available on the &nbsp;
          <Anchor href="https://www.youtube.com/playlist?list=PLlMMtlgw6qNiY6mkBu111-lpmANKHdGKM">
            Broad YouTube channel
          </Anchor>
        </List.Item>
      </List>
    </PageSegment>
  </Segment.Group>
)

LandingPage.propTypes = {
  googleLoginEnabled: PropTypes.bool,
}

const mapStateToProps = state => ({
  googleLoginEnabled: getGoogleLoginEnabled(state),
})

export default connect(mapStateToProps)(LandingPage)
