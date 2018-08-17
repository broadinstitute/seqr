import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Field } from 'redux-form'
import { Form, Accordion, Header } from 'semantic-ui-react'

import { snakecaseToTitlecase } from 'shared/utils/stringUtils'


const CLINVAR_ANNOTATION_GROUPS = [
  {
    name: 'In Clinvar',
    slug: 'clinvar',
    children: [
      'pathogenic',
      'likely_pathogenic',
      'vus_or_conflicting',
      'likely_benign',
      'benign',
    ],
  },
]

const HGMD_ANNOTATION_GROUPS = [
  {
    name: 'In HGMD',
    slug: 'hgmd',
    children: [ // see https://portal.biobase-international.com/hgmd/pro/global.php#cats
      'disease_causing',
      'likely_disease_causing',
      'hgmd_other',
    ],
  },
]

const VEP_ANNOTATION_GROUPS = [
  {
    name: 'Nonsense',
    slug: 'nonsense',
    children: [
      'stop_gained',
    ],
  },
  {
    name: 'Essential splice site',
    slug: 'essential_splice_site',
    children: [
      'splice_donor_variant',
      'splice_acceptor_variant',
    ],
  },
  {
    name: 'Extended splice site',
    slug: 'extended_splice_site',
    children: [
      'splice_region_variant',
    ],
  },
  {
    name: 'Missense',
    slug: 'missense',
    children: [
      'stop_lost',
      'initiator_codon_variant',
      'start_lost',
      'missense_variant',
      'protein_altering_variant',
    ],
  },
  {
    name: 'Frameshift',
    slug: 'frameshift',
    children: [
      'frameshift_variant',
    ],
  },
  {
    name: 'In Frame',
    slug: 'inframe',
    children: [
      'inframe_insertion',
      'inframe_deletion',
    ],
  },
  {
    name: 'Synonymous',
    slug: 'synonymous',
    children: [
      'synonymous_variant',
      'stop_retained_variant',
    ],
  },
  {
    name: 'Other',
    slug: 'other',
    children: [
      'transcript_ablation',
      'transcript_amplification',
      'incomplete_terminal_codon_variant',
      'coding_sequence_variant',
      'mature_miRNA_variant',
      '5_prime_UTR_variant',
      '3_prime_UTR_variant',
      'intron_variant',
      'NMD_transcript_variant',
      'non_coding_exon_variant', // 2 kinds of 'non_coding_exon_variant' label due to name change in Ensembl v77
      'non_coding_transcript_exon_variant', // 2 kinds of 'non_coding_exon_variant' due to name change in Ensembl v77
      'nc_transcript_variant', // 2 kinds of 'nc_transcript_variant' label due to name change in Ensembl v77
      'non_coding_transcript_variant', // 2 kinds of 'nc_transcript_variant' due to name change in Ensembl v77
      'upstream_gene_variant',
      'downstream_gene_variant',
      'TFBS_ablation',
      'TFBS_amplification',
      'TF_binding_site_variant',
      'regulatory_region_variant',
      'regulatory_region_ablation',
      'regulatory_region_amplification',
      'feature_elongation',
      'feature_truncation',
      'intergenic_variant',
    ],
  },
]

const OPTIONS = [...CLINVAR_ANNOTATION_GROUPS, ...HGMD_ANNOTATION_GROUPS, ...VEP_ANNOTATION_GROUPS].reduce(
  (acc, { name, children }) =>
    [...acc, ...children.map(child => ({ category: name, value: child, text: snakecaseToTitlecase(child) }))],
  [],
)

const ToggleHeader = styled(Header).attrs({ size: 'medium' })`
  display: inline-block;
  margin-top: 1em !important;
  margin-bottom: 0.5em !important;
`

const FormSelect = props =>
  <Form.Select value={props.input.value} {...props} onChange={(e, fieldProps) => fieldProps.input.onChange(fieldProps.value)} />

FormSelect.propTypes = {
  input: PropTypes.object,
}

const QualityFilter = ({ input }) =>
  <Form.Input onChange={(e, data) => input.onChange({ ...input.value, min_ab: data.value })} value={input.value.min_ab} label="Min AB" />

QualityFilter.propTypes = {
  input: PropTypes.object,
}

const PANEL_DETAILS = [
  {
    name: 'annotations',
    title: 'Variant Annotations',
    component: FormSelect,
    label: 'Annotation',
    options: OPTIONS,
    multiple: true,
    format: val => val.split(','),
    parse: val => val.join(','),
  },
  {
    name: 'qualityFilter',
    title: 'Call Quality',
    component: QualityFilter,
    format: val => JSON.parse(val),
    parse: val => JSON.stringify(val),
  },
]

const PANELS = PANEL_DETAILS.map(({ name, title, ...fieldProps }) => ({
  key: name,
  title: {
    key: title,
    content: <ToggleHeader content={title} />,
  },
  content: {
    key: name,
    content: <Field name={name} {...fieldProps} />,
  },
}))

const VariantSearchForm = () => <Accordion styled fluid defaultActiveIndex={1} panels={PANELS} />

export default VariantSearchForm
