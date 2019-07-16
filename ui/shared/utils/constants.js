import { Form } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import { validators } from '../components/form/ReduxFormWrapper'
import { BooleanCheckbox, RadioGroup, Dropdown, InlineToggle, Pagination, BaseSemanticInput } from '../components/form/Inputs'
import BaseFieldView from '../components/panel/view-fields/BaseFieldView'
import OptionFieldView from '../components/panel/view-fields/OptionFieldView'
import ListFieldView from '../components/panel/view-fields/ListFieldView'
import SingleFieldView from '../components/panel/view-fields/SingleFieldView'

import { stripMarkdown } from './stringUtils'


export const GENOME_VERSION_37 = '37'
export const GENOME_VERSION_38 = '38'
export const GENOME_VERSION_OPTIONS = [
  { value: GENOME_VERSION_37, text: 'GRCh37' },
  { value: GENOME_VERSION_38, text: 'GRCh38' },
]

// PROJECT FIELDS

export const EDITABLE_PROJECT_FIELDS = [
  { name: 'name', label: 'Project Name', placeholder: 'Name', validate: validators.required, autoFocus: true },
  { name: 'description', label: 'Project Description', placeholder: 'Description' },
]

export const PROJECT_FIELDS = [
  ...EDITABLE_PROJECT_FIELDS,
  { name: 'genomeVersion', label: 'Genome Version', component: RadioGroup, options: GENOME_VERSION_OPTIONS },
]


// SAMPLES

export const DATASET_TYPE_READ_ALIGNMENTS = 'ALIGN'
export const DATASET_TYPE_VARIANT_CALLS = 'VARIANTS'

export const SAMPLE_STATUS_LOADED = 'loaded'

export const SAMPLE_TYPE_EXOME = 'WES'
export const SAMPLE_TYPE_GENOME = 'WGS'
export const SAMPLE_TYPE_RNA = 'RNA'

export const SAMPLE_TYPE_OPTIONS = [
  { value: SAMPLE_TYPE_EXOME, text: 'Exome' },
  { value: SAMPLE_TYPE_GENOME, text: 'Genome' },
  { value: SAMPLE_TYPE_RNA, text: 'RNA-seq' },
]

export const SAMPLE_TYPE_LOOKUP = SAMPLE_TYPE_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt },
  }), {},
)

// ANALYSIS STATUS

export const FAMILY_STATUS_SOLVED = 'S'
export const FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE = 'S_kgfp'
export const FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'S_kgdp'
export const FAMILY_STATUS_SOLVED_NOVEL_GENE = 'S_ng'
export const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE = 'Sc_kgfp'
export const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'Sc_kgdp'
export const FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE = 'Sc_ng'
export const FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES = 'Rcpc'
export const FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE = 'Rncc'
export const FAMILY_STATUS_CLOSED = 'C'
export const FAMILY_STATUS_ANALYSIS_IN_PROGRESS = 'I'
const FAMILY_STATUS_WAITING_FOR_DATA = 'Q'

export const FAMILY_ANALYSIS_STATUS_OPTIONS = [
  { value: FAMILY_STATUS_SOLVED, color: '#4CAF50', name: 'Solved' },
  { value: FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE, color: '#4CAF50', name: 'Solved - known gene for phenotype' },
  { value: FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE, color: '#4CAF50', name: 'Solved - gene linked to different phenotype' },
  { value: FAMILY_STATUS_SOLVED_NOVEL_GENE, color: '#4CAF50', name: 'Solved - novel gene' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE, color: '#CDDC39', name: 'Strong candidate - known gene for phenotype' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE, color: '#CDDC39', name: 'Strong candidate - gene linked to different phenotype' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE, color: '#CDDC39', name: 'Strong candidate - novel gene' },
  { value: FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES, color: '#CDDC39', name: 'Reviewed, currently pursuing candidates' },
  { value: FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE, color: '#EF5350', name: 'Reviewed, no clear candidate' },
  { value: FAMILY_STATUS_CLOSED, color: '#9c0502', name: 'Closed, no longer under analysis' },
  { value: FAMILY_STATUS_ANALYSIS_IN_PROGRESS, color: '#4682B4', name: 'Analysis in Progress' },
  { value: FAMILY_STATUS_WAITING_FOR_DATA, color: '#FFC107', name: 'Waiting for data' },
]

// FAMILY FIELDS

export const FAMILY_FIELD_ID = 'familyId'
export const FAMILY_DISPLAY_NAME = 'displayName'
export const FAMILY_FIELD_DESCRIPTION = 'description'
export const FAMILY_FIELD_ANALYSIS_STATUS = 'analysisStatus'
export const FAMILY_FIELD_ASSIGNED_ANALYST = 'assignedAnalyst'
export const FAMILY_FIELD_ANALYSED_BY = 'analysedBy'
export const FAMILY_FIELD_ANALYSIS_NOTES = 'analysisNotes'
export const FAMILY_FIELD_ANALYSIS_SUMMARY = 'analysisSummary'
export const FAMILY_FIELD_INTERNAL_NOTES = 'internalCaseReviewNotes'
export const FAMILY_FIELD_INTERNAL_SUMMARY = 'internalCaseReviewSummary'
export const FAMILY_FIELD_FIRST_SAMPLE = 'firstSample'
export const FAMILY_FIELD_CODED_PHENOTYPE = 'codedPhenotype'
export const FAMILY_FIELD_OMIM_NUMBER = 'postDiscoveryOmimNumber'
export const FAMILY_FIELD_PMIDS = 'pubmedIds'
export const FAMILY_FIELD_PEDIGREE = 'pedigreeImage'
export const FAMILY_FIELD_CREATED_DATE = 'createdDate'

export const FAMILY_FIELD_RENDER_LOOKUP = {
  [FAMILY_FIELD_DESCRIPTION]: { name: 'Family Description' },
  [FAMILY_FIELD_ANALYSIS_STATUS]: { name: 'Analysis Status', component: OptionFieldView },
  [FAMILY_FIELD_ASSIGNED_ANALYST]: {
    name: 'Assigned Analyst',
    component: BaseFieldView,
    submitArgs: { familyField: 'assigned_analyst' },
  },
  [FAMILY_FIELD_ANALYSED_BY]: {
    name: 'Analysed By',
    component: BaseFieldView,
    submitArgs: { familyField: 'analysed_by' },
  },
  [FAMILY_FIELD_FIRST_SAMPLE]: { name: 'Data Loaded?', component: BaseFieldView },
  [FAMILY_FIELD_ANALYSIS_NOTES]: { name: 'Notes' },
  [FAMILY_FIELD_ANALYSIS_SUMMARY]: { name: 'Analysis Summary' },
  [FAMILY_FIELD_CODED_PHENOTYPE]: { name: 'Coded Phenotype', component: SingleFieldView },
  [FAMILY_FIELD_OMIM_NUMBER]: { name: 'Post-discovery OMIM #', component: SingleFieldView },
  [FAMILY_FIELD_PMIDS]: { name: 'Publications on this discovery', component: ListFieldView },
  [FAMILY_FIELD_INTERNAL_NOTES]: { name: 'Internal Notes', internal: true },
  [FAMILY_FIELD_INTERNAL_SUMMARY]: { name: 'Internal Summary', internal: true },
}

export const FAMILY_DETAIL_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_STATUS, canEdit: true },
  { id: FAMILY_FIELD_ASSIGNED_ANALYST, canEdit: true },
  { id: FAMILY_FIELD_ANALYSED_BY, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_NOTES, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY, canEdit: true },
  { id: FAMILY_FIELD_CODED_PHENOTYPE, canEdit: true },
  { id: FAMILY_FIELD_OMIM_NUMBER, canEdit: true },
  { id: FAMILY_FIELD_PMIDS, canEdit: true },
]

// INDIVIDUAL FIELDS

export const SEX_OPTIONS = [
  { value: 'M', text: 'Male' },
  { value: 'F', text: 'Female' },
  { value: 'U', text: '?' },
]

export const SEX_LOOKUP = SEX_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.text === '?' ? 'Unknown' : opt.text },
  }), {},
)

export const AFFECTED = 'A'
export const UNAFFECTED = 'N'
export const UNKNOWN_AFFECTED = 'U'
export const AFFECTED_OPTIONS = [
  { value: AFFECTED, text: 'Affected' },
  { value: UNAFFECTED, text: 'Unaffected' },
  { value: UNKNOWN_AFFECTED, text: '?' },
]

export const AFFECTED_LOOKUP = AFFECTED_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.text === '?' ? 'Unknown' : opt.text },
  }), {},
)

export const INDIVIDUAL_FIELD_ID = 'individualId'
export const INDIVIDUAL_FIELD_PATERNAL_ID = 'paternalId'
export const INDIVIDUAL_FIELD_MATERNAL_ID = 'maternalId'
export const INDIVIDUAL_FIELD_SEX = 'sex'
export const INDIVIDUAL_FIELD_AFFECTED = 'affected'
export const INDIVIDUAL_FIELD_NOTES = 'notes'

export const INDIVIDUAL_FIELD_CONFIGS = {
  [FAMILY_FIELD_ID]: { label: 'Family ID' },
  [INDIVIDUAL_FIELD_ID]: { label: 'Individual ID' },
  [INDIVIDUAL_FIELD_PATERNAL_ID]: { label: 'Paternal ID', description: 'Individual ID of the father' },
  [INDIVIDUAL_FIELD_MATERNAL_ID]: { label: 'Maternal ID', description: 'Individual ID of the mother' },
  [INDIVIDUAL_FIELD_SEX]: {
    label: 'Sex',
    format: sex => SEX_LOOKUP[sex],
    width: 3,
    description: 'Male or Female, leave blank if unknown',
    formFieldProps: { component: RadioGroup, options: SEX_OPTIONS },
  },
  [INDIVIDUAL_FIELD_AFFECTED]: {
    label: 'Affected Status',
    format: affected => AFFECTED_LOOKUP[affected],
    width: 4,
    description: 'Affected or Unaffected, leave blank if unknown',
    formFieldProps: { component: RadioGroup, options: AFFECTED_OPTIONS },
  },
  [INDIVIDUAL_FIELD_NOTES]: { label: 'Notes', format: stripMarkdown, description: 'free-text notes related to this individual' },
}


export const INDIVIDUAL_HPO_EXPORT_DATA = [
  {
    header: 'HPO Terms (present)',
    field: 'phenotipsData',
    format: phenotipsData => (
      (phenotipsData || {}).features ?
        phenotipsData.features.filter(feature => feature.observed === 'yes').map(feature => `${feature.id} (${feature.label})`).join('; ') :
        ''
    ),
    description: 'comma-separated list of HPO Terms for present phenotypes in this individual',
  },
  {
    header: 'HPO Terms (absent)',
    field: 'phenotipsData',
    format: phenotipsData => (
      (phenotipsData || {}).features ?
        phenotipsData.features.filter(feature => feature.observed === 'no').map(feature => `${feature.id} (${feature.label})`).join('; ') :
        ''
    ),
    description: 'comma-separated list of HPO Terms for phenotypes not present in this individual',
  },
]

export const latestSamplesLoaded = (sampleGuids, samplesByGuid, datasetType) => {
  const loadedSamples = sampleGuids.map(sampleGuid => samplesByGuid[sampleGuid]).filter(sample =>
    sample.datasetType === (datasetType || DATASET_TYPE_VARIANT_CALLS) &&
    sample.sampleStatus === SAMPLE_STATUS_LOADED &&
    sample.loadedDate,
  )
  return orderBy(loadedSamples, [s => s.loadedDate], 'asc')
}

export const familySamplesLoaded = (family, individualsByGuid, samplesByGuid, datasetType) => {
  const sampleGuids = [...family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).reduce(
    (acc, individual) => new Set([...acc, ...individual.sampleGuids]), new Set(),
  )]
  return latestSamplesLoaded(sampleGuids, samplesByGuid, datasetType)
}

// CLINVAR

export const CLINSIG_SEVERITY = {
  // clinvar
  pathogenic: 1,
  'risk factor': 0,
  risk_factor: 0,
  'likely pathogenic': 1,
  'pathogenic/likely_pathogenic': 1,
  likely_pathogenic: 1,
  benign: -1,
  'likely benign': -1,
  'benign/likely_benign': -1,
  likely_benign: -1,
  protective: -1,
  // hgmd
  DM: 1,
  'DM?': 0,
  FPV: 0,
  FP: 0,
  DFP: 0,
  DP: 0,
}


// LOCUS LISTS

export const LOCUS_LIST_IS_PUBLIC_FIELD_NAME = 'isPublic'
export const LOCUS_LIST_LAST_MODIFIED_FIELD_NAME = 'lastModifiedDate'
export const LOCUS_LIST_CURATOR_FIELD_NAME = 'createdBy'

export const LOCUS_LIST_FIELDS = [
  {
    name: 'name',
    label: 'List Name',
    labelHelp: 'A descriptive name for this gene list',
    validate: value => (value ? undefined : 'Name is required'),
    width: 3,
    isEditable: true,
  },
  { name: 'numEntries', label: 'Entries', width: 1 },
  {
    name: 'description',
    label: 'Description',
    labelHelp: 'Some background on how this list is curated',
    width: 9,
    isEditable: true,
  },
  {
    name: LOCUS_LIST_LAST_MODIFIED_FIELD_NAME,
    label: 'Last Updated',
    width: 3,
    fieldDisplay: lastModifiedDate => new Date(lastModifiedDate).toLocaleString('en-US', { year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' }),
  },
  { name: LOCUS_LIST_CURATOR_FIELD_NAME, label: 'Curator', width: 3 },
  {
    name: LOCUS_LIST_IS_PUBLIC_FIELD_NAME,
    label: 'Public List',
    labelHelp: 'Should other seqr users be able to use this gene list?',
    component: RadioGroup,
    options: [{ value: true, text: 'Yes' }, { value: false, text: 'No' }],
    fieldDisplay: isPublic => (isPublic ? 'Yes' : 'No'),
    width: 2,
    isEditable: true,
  },
]

export const LOCUS_LIST_ITEMS_FIELD = {
  name: 'rawItems',
  label: 'Genes/ Intervals',
  labelHelp: 'A list of genes and intervals. Can be separated by commas or whitespace. Intervals should be in the form <chrom>:<start>-<end>',
  fieldDisplay: () => null,
  isEditable: true,
  component: Form.TextArea,
  rows: 12,
  validate: value => (value ? undefined : 'Genes and/or intervals are required'),
  additionalFormFields: [
    {
      name: 'intervalGenomeVersion',
      component: RadioGroup,
      options: GENOME_VERSION_OPTIONS,
      label: 'Genome Version',
      labelHelp: 'The genome version associated with intervals. Only required if the list contains intervals',
      validate: (value, allValues) => (
        (value || !(allValues.rawItems || '').match(/([^\s-]*):(\d*)-(\d*)/)) ? undefined :
          'Genome version is required for lists with intervals'
      ),
    },
    {
      name: 'ignoreInvalidItems',
      component: BooleanCheckbox,
      label: 'Ignore invalid genes and intervals',
    },
  ],
}

export const VEP_GROUP_NONSENSE = 'nonsense'
export const VEP_GROUP_ESSENTIAL_SPLICE_SITE = 'essential_splice_site'
export const VEP_GROUP_EXTENDED_SPLICE_SITE = 'extended_splice_site'
export const VEP_GROUP_MISSENSE = 'missense'
export const VEP_GROUP_FRAMESHIFT = 'frameshift'
export const VEP_GROUP_INFRAME = 'in_frame'
export const VEP_GROUP_SYNONYMOUS = 'synonymous'
export const VEP_GROUP_OTHER = 'other'


const ORDERED_VEP_CONSEQUENCES = [
  {
    description: 'A feature ablation whereby the deleted region includes a transcript feature',
    text: 'Transcript ablation',
    value: 'transcript_ablation',
    so: 'SO:0001893',
  },
  {
    description: "A splice variant that changes the 2 base region at the 5' end of an intron",
    text: 'Splice donor variant',
    value: 'splice_donor_variant',
    group: VEP_GROUP_ESSENTIAL_SPLICE_SITE,
    so: 'SO:0001575',
  },
  {
    description: "A splice variant that changes the 2 base region at the 3' end of an intron",
    text: 'Splice acceptor variant',
    value: 'splice_acceptor_variant',
    group: VEP_GROUP_ESSENTIAL_SPLICE_SITE,
    so: 'SO:0001574',
  },
  {
    description: 'A sequence variant whereby at least one base of a codon is changed, resulting in a premature stop codon, leading to a shortened transcript',
    text: 'Stop gained',
    value: 'stop_gained',
    group: VEP_GROUP_NONSENSE,
    so: 'SO:0001587',
  },
  {
    description: 'A sequence variant which causes a disruption of the translational reading frame, because the number of nucleotides inserted or deleted is not a multiple of three',
    text: 'Frameshift',
    value: 'frameshift_variant',
    group: VEP_GROUP_FRAMESHIFT,
    so: 'SO:0001589',
  },
  {
    description: 'A sequence variant where at least one base of the terminator codon (stop) is changed, resulting in an elongated transcript',
    text: 'Stop lost',
    value: 'stop_lost',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001578',
  },
  {
    description: 'A codon variant that changes at least one base of the first codon of a transcript',
    text: 'Initiator codon',
    value: 'initiator_codon_variant',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001582',
  },
  {
    description: 'A codon variant that changes at least one base of the canonical start codon.',
    text: 'Start lost',
    value: 'start_lost',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0002012',
  },
  {
    description: 'An inframe non synonymous variant that inserts bases into in the coding sequence',
    text: 'In frame insertion',
    value: 'inframe_insertion',
    group: VEP_GROUP_INFRAME,
    so: 'SO:0001821',
  },
  {
    description: 'An inframe non synonymous variant that deletes bases from the coding sequence',
    text: 'In frame deletion',
    value: 'inframe_deletion',
    group: VEP_GROUP_INFRAME,
    so: 'SO:0001822',
  },
  {
    description: 'A feature amplification of a region containing a transcript',
    text: 'Transcript amplification',
    value: 'transcript_amplification',
    so: 'SO:0001889',
  },
  {
    description: 'A sequence_variant which is predicted to change the protein encoded in the coding sequence',
    text: 'Protein Altering',
    value: 'protein_altering_variant',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001818',
  },
  {
    description: 'A sequence variant, where the change may be longer than 3 bases, and at least one base of a codon is changed resulting in a codon that encodes for a different amino acid',
    text: 'Missense',
    value: 'missense_variant',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001583',
  },
  {
    description: 'A sequence variant in which a change has occurred within the region of the splice site, either within 1-3 bases of the exon or 3-8 bases of the intron',
    text: 'Splice region',
    value: 'splice_region_variant',
    group: VEP_GROUP_EXTENDED_SPLICE_SITE,
    so: 'SO:0001630',
  },
  {
    description: 'A sequence variant where at least one base of the final codon of an incompletely annotated transcript is changed',
    text: 'Incomplete terminal codon variant',
    value: 'incomplete_terminal_codon_variant',
    so: 'SO:0001626',
  },
  {
    description: 'A sequence variant where there is no resulting change to the encoded amino acid',
    text: 'Synonymous',
    value: 'synonymous_variant',
    group: VEP_GROUP_SYNONYMOUS,
    so: 'SO:0001819',
  },
  {
    description: 'A sequence variant where at least one base in the terminator codon is changed, but the terminator remains',
    text: 'Stop retained',
    value: 'stop_retained_variant',
    group: VEP_GROUP_SYNONYMOUS,
    so: 'SO:0001567',
  },
  {
    description: 'A sequence variant that changes the coding sequence',
    text: 'Coding sequence variant',
    value: 'coding_sequence_variant',
    so: 'SO:0001580',
  },
  {
    description: 'A transcript variant located with the sequence of the mature miRNA',
    text: 'Mature miRNA variant',
    value: 'mature_miRNA_variant',
    so: 'SO:0001620',
  },
  {
    description: "A UTR variant of the 5' UTR",
    text: '5 prime UTR variant',
    value: '5_prime_UTR_variant',
    so: 'SO:0001623',
  },
  {
    description: "A UTR variant of the 3' UTR",
    text: '3 prime UTR variant',
    value: '3_prime_UTR_variant',
    so: 'SO:0001624',
  },
  {
    description: 'A transcript variant occurring within an intron',
    text: 'Intron variant',
    value: 'intron_variant',
    so: 'SO:0001627',
  },
  {
    description: 'A variant in a transcript that is the target of NMD',
    text: 'NMD transcript variant',
    value: 'NMD_transcript_variant',
    so: 'SO:0001621',
  },
  //2 kinds of 'non_coding_transcript_exon_variant' text due to value change in Ensembl v77
  {
    description: 'A sequence variant that changes non-coding exon sequence',
    text: 'Non-coding exon variant',
    value: 'non_coding_exon_variant',
    so: 'SO:0001792',
  },
  {
    description: 'A sequence variant that changes non-coding exon sequence',
    text: 'Non-coding transcript exon variant',
    value: 'non_coding_transcript_exon_variant',
    so: 'SO:0001792',
  },
  // 2 kinds of 'nc_transcript_variant' text due to value change in Ensembl v77
  {
    description: 'A transcript variant of a non coding RNA',
    text: 'nc transcript variant',
    value: 'nc_transcript_variant',
    so: 'SO:0001619',
  },
  {
    description: 'A transcript variant of a non coding RNA',
    text: 'Non-coding transcript variant',
    value: 'non_coding_transcript_variant',
    so: 'SO:0001619',
  },
  {
    description: 'A feature ablation whereby the deleted region includes a transcription factor binding site',
    text: 'TFBS ablation',
    value: 'TFBS_ablation',
    so: 'SO:0001895',
  },
  {
    description: 'A feature amplification of a region containing a transcription factor binding site',
    text: 'TFBS amplification',
    value: 'TFBS_amplification',
    so: 'SO:0001892',
  },
  {
    description: 'In regulatory region annotated by Ensembl',
    text: 'TF binding site variant',
    value: 'TF_binding_site_variant',
    so: 'SO:0001782',
  },
  {
    description: 'A sequence variant located within a regulatory region',
    text: 'Regulatory region variant',
    value: 'regulatory_region_variant',
    so: 'SO:0001566',
  },
  {
    description: 'A feature ablation whereby the deleted region includes a regulatory region',
    text: 'Regulatory region ablation',
    value: 'regulatory_region_ablation',
    so: 'SO:0001894',
  },
  {
    description: 'A feature amplification of a region containing a regulatory region',
    text: 'Regulatory region amplification',
    value: 'regulatory_region_amplification',
    so: 'SO:0001891',
  },
  {
    description: 'A sequence variant that causes the extension of a genomic feature, with regard to the reference sequence',
    text: 'Feature elongation',
    value: 'feature_elongation',
    so: 'SO:0001907',
  },
  {
    description: 'A sequence variant that causes the reduction of a genomic feature, with regard to the reference sequence',
    text: 'Feature truncation',
    value: 'feature_truncation',
    so: 'SO:0001906',
  },
  {
    description: 'A sequence variant located in the intergenic region, between genes',
    text: 'Intergenic variant',
    value: 'intergenic_variant',
    so: 'SO:0001628',
  },
]

export const GROUPED_VEP_CONSEQUENCES = ORDERED_VEP_CONSEQUENCES.reduce((acc, consequence) => {
  const group = consequence.group || VEP_GROUP_OTHER
  acc[group] = [...(acc[group] || []), consequence]
  return acc
}, {})

export const VEP_CONSEQUENCE_ORDER_LOOKUP = ORDERED_VEP_CONSEQUENCES.reduce((acc, consequence, i) =>
  ({ ...acc, [consequence.value]: i }),
{})

export const SHOW_ALL = 'ALL'
export const NOTE_TAG_NAME = 'Has Notes'
export const EXCLUDED_TAG_NAME = 'Excluded'
export const REVIEW_TAG_NAME = 'Review'
export const KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME = 'Known gene for phenotype'
export const DISCOVERY_CATEGORY_NAME = 'CMG Discovery Tags'


export const SORT_BY_FAMILY_GUID = 'FAMILY_GUID'
export const SORT_BY_XPOS = 'XPOS'
const SORT_BY_PATHOGENICITY = 'PATHOGENICITY'
const SORT_BY_IN_OMIM = 'IN_OMIM'
const SORT_BY_PROTEIN_CONSQ = 'PROTEIN_CONSEQUENCE'
const SORT_BY_GNOMAD = 'GNOMAD'
const SORT_BY_EXAC = 'EXAC'
const SORT_BY_1KG = '1KG'
const SORT_BY_CONSTRAINT = 'CONSTRAINT'
const SORT_BY_CADD = 'CADD'
const SORT_BY_REVEL = 'REVEL'
const SORT_BY_SPLICE_AI = 'SPLICE_AI'
const SORT_BY_EIGEN = 'EIGEN'
const SORT_BY_MPC = 'MPC'
const SORT_BY_PRIMATE_AI = 'PRIMATE_AI'


const clinsigSeverity = (variant, user) => {
  const clinvarSignificance = variant.clinvar.clinicalSignificance && variant.clinvar.clinicalSignificance.split('/')[0]
  const hgmdSignificance = user.isStaff && variant.hgmd.class
  if (!clinvarSignificance && !hgmdSignificance) return -10
  let clinvarSeverity = 0.1
  if (clinvarSignificance) {
    clinvarSeverity = clinvarSignificance in CLINSIG_SEVERITY ? CLINSIG_SEVERITY[clinvarSignificance] + 1 : 0.5
  }
  const hgmdSeverity = hgmdSignificance in CLINSIG_SEVERITY ? CLINSIG_SEVERITY[hgmdSignificance] + 0.5 : 0
  return clinvarSeverity + hgmdSeverity
}

export const MISSENSE_THRESHHOLD = 3
export const LOF_THRESHHOLD = 0.35

const getGeneConstraintSortScore = ({ constraints }) => {
  if (!constraints || constraints.louef === undefined) {
    return Infinity
  }
  let missenseOffset = constraints.misZ > MISSENSE_THRESHHOLD ? constraints.misZ : 0
  if (constraints.louef > LOF_THRESHHOLD) {
    missenseOffset /= MISSENSE_THRESHHOLD
  }
  return constraints.louef - missenseOffset
}


const VARIANT_SORT_OPTONS = [
  { value: SORT_BY_FAMILY_GUID, text: 'Family', comparator: (a, b) => a.familyGuids[0].localeCompare(b.familyGuids[0]) },
  { value: SORT_BY_XPOS, text: 'Position', comparator: (a, b) => a.xpos - b.xpos },
  {
    value: SORT_BY_PROTEIN_CONSQ,
    text: 'Protein Consequence',
    comparator: (a, b) =>
      VEP_CONSEQUENCE_ORDER_LOOKUP[a.mainTranscript.majorConsequence] - VEP_CONSEQUENCE_ORDER_LOOKUP[b.mainTranscript.majorConsequence],
  },
  { value: SORT_BY_GNOMAD, text: 'gnomAD Genomes Frequency', comparator: (a, b) => a.populations.gnomad_genomes.af - b.populations.gnomad_genomes.af },
  { value: SORT_BY_EXAC, text: 'ExAC Frequency', comparator: (a, b) => a.populations.exac.af - b.populations.exac.af },
  { value: SORT_BY_1KG, text: '1kg  Frequency', comparator: (a, b) => a.populations.g1k.af - b.populations.g1k.af },
  { value: SORT_BY_CADD, text: 'Cadd', comparator: (a, b) => b.predictions.cadd - a.predictions.cadd },
  { value: SORT_BY_REVEL, text: 'Revel', comparator: (a, b) => b.predictions.revel - a.predictions.revel },
  { value: SORT_BY_EIGEN, text: 'Eigen', comparator: (a, b) => b.predictions.eigen - a.predictions.eigen },
  { value: SORT_BY_MPC, text: 'MPC', comparator: (a, b) => b.predictions.mpc - a.predictions.mpc },
  { value: SORT_BY_SPLICE_AI, text: 'Splice AI', comparator: (a, b) => b.predictions.splice_ai - a.predictions.splice_ai },
  { value: SORT_BY_PRIMATE_AI, text: 'Primate AI', comparator: (a, b) => b.predictions.primate_ai - a.predictions.primate_ai },
  { value: SORT_BY_PATHOGENICITY, text: 'Pathogenicity', comparator: (a, b, geneId, user) => clinsigSeverity(b, user) - clinsigSeverity(a, user) },
  {
    value: SORT_BY_CONSTRAINT,
    text: 'Constraint',
    comparator: (a, b, genesById) =>
      Math.min(...Object.keys(a.transcripts).reduce((acc, geneId) =>
        [...acc, getGeneConstraintSortScore(genesById[geneId] || {})], [])) -
      Math.min(...Object.keys(b.transcripts).reduce((acc, geneId) =>
        [...acc, getGeneConstraintSortScore(genesById[geneId] || {})], [])),
  },
  {
    value: SORT_BY_IN_OMIM,
    text: 'In OMIM',
    comparator: (a, b, genesById) =>
      (genesById[b.mainTranscript.geneId] || { omimPhenotypes: [] }).omimPhenotypes.length - (genesById[a.mainTranscript.geneId] || { omimPhenotypes: [] }).omimPhenotypes.length,
  },
]
const VARIANT_SORT_OPTONS_NO_FAMILY_SORT = VARIANT_SORT_OPTONS.slice(1)

export const VARIANT_SORT_LOOKUP = VARIANT_SORT_OPTONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.comparator,
  }), {},
)

const BASE_VARIANT_SORT_FIELD = {
  name: 'sort',
  component: Dropdown,
  inline: true,
  selection: false,
  fluid: false,
  label: 'Sort By:',
}
export const VARIANT_SORT_FIELD = { ...BASE_VARIANT_SORT_FIELD, options: VARIANT_SORT_OPTONS }
export const VARIANT_SORT_FIELD_NO_FAMILY_SORT = { ...BASE_VARIANT_SORT_FIELD, options: VARIANT_SORT_OPTONS_NO_FAMILY_SORT }
export const VARIANT_HIDE_EXCLUDED_FIELD = {
  name: 'hideExcluded',
  component: InlineToggle,
  label: 'Hide Excluded',
  labelHelp: 'Remove all variants tagged with the "Excluded" tag from the results',
}
export const VARIANT_HIDE_REVIEW_FIELD = {
  name: 'hideReviewOnly',
  component: InlineToggle,
  label: 'Hide Review Only',
  labelHelp: 'Remove all variants tagged with only the "Review" tag from the results',
}
export const VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD = {
  name: 'hideKnownGeneForPhenotype',
  component: InlineToggle,
  label: 'Hide Known Gene For Phenotype',
  labelHelp: 'Remove all variants tagged with the "Known Gene For Phenotype" tag from the results',
}
export const VARIANT_PER_PAGE_FIELD = {
  name: 'recordsPerPage',
  component: Dropdown,
  inline: true,
  selection: false,
  fluid: false,
  label: 'Variants Per Page:',
  options: [{ value: 10 }, { value: 25 }, { value: 50 }, { value: 100 }],
}
export const VARIANT_PAGINATION_FIELD = {
  name: 'page',
  component: Pagination,
  size: 'mini',
  siblingRange: 0,
  firstItem: null,
  lastItem: null,
  format: val => parseInt(val, 10),
}
export const VARIANT_GENE_FIELD = {
  name: 'gene',
  component: BaseSemanticInput,
  inputType: 'Input',
  label: 'Gene',
  inline: true,
}
export const VARIANT_TAGGED_DATE_FIELD = {
  name: 'taggedAfter',
  component: BaseSemanticInput,
  inputType: 'Input',
  label: 'Tagged After',
  type: 'date',
  inline: true,
}

export const PREDICTION_INDICATOR_MAP = {
  D: { color: 'red', value: 'damaging' },
  A: { color: 'red', value: 'disease causing' },
  T: { color: 'green', value: 'tolerated' },
  N: { color: 'green', value: 'polymorphism' },
  P: { color: 'green', value: 'polymorphism' },
  B: { color: 'green', value: 'benign' },
}

export const POLYPHEN_MAP = {
  D: { value: 'probably damaging' },
  P: { color: 'yellow', value: 'possibly damaging' },
}

export const MUTTASTER_MAP = {
  D: { value: 'disease causing' },
}

export const VARIANT_EXPORT_DATA = [
  { header: 'chrom' },
  { header: 'pos' },
  { header: 'ref' },
  { header: 'alt' },
  { header: 'gene', getVal: variant => variant.mainTranscript.geneSymbol },
  { header: 'worst_consequence', getVal: variant => variant.mainTranscript.majorConsequence },
  { header: 'family', getVal: variant => variant.familyGuids[0].split(/_(.+)/)[1] },
  { header: 'tags', getVal: variant => variant.tags.map(tag => tag.name).join('|') },
  { header: 'notes', getVal: variant => variant.notes.map(note => `${note.createdBy}: ${note.note}`).join('|') },
  { header: '1kg_freq', getVal: variant => variant.populations.g1k.af },
  { header: 'exac_freq', getVal: variant => variant.populations.exac.af },
  { header: 'gnomad_genomes_freq', getVal: variant => variant.populations.gnomad_genomes.af },
  { header: 'gnomad_exomes_freq', getVal: variant => variant.populations.gnomad_exomes.af },
  { header: 'topmed_freq', getVal: variant => variant.populations.topmed.af },
  { header: 'cadd', getVal: variant => variant.predictions.cadd },
  { header: 'revel', getVal: variant => variant.predictions.revel },
  { header: 'eigen', getVal: variant => variant.predictions.eigen },
  { header: 'polyphen', getVal: variant => (MUTTASTER_MAP[variant.predictions.polyphen] || PREDICTION_INDICATOR_MAP[variant.predictions.polyphen] || {}).value },
  { header: 'sift', getVal: variant => (PREDICTION_INDICATOR_MAP[variant.predictions.sift] || {}).value },
  { header: 'muttaster', getVal: variant => (MUTTASTER_MAP[variant.predictions.mut_taster] || PREDICTION_INDICATOR_MAP[variant.predictions.mut_taster] || {}).value },
  { header: 'fathmm', getVal: variant => (PREDICTION_INDICATOR_MAP[variant.predictions.fathmm] || {}).value },
  { header: 'rsid', getVal: variant => variant.rsid },
  { header: 'hgvsc', getVal: variant => variant.mainTranscript.hgvsc },
  { header: 'hgvsp', getVal: variant => variant.mainTranscript.hgvsp },
  { header: 'clinvar_clinical_significance', getVal: variant => variant.clinvar.clinicalSignificance },
  { header: 'clinvar_gold_stars', getVal: variant => variant.clinvar.goldStars },
  { header: 'filter', getVal: variant => variant.genotypeFilters },
]

const VARIANT_GENOTYPE_EXPORT_DATA = [
  { header: 'sample_id', getVal: genotype => genotype.sampleId },
  { header: 'num_alt_alleles', getVal: genotype => genotype.numAlt },
  { header: 'ad' },
  { header: 'dp' },
  { header: 'gq' },
  { header: 'ab' },
]

export const getVariantsExportData = (variants) => {
  const maxGenotypes = Math.max(...variants.map(variant => Object.keys(variant.genotypes).length), 0)
  return {
    rawData: variants,
    headers: [...Array(maxGenotypes).keys()].reduce(
      (acc, i) => [...acc, ...VARIANT_GENOTYPE_EXPORT_DATA.map(config => `${config.header}_${i + 1}`)],
      VARIANT_EXPORT_DATA.map(config => config.header),
    ),
    processRow: variant => Object.values(variant.genotypes).reduce(
      (acc, genotype) => [...acc, ...VARIANT_GENOTYPE_EXPORT_DATA.map((config) => {
        return config.getVal ? config.getVal(genotype) : genotype[config.header]
      })],
      VARIANT_EXPORT_DATA.map(config => (config.getVal ? config.getVal(variant) : variant[config.header])),
    ),
  }
}

// Users

export const USER_NAME_FIELDS = [
  {
    name: 'firstName',
    label: 'First Name',
    width: 8,
    inline: true,
  },
  {
    name: 'lastName',
    label: 'Last Name',
    width: 8,
    inline: true,
  },
]

