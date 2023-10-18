import React from 'react'
import PropTypes from 'prop-types'
import { Grid, Header } from 'semantic-ui-react'

import StateDataLoader from 'shared/components/StateDataLoader'
import FormWrapper from 'shared/components/form/FormWrapper'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { Variant } from 'shared/components/panel/variants/Variants'
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

const VariantDisplay = ({ variant }) => (variant ? <Variant variant={variant} /> : null)

VariantDisplay.propTypes = {
  variant: PropTypes.object,
}

class VariantLookup extends React.PureComponent {

  state = {
    url: null,
  }

  onSubmit = ({ variantId, genomeVersion }) => (
    new Promise(resolve => this.setState({ url: `/api/variant/${genomeVersion}/${variantId}` }, resolve))
  )

  parseResponse = response => response

  render() {
    const { url } = this.state
    return (
      <Grid divided="vertically">
        <Grid.Row>
          <Grid.Column width={5} />
          <Grid.Column width={6}>
            <Header dividing size="medium" content="Lookup Variant" />
            <FormWrapper noModal fields={FIELDS} onSubmit={this.onSubmit} />
          </Grid.Column>
          <Grid.Column width={5} />
        </Grid.Row>
        <StateDataLoader
          url={url}
          parseResponse={this.parseResponse}
          childComponent={VariantDisplay}
        />
      </Grid>
    )
  }

}

export default VariantLookup
