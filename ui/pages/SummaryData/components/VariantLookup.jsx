import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Grid, Header } from 'semantic-ui-react'

import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import StateDataLoader from 'shared/components/StateDataLoader'
import FormWrapper from 'shared/components/form/FormWrapper'
import { helpLabel } from 'shared/components/form/FormHelpers'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import Variants from 'shared/components/panel/variants/Variants'
import { GENOME_VERSION_FIELD } from 'shared/utils/constants'

const FIELDS = [
  {
    name: 'variantId',
    label: helpLabel('Variant ID', (
      <div>
        Variants should be represented as &nbsp;
        <i>chrom-pos-ref-alt</i>
        <br />
        For example, 4-88047328-C-T
      </div>
    )),
    inline: true,
    required: true,
    component: BaseSemanticInput,
    inputType: 'Input',
  },
  { required: true, ...GENOME_VERSION_FIELD },
]

const VariantDisplay = ({ variants }) => <Variants variants={variants} />

VariantDisplay.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.object),
}

const onSubmit = updateQueryParams => (data) => {
  updateQueryParams(data)
  return Promise.resolve()
}

const VariantLookup = ({ queryParams, receiveData, updateQueryParams }) => (
  <Grid divided="vertically" centered>
    {!queryParams.include_genotypes && (
      <Grid.Row>
        <Grid.Column width={5} />
        <Grid.Column width={6}>
          <Header dividing size="medium" content="Lookup Variant" />
          <FormWrapper noModal fields={FIELDS} initialValues={queryParams} onSubmit={onSubmit(updateQueryParams)} />
        </Grid.Column>
        <Grid.Column width={5} />
      </Grid.Row>
    )}
    <Grid.Row>
      <Grid.Column width={16}>
        <StateDataLoader
          url={queryParams.variantId && '/api/variant_lookup'}
          query={queryParams}
          parseResponse={receiveData}
          childComponent={VariantDisplay}
        />
      </Grid.Column>
    </Grid.Row>
  </Grid>
)

VariantLookup.propTypes = {
  receiveData: PropTypes.func,
  updateQueryParams: PropTypes.func,
  queryParams: PropTypes.object,
}

const mapDispatchToProps = dispatch => ({
  receiveData: (updatesById) => {
    dispatch({ type: RECEIVE_DATA, updatesById })
    return updatesById
  },
})

const WrappedVariantLookup = props => (
  <QueryParamsEditor {...props}>
    <VariantLookup />
  </QueryParamsEditor>
)

export default connect(null, mapDispatchToProps)(WrappedVariantLookup)
