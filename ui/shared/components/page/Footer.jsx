import React from 'react'
import { Grid } from 'semantic-ui-react'

const Footer = () => <Grid
  style={{
    backgroundColor: '#F3F3F3',
    borderStyle: 'solid',
    borderWidth: '1px 0px 0px 0px',
    borderColor: '#E2E2E2' }}
>
  <Grid.Column width={2} />
  <Grid.Column width={7}>
      For bug reports or feature requests please submit  &nbsp;
      <a href="https://github.com/macarthur-lab/seqr/issues">Github Issues</a>
  </Grid.Column>
  <Grid.Column width={5} style={{ textAlign: 'right' }}>
      If you have questions or feedback, &nbsp;
      <a
        href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;tf=1&amp;to=seqr@broadinstitute.org"
        rel="noopener noreferrer" target="_blank"
      >Contact Us</a>
  </Grid.Column>
  <Grid.Column width={2} />
</Grid>

export default Footer
