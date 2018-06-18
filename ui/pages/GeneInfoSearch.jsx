import React from 'react'
import styled from 'styled-components'
import { Grid, Segment, Header } from 'semantic-ui-react'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import { VerticalSpacer } from 'shared/components/Spacers'

const ContentGrid = styled(Grid)`
  padding-top: 70px !important;
`

const SEARCH_CATEGORIES = ['genes']

const GeneInfoSearch = () =>
  <ContentGrid>
    <Grid.Row>
      <Grid.Column width={5} />
      <Grid.Column width={6}>
        <Segment padded>
          <Header dividing size="large" content="Gene Summary Information" />
          To access the summary page for a gene start typing the gene symbol in the form below and select the appropriate gene.
          <VerticalSpacer height={15} />
          <b><i>Gene Name: </i></b> Enter the gene name to search for variants.
          <VerticalSpacer height={15} />
          <AwesomeBar categories={SEARCH_CATEGORIES} />
        </Segment>
      </Grid.Column>
      <Grid.Column width={5} />
    </Grid.Row>
  </ContentGrid>

export default GeneInfoSearch
