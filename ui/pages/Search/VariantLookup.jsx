import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Grid, Header, Label, Table } from 'semantic-ui-react'

import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { getVlmEnabled } from 'redux/selectors'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import StateDataLoader from 'shared/components/StateDataLoader'
import SendEmailButton from 'shared/components/buttons/SendEmailButton'
import FormWrapper from 'shared/components/form/FormWrapper'
import { helpLabel, validators } from 'shared/components/form/FormHelpers'
import { BaseSemanticInput, InlineToggle, AlignedCheckboxGroup } from 'shared/components/form/Inputs'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import FamilyVariantTags from 'shared/components/panel/variants/FamilyVariantTags'
import Variants, { Variant, StyledVariantRow } from 'shared/components/panel/variants/Variants'
import { FamilyVariantIndividuals } from 'shared/components/panel/variants/VariantIndividuals'
import {
  GENOME_VERSION_FIELD,
  GENOME_VERSION_37,
  GENOME_VERSION_38,
  GENE_SEARCH_FREQUENCIES,
  GROUPED_VEP_CONSEQUENCES,
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_FRAMESHIFT,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_INFRAME,
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
} from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { sendVlmContactEmail } from './reducers'
import { getVlmDefaultContactEmails, getVlmFamiliesByContactEmail, getSearchedVariantsIsLoading } from './selectors'

const LOOKUP_FIELDS = [
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
  {
    name: 'homOnly',
    label: 'Homozygotes Only',
    labelHelp: 'Only return cases where at least one call is homozygous',
    component: InlineToggle,
    asFormInput: true,
    fullHeight: true,
    color: 'grey',
  },
  {
    name: 'affectedOnly',
    label: 'Affected Only',
    labelHelp: 'Only return cases where the variant is present for at least one affected individual',
    component: InlineToggle,
    asFormInput: true,
    fullHeight: true,
    color: 'grey',
  },
]

const validateAnnotations = (value, { search }) => (
  value || Object.values(search.annotations || {}).some(val => val.length) ? undefined : 'At least one consequence filter is required'
)

const CONSEQUENCE_FILEDS = [
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_FRAMESHIFT,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_INFRAME,
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
].map((group, i) => ({
  name: `search.annotations.${group}`,
  component: AlignedCheckboxGroup,
  groupLabel: snakecaseToTitlecase(group),
  options: GROUPED_VEP_CONSEQUENCES[group],
  format: value => value || [],
  inline: true,
  validate: i === 0 ? validateAnnotations : undefined,
}))

const GENE_LOOKUP_FIELDS = [
  { validate: validators.required, ...GENOME_VERSION_FIELD, name: 'allGenomeProjectFamilies' },
  {
    name: 'search.locus.rawItems',
    label: 'Gene',
    control: AwesomeBarFormInput,
    categories: ['genes'],
    fluid: true,
    placeholder: 'Search for gene',
    validate: validators.required,
  },
  ...CONSEQUENCE_FILEDS,
]

const INITIAL_GENE_LOOKUP_VALUES = {
  includeNoAccessProjects: true,
  search: { freqs: GENE_SEARCH_FREQUENCIES },
}

const VlmDisplay = ({ vlmMatches }) => (
  <Table basic collapsing definition>
    {Object.entries(vlmMatches || {}).map(
      ([nodeId, nodeResults]) => Object.entries(nodeResults).map(([id, { url, counts }], i) => (
        <Table.Row key={id}>
          <Table.Cell content={i === 0 ? nodeId : null} />
          <Table.Cell content={`${id} Hom=${counts.Homozygous} Het=${counts.Heterozygous}`}>
            <a target="_blank" href={url} rel="noreferrer"><b>{id}</b></a>
            {counts.Homozygous >= 0 && ` Hom=${counts.Homozygous}`}
            {counts.Heterozygous >= 0 && ` Het=${counts.Heterozygous}`}
          </Table.Cell>
        </Table.Row>
      )),
    )}
  </Table>
)

VlmDisplay.propTypes = {
  vlmMatches: PropTypes.object,
}

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

const mapVariantStateToProps = (state, ownProps) => ({
  familiesByContactEmail: getVlmFamiliesByContactEmail(state, ownProps),
  vlmDefaultContactEmails: getVlmDefaultContactEmails(state, ownProps),
})

const LookupVariant = connect(mapVariantStateToProps)(BaseLookupVariant)

const VariantDisplay = ({ variants }) => (
  (variants || [])[0]?.lookupFamilyGuids ? <LookupVariant variant={variants[0]} /> : <Variants variants={variants} />
)

VariantDisplay.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.object),
}

const passThroughResponse = response => response

const BaseVariantLookupResults = ({ queryParams, receiveData, vlmEnabled }) => ([
  ...(vlmEnabled ? [(
    <Grid.Row key="vlm">
      <Grid.Column width={6} textAlign="right" verticalAlign="middle">
        <Header size="large" content="External Variant-Level Matching (VLM)" />
      </Grid.Column>
      <Grid.Column width={10}>
        <StateDataLoader
          url={queryParams.variantId && '/api/vlm_lookup'}
          query={queryParams}
          parseResponse={passThroughResponse}
          childComponent={VlmDisplay}
        />
      </Grid.Column>
    </Grid.Row>
  ), (
    <Grid.Row key="internal_header">
      <Grid.Column width={6} textAlign="right" verticalAlign="middle">
        <Header size="large" content="Internal seqr Variants" />
      </Grid.Column>
      <Grid.Column width={10} />
    </Grid.Row>
  )] : []), (
    <Grid.Row key="results">
      <Grid.Column width={16}>
        <StateDataLoader
          url={queryParams.variantId && '/api/variant_lookup'}
          query={queryParams}
          parseResponse={receiveData}
          childComponent={VariantDisplay}
        />
      </Grid.Column>
    </Grid.Row>
  ),
])

BaseVariantLookupResults.propTypes = {
  receiveData: PropTypes.func,
  queryParams: PropTypes.object,
  vlmEnabled: PropTypes.bool,
}

const mapResultsStateToProps = state => ({
  vlmEnabled: getVlmEnabled(state),
})

const mapResultsDispatchToProps = dispatch => ({
  receiveData: (updatesById) => {
    dispatch({ type: RECEIVE_DATA, updatesById })
    return updatesById
  },
})

const VariantLookupResults = connect(mapResultsStateToProps, mapResultsDispatchToProps)(BaseVariantLookupResults)

const LOOKUP_HEADER = { content: 'Lookup Variant' }
const GENE_LOOKUP_HEADER = {
  content: 'Lookup Variants in Gene',
  subheader: (
    <Header.Subheader>
      Lookup up all rare variants is seqr in a given gene, regardless of whether or not they are in your
      projects.
      <br />
      Variants are only returned if they have a gnomAD Allele Frequency &lt; 3%
      and have a seqr global Allele Count &lt; 3000.
    </Header.Subheader>
  ),
}

const VariantLookupRoute = ({ match, formProps, onSubmit, ...props }) => (
  <Grid divided="vertically" centered>
    <Grid.Row>
      <Grid.Column width={16}>
        <Header />
        <Header textAlign="center" {...(match.params.gene ? GENE_LOOKUP_HEADER : LOOKUP_HEADER)} />
      </Grid.Column>
    </Grid.Row>
    <Grid.Row>
      <Grid.Column width={match.params.gene ? 1 : 5} />
      <Grid.Column width={match.params.gene ? 14 : 6}>
        <FormWrapper
          {...formProps}
          onSubmit={onSubmit}
          noModal
          verticalAlign="top"
        />
      </Grid.Column>
      <Grid.Column width={match.params.gene ? 1 : 5} />
    </Grid.Row>
    {match.params.gene ? JSON.stringify(props) : <VariantLookupResults {...props} />}
  </Grid>
)

VariantLookupRoute.propTypes = {
  match: PropTypes.object,
  formProps: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  formProps: ownProps.match.params.gene ? {
    showErrorPanel: true,
    loading: getSearchedVariantsIsLoading(state),
    initialValues: INITIAL_GENE_LOOKUP_VALUES,
    fields: GENE_LOOKUP_FIELDS,
  } : {
    fields: LOOKUP_FIELDS,
    initialValues: ownProps.queryParams,
  },
})

const onQueryParamSubmit = (updateQueryParams, data) => {
  updateQueryParams(data)
  return Promise.resolve()
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: data => (ownProps.match.params.gene ?
    dispatch(navigateSavedHashedSearch(data)) :
    onQueryParamSubmit(ownProps.updateQueryParams, data)
  ),
})

const ConnectedVariantLookup = connect(mapStateToProps, mapDispatchToProps)(VariantLookupRoute)

export default props => (
  <QueryParamsEditor {...props}>
    <ConnectedVariantLookup />
  </QueryParamsEditor>
)
