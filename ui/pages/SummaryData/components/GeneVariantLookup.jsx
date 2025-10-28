import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Grid, Header } from 'semantic-ui-react'

import { validators } from 'shared/components/form/FormHelpers'
import FormWrapper from 'shared/components/form/FormWrapper'
import { AlignedCheckboxGroup } from 'shared/components/form/Inputs'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import { Variant } from 'shared/components/panel/variants/Variants'
import {
  GENE_SEARCH_FREQUENCIES,
  GENOME_VERSION_FIELD,
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
import { loadGeneVariantLookup } from '../reducers'
import { getGeneVariantLookupLoading, getGeneVariantLookupResults } from '../selectors'

const validateAnnotations = (value, { annotations }) => (
  value || Object.values(annotations || {}).some(val => val.length) ? undefined : 'At least one consequence filter is required'
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
  name: `annotations.${group}`,
  component: AlignedCheckboxGroup,
  groupLabel: snakecaseToTitlecase(group),
  options: GROUPED_VEP_CONSEQUENCES[group],
  format: value => value || [],
  inline: true,
  validate: i === 0 ? validateAnnotations : undefined,
}))

const FIELDS = [
  { validate: validators.required, ...GENOME_VERSION_FIELD },
  {
    name: 'geneId',
    label: 'Gene',
    control: AwesomeBarFormInput,
    categories: ['genes'],
    fluid: true,
    placeholder: 'Search for gene',
    validate: validators.required,
  },
  ...CONSEQUENCE_FILEDS,
]

const INITIAL_VALUES = { freqs: GENE_SEARCH_FREQUENCIES }

const GeneVariantLookup = ({ loading, results, onSubmit }) => (
  <Grid divided="vertically">
    <Grid.Row>
      <Grid.Column width={16}>
        <Header
          textAlign="center"
          content="Lookup Variants in Gene"
          subheader={(
            <Header.Subheader>
              Lookup up all rare variants is seqr in a given gene, regardless of whether or not they are in your
              projects.
              <br />
              Variants are only returned if they have a gnomAD Allele Frequency &lt; 3%
              and have a seqr global Allele Count &lt; 3000.
            </Header.Subheader>
          )}
        />
      </Grid.Column>
    </Grid.Row>
    <Grid.Row>
      <Grid.Column width={1} />
      <Grid.Column width={14}>
        <FormWrapper
          loading={loading}
          onSubmit={onSubmit}
          initialValues={INITIAL_VALUES}
          fields={FIELDS}
          noModal
          showErrorPanel
          verticalAlign="top"
        />
      </Grid.Column>
      <Grid.Column width={1} />
    </Grid.Row>
    {!loading && results && (
      <Grid.Row>
        <Grid.Column width={16}>
          Found &nbsp;
          <b>{results.length}</b>
          &nbsp; variants
        </Grid.Column>
      </Grid.Row>
    )}
    {!loading && results?.map(variant => (
      <Variant key={variant.key} variant={variant} />
    ))}
  </Grid>
)

GeneVariantLookup.propTypes = {
  loading: PropTypes.bool,
  results: PropTypes.arrayOf(PropTypes.object),
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  loading: getGeneVariantLookupLoading(state),
  results: getGeneVariantLookupResults(state),
})

const mapDispatchToProps = {
  onSubmit: loadGeneVariantLookup,
}

export default connect(mapStateToProps, mapDispatchToProps)(GeneVariantLookup)
