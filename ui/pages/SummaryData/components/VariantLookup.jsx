import React from 'react'
import PropTypes from 'prop-types'
import { Grid, Segment, Header } from 'semantic-ui-react'

import StateDataLoader from 'shared/components/StateDataLoader'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { GENOME_VERSION_FIELD } from 'shared/utils/constants'

const FIELDS = [
  {
    name: 'variantId',
    label: 'Variant ID',
    inline: true,
    component: BaseSemanticInput,
    inputType: 'Input',
  },
  GENOME_VERSION_FIELD,
]

const VariantLookup = React.memo(({ queryForm, variant }) => (
  <Grid>
    <Grid.Row>
      <Grid.Column width={5} />
      <Grid.Column width={6}>
        <Segment padded>
          <Header dividing size="medium" content="Lookup Variant" />
          {queryForm}
        </Segment>
      </Grid.Column>
      <Grid.Column width={5} />
    </Grid.Row>
    <Grid.Row>
      {variant && JSON.stringify(variant)}
    </Grid.Row>
  </Grid>
))

VariantLookup.propTypes = {
  queryForm: PropTypes.node,
  variant: PropTypes.object,
}

const validateQueryLoad = ({ shouldSearch }) => shouldSearch

const parseResponse = variant => ({ variant })

export default () => (
  <StateDataLoader
    url="/api/variant_lookup"
    validateQueryLoad={validateQueryLoad}
    parseResponse={parseResponse}
    queryFields={FIELDS}
    childComponent={VariantLookup}
  />
)
