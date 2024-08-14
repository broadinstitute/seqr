import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Grid, Header } from 'semantic-ui-react'

import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import StateDataLoader from 'shared/components/StateDataLoader'
import SendEmailButton from 'shared/components/buttons/SendEmailButton'
import FormWrapper from 'shared/components/form/FormWrapper'
import { helpLabel } from 'shared/components/form/FormHelpers'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import FamilyVariantTags from 'shared/components/panel/variants/FamilyVariantTags'
import Variants, { Variant, StyledVariantRow } from 'shared/components/panel/variants/Variants'
import { FamilyVariantIndividuals } from 'shared/components/panel/variants/VariantIndividuals'
import { GENOME_VERSION_FIELD } from 'shared/utils/constants'
import { sendVlmContactEmail } from '../reducers'
import { geVlmDefaultContactEmailByFamily } from '../selectors'

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

const mapContactStateToProps = (state, ownProps) => {
  const defaultEmail = geVlmDefaultContactEmailByFamily(state, ownProps)[ownProps.familyGuid]
  const disabled = !defaultEmail?.to
  return {
    defaultEmail,
    disabled,
    buttonText: disabled ? 'Contact Opted Out' : null,
    modalId: ownProps.familyGuid,
  }
}

const mapContactDispatchToProps = {
  onSubmit: sendVlmContactEmail,
}

const ContactButton = connect(mapContactStateToProps, mapContactDispatchToProps)(SendEmailButton)

const LookupFamily = ({ familyGuid, variant, reads, showReads }) => (
  <StyledVariantRow>
    <Grid.Column width={16}>
      <FamilyVariantTags familyGuid={familyGuid} variant={variant} linkToSavedVariants />
    </Grid.Column>
    <Grid.Column width={4}><ContactButton familyGuid={familyGuid} variant={variant} /></Grid.Column>
    <Grid.Column width={12}>
      <FamilyVariantIndividuals familyGuid={familyGuid} variant={variant} />
      {showReads}
    </Grid.Column>
    <Grid.Column width={16}>{reads}</Grid.Column>
  </StyledVariantRow>
)

LookupFamily.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  variant: PropTypes.object.isRequired,
  reads: PropTypes.object,
  showReads: PropTypes.object,
}

const LookupVariant = ({ variant }) => (
  <Grid stackable divided="vertically">
    <Variant variant={variant} />
    {variant.lookupFamilyGuids.map(familyGuid => (
      <FamilyReads key={familyGuid} layout={LookupFamily} familyGuid={familyGuid} variant={variant} />
    ))}
  </Grid>
)

LookupVariant.propTypes = {
  variant: PropTypes.object,
}

const VariantDisplay = ({ variants }) => (
  (variants || [])[0]?.lookupFamilyGuids ? <LookupVariant variant={variants[0]} /> : <Variants variants={variants} />
)

VariantDisplay.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.object),
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
