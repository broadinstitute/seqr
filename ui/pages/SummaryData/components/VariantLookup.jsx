import React from 'react'
import { Grid, Segment, Header } from 'semantic-ui-react'

import StateDataLoader from 'shared/components/StateDataLoader'
import FormWrapper from 'shared/components/form/FormWrapper'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { GENOME_VERSION_FIELD } from 'shared/utils/constants'

const FIELDS = [
  {
    name: 'variantId',
    label: 'Variant ID',
    inline: true,
    required: true,
    component: BaseSemanticInput,
    inputType: 'Input',
  },
  { required: true, ...GENOME_VERSION_FIELD },
]

const VariantDisplay = ({ variant }) => JSON.stringify(variant) || 'none'

class VariantLookup extends React.PureComponent {

  state = {
    url: null,
  }

  onSubmit = ({ variantId, genomeVersion }) => (
    new Promise(resolve => this.setState({ url: `/api/variant/${genomeVersion}/${variantId}` }, resolve))
  )

  parseResponse = variant => ({ variant })

  render() {
    const { url } = this.state
    return (
      <Grid>
        <Grid.Row>
          <Grid.Column width={5} />
          <Grid.Column width={6}>
            <Segment padded>
              <Header dividing size="medium" content="Lookup Variant" />
              <FormWrapper noModal fields={FIELDS} onSubmit={this.onSubmit} />
            </Segment>
          </Grid.Column>
          <Grid.Column width={5} />
        </Grid.Row>
        <Grid.Row>
          <StateDataLoader
            url={url}
            parseResponse={this.parseResponse}
            childComponent={VariantDisplay}
          />
        </Grid.Row>
      </Grid>
    )
  }

}

export default VariantLookup
