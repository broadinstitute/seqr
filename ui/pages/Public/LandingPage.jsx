import React from 'react'
import { Link } from 'react-router-dom'
import { Segment, Header, Grid, Button, List } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'

export default () =>
  <Segment.Group>
    <Segment textAlign="center" size="massive" padded="very" secondary>
      <Header size="huge" content={<i>seqr</i>} />
      <VerticalSpacer height={20} />
      An open source software platform for rare disease genomics
      <VerticalSpacer height={40} />
      <Button as={Link} to="/login" label="Already a seqr user?" content="Sign In" primary size="big" labelPosition="left" />
    </Segment>
    <Segment padded>
      <Grid columns="equal">
        <Grid.Column width={3} />
        <Grid.Column>
          <img src="/media/images/landing_page_icon1.png" alt="Identify disease causing variants" width="100%" />
        </Grid.Column>
        <Grid.Column>
          <img src="/media/images/landing_page_icon3.png" alt="Integrate data sources" width="100%" />
        </Grid.Column>
        <Grid.Column>
          <img src="/media/images/landing_page_icon2.png" alt="Collaborate" width="100%" />
        </Grid.Column>
        <Grid.Column width={3} />
      </Grid>
    </Segment>
    <Segment textAlign="center" size="big" secondary padded="very">
      <Header size="large" content={<span>About <i>seqr</i></span>} />
      <VerticalSpacer height={20} />
      Next Generation Sequencing (NGS) is a powerful diagnostic and research tool for Mendelian disease, but without
      proper tools, this data can be inaccessible to researchers. We are developing seqr as an open source web interface
      to make research productive, accessible, and user-friendly while leveraging resources and infrastructure at the
      Broad Institute.
    </Segment>
    <Segment size="large" padded="very">
      <Header
        textAlign="center"
        size="medium"
        content={
          <span>
            Currently, <i>seqr</i> is in closed beta-testing mode and is only used by our group and collaborators
          </span>}
      />
      <Grid>
        <Grid.Column width={3} />
        <Grid.Column width={10}>
          <List bulleted>
            <List.Item>
              If you are interested in collaborating with our group, please &nbsp;
              <a href="mailto:seqr@broadinstitute.org"><b>contact us</b></a>
            </List.Item>
            <List.Item>
              To get updates about seqr, &nbsp;
              <a target="_blank" href="http://groups.google.com/a/broadinstitute.org/forum/#!forum/seqr-updates/join">
                <b>join our mailing list</b>
              </a>
            </List.Item>
            <List.Item>
              The <a target="_blank" href="http://github.com/broadinstitute/seqr"><b>source code</b></a> is available on
              github. Please use the &nbsp;
              <a target="_blank" href="http://github.com/broadinstitute/seqr/issues"><b>github issues page</b></a> to
              submit bug reports or feature requests
            </List.Item>
          </List>
        </Grid.Column>
        <Grid.Column width={3} />
      </Grid>
    </Segment>
  </Segment.Group>
