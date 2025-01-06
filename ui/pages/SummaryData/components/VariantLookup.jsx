import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Grid, Header, Label } from 'semantic-ui-react'

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
import { GENOME_VERSION_FIELD, GENOME_VERSION_37, GENOME_VERSION_38 } from 'shared/utils/constants'
import { sendVlmContactEmail } from '../reducers'
import { getVlmDefaultContactEmails, getVlmFamiliesByContactEmail } from '../selectors'

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

const mapContactDispatchToProps = {
  onSubmit: sendVlmContactEmail,
}

const ContactButton = connect(null, mapContactDispatchToProps)(SendEmailButton)

const liftoverGenomeVersion = genomeVersion => (
  genomeVersion === GENOME_VERSION_37 ? GENOME_VERSION_38 : GENOME_VERSION_37
)

const LookupFamilyLayout = ({ topContent, bottomContent, hasLiftover, genomeVersion, children, ...buttonProps }) => (
  <StyledVariantRow>
    {topContent}
    <Grid.Column width={4}>
      <Label
        content={`GRCh${hasLiftover ? liftoverGenomeVersion(genomeVersion) : genomeVersion}`}
        basic
        color={hasLiftover ? 'orange' : 'green'}
      />
      <ContactButton {...buttonProps} />
    </Grid.Column>
    <Grid.Column width={12}>
      {children}
    </Grid.Column>
    {bottomContent}
  </StyledVariantRow>
)

LookupFamilyLayout.propTypes = {
  topContent: PropTypes.node,
  bottomContent: PropTypes.node,
  children: PropTypes.node,
  hasLiftover: PropTypes.bool,
  genomeVersion: PropTypes.string,
}

const InternalFamily = ({ familyGuid, variant, reads, showReads }) => (
  <LookupFamilyLayout
    topContent={(
      <Grid.Column width={16}>
        <FamilyVariantTags familyGuid={familyGuid} variant={variant} linkToSavedVariants />
      </Grid.Column>
    )}
    bottomContent={<Grid.Column width={16}>{reads}</Grid.Column>}
    hasLiftover={variant.liftedFamilyGuids?.includes(familyGuid)}
    genomeVersion={variant.genomeVersion}
  >
    <FamilyVariantIndividuals familyGuid={familyGuid} variant={variant} />
    {showReads}
  </LookupFamilyLayout>
)

InternalFamily.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  variant: PropTypes.object.isRequired,
  reads: PropTypes.object,
  showReads: PropTypes.object,
}

const BaseLookupVariant = ({ variant, familiesByContactEmail, vlmDefaultContactEmails }) => {
  const { internal, disabled, ...familiesByContact } = familiesByContactEmail
  return (
    <Grid stackable divided="vertically">
      <Variant variant={variant} />
      {(internal || []).map(familyGuid => (
        <FamilyReads key={familyGuid} layout={InternalFamily} familyGuid={familyGuid} variant={variant} />
      ))}
      {Object.entries(familiesByContact).map(([contactEmail, families]) => (
        <LookupFamilyLayout
          key={contactEmail}
          defaultEmail={vlmDefaultContactEmails[contactEmail]}
          modalId={contactEmail}
          hasLiftover={(variant.liftedFamilyGuids || []).some(familyGuid => families.includes(familyGuid))}
          genomeVersion={variant.genomeVersion}
        >
          <Grid stackable divided="vertically">
            {families.map(familyGuid => (
              <Grid.Row key={familyGuid}>
                <Grid.Column width={16}>
                  <FamilyVariantIndividuals familyGuid={familyGuid} variant={variant} />
                </Grid.Column>
              </Grid.Row>
            ))}
          </Grid>
        </LookupFamilyLayout>
      ))}
      {(disabled || []).map(familyGuid => (
        <LookupFamilyLayout key={familyGuid} defaultEmail={vlmDefaultContactEmails.disabled} disabled buttonText="Contact Opted Out">
          <FamilyVariantIndividuals familyGuid={familyGuid} variant={variant} />
        </LookupFamilyLayout>
      ))}
    </Grid>
  )
}

BaseLookupVariant.propTypes = {
  variant: PropTypes.object,
  familiesByContactEmail: PropTypes.object,
  vlmDefaultContactEmails: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  familiesByContactEmail: getVlmFamiliesByContactEmail(state, ownProps),
  vlmDefaultContactEmails: getVlmDefaultContactEmails(state, ownProps),
})

const LookupVariant = connect(mapStateToProps)(BaseLookupVariant)

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
