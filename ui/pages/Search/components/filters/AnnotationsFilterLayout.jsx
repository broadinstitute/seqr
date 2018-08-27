import React from 'react'
import { Grid } from 'semantic-ui-react'

import {
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_FRAMESHIFT,
  VEP_GROUP_INFRAME,
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_OTHER,
} from 'shared/utils/constants'
import {
  CLINVAR_GROUP,
  HGMD_GROUP,
  ANNOTATION_GROUPS,
} from '../../constants'

const ANNOTATION_GROUP_INDEX_MAP = ANNOTATION_GROUPS.reduce((acc, { name }, i) => ({ ...acc, [name]: i }), {})

const GROUPED_ANNOTATIONS = [
  [CLINVAR_GROUP, HGMD_GROUP],
  [VEP_GROUP_NONSENSE, VEP_GROUP_MISSENSE],
  [VEP_GROUP_ESSENTIAL_SPLICE_SITE, VEP_GROUP_EXTENDED_SPLICE_SITE],
  [VEP_GROUP_FRAMESHIFT, VEP_GROUP_INFRAME, VEP_GROUP_SYNONYMOUS],
  [VEP_GROUP_OTHER],
]

export default fieldComponents => (
  <Grid textAlign="left">
    <Grid.Row columns="equal">
      {GROUPED_ANNOTATIONS.map(groups =>
        <Grid.Column key={groups[0]}>
          {groups.map(group => fieldComponents[ANNOTATION_GROUP_INDEX_MAP[group]])}
        </Grid.Column>,
      )}
    </Grid.Row>
  </Grid>
)
