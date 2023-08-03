import React from 'react'
import { Link } from 'react-router-dom'

import { successStoryTypeDisplay, KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME, REVIEW_TAG_NAME } from 'shared/utils/constants'

const formatIDLink =
  row => <Link to={`/project/${row.project_guid}/family_page/${row.family_guid}`} target="_blank">{row.family_id}</Link>

const formatSuccessStoryTypes =
  row => row.success_story_types && row.success_story_types.map(tag => <div>{successStoryTypeDisplay(tag)}</div>)

const formatDiscoveryTags = row => row.extras_variant_tag_list &&
  <div>{row.extras_variant_tag_list.map(tag => <div><small>{tag}</small></div>)}</div>

export const SUCCESS_STORY_COLUMNS = [
  { name: 'family_id', content: 'Family ID', format: formatIDLink, noFormatExport: true, style: { minWidth: '200px' } },
  { name: 'success_story_types', content: 'Success Story Types', format: formatSuccessStoryTypes, noFormatExport: true, style: { minWidth: '300px' } },
  { name: 'success_story', content: 'Success Story', style: { minWidth: '564px' } },
  { name: 'discovery_tags', content: 'Discovery Tags', format: formatDiscoveryTags, noFormatExport: true, style: { minWidth: '400px' } },
]

export const SUMMARY_PAGE_SAVED_VARIANT_TAGS = [
  'Tier 1 - Novel gene and phenotype',
  'Tier 1 - Novel gene for known phenotype',
  'Tier 1 - Phenotype expansion',
  'Tier 1 - Phenotype not delineated',
  'Tier 1 - Novel mode of inheritance',
  'Tier 1 - Known gene, new phenotype',
  'Tier 2 - Novel gene and phenotype',
  'Tier 2 - Novel gene for known phenotype',
  'Tier 2 - Phenotype expansion',
  'Tier 2 - Phenotype not delineated',
  'Tier 2 - Known gene, new phenotype',
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  REVIEW_TAG_NAME,
  'Send for Sanger validation',
  'Sanger validated',
  'Sanger did not confirm',
  'Confident AR one hit',
  'Analyst high priority',
  'seqr MME (old)',
  'Submit to Clinvar',
  'Share with KOMP',
]
