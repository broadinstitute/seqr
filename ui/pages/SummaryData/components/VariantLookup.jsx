import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Grid, Header } from 'semantic-ui-react'

import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
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

const onSubmit = updateQueryParams => (data) => {
  updateQueryParams(data)
  return Promise.resolve()
}

const VariantLookup = ({ queryParams, receiveData, updateQueryParams }) => (
  <Grid divided="vertically" centered>
    <Grid.Row>
      <Grid.Column width={5} />
      <Grid.Column width={6}>
        <Header dividing size="medium" content="Lookup Variant" />
        <FormWrapper noModal fields={FIELDS} initialValues={queryParams} onSubmit={onSubmit(updateQueryParams)} />
      </Grid.Column>
      <Grid.Column width={5} />
    </Grid.Row>
    <StateDataLoader
      url={queryParams.variantId && '/api/variant_lookup'}
      query={queryParams}
      parseResponse={receiveData}
      childComponent={VariantDisplay}
    />
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
