import React from 'react'
import { Segment, Grid } from 'semantic-ui-react'

export default () =>
  <div>
    <Segment textAlign="center" size="huge" padded="very" basic>
      <Grid>
        <Grid.Row>
          <Grid.Column width={5} />
          <Grid.Column width={6}>
            <img
              alt="matchbox"
              src="https://raw.githubusercontent.com/macarthur-lab/matchbox/master/aux-files/matchbox-logo.png"
            />
          </Grid.Column>
          <Grid.Column width={5} />
        </Grid.Row>
        <Grid.Row>
          <Grid.Column>
            <p>
              Welcome to <i>matchbox</i>! The bridge to the &nbsp;
              <a target="_blank" href="http://www.matchmakerexchange.org/">Matchmaker Exchange</a>
              at the <a target="_blank" href="https://cmg.broadinstitute.org/">Center for Mendelian Genomics</a> at the
              &nbsp; <a target="_blank" href="https://www.broadinstitute.org/">Broad Institute of MIT and Harvard</a>
              (Broad CMG). To use <i>matchbox</i>, you must be a collaborator and have your data deposited in the
              &nbsp; <a target="_blank" href="https://seqr.broadinstitute.org"><i>seqr</i></a> platform
            </p>
          </Grid.Column>
        </Grid.Row>
        <Grid.Row>
          <Grid.Column>
            Please contact us at <a href="mailto:matchmaker@broadinstitute.org">matchmaker@broad</a>.
          </Grid.Column>
        </Grid.Row>
      </Grid>
    </Segment>
    <Grid textAlign="center">
      <Grid.Row>
        <Grid.Column width={2} />
        <Grid.Column width={12}>
          Our software is freely available, open source and can be found &nbsp;
          <a target="_blank" href="https://github.com/macarthur-lab/matchbox">here.</a> We encourage all new centers
          interested in joining the <a target="_blank" href="http://www.matchmakerexchange.org/">Matchmaker Exchange</a>
          to please use this software and contribute their effort towards making this a community resource.
        </Grid.Column>
        <Grid.Column width={2} />
      </Grid.Row>
      <Grid.Row>
        <Grid.Column>
          <i>matchbox</i> is currently maintained by the &nbsp;
          <a target="_blank" href="https://cmg.broadinstitute.org/">Broad CMG</a>, and the &nbsp;
          <a target="_blank" href="https://monarchinitiative.org/">Monarch Initiative</a>.
          <br />
          Logo development by Lauren Solomon and Susanna M. Hamilton, Broad Communications.
        </Grid.Column>
      </Grid.Row>
    </Grid>
  </div>
