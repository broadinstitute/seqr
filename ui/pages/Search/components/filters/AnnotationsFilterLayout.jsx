import React from 'react'
import { Form } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import { VEP_GROUP_OTHER } from 'shared/utils/constants'
import { ANNOTATION_GROUPS, HIGH_IMPACT_GROUPS, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS } from '../../constants'

const ANNOTATION_GROUP_INDEX_MAP = ANNOTATION_GROUPS.reduce((acc, { name }, i) => ({ ...acc, [name]: i }), {})

export default fieldComponents => [
  ...[HIGH_IMPACT_GROUPS, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS].map(groups =>
    <Form.Field key={groups[0]} width={3}>
      {groups.map(group =>
        <div key={group}>
          {fieldComponents[ANNOTATION_GROUP_INDEX_MAP[group]]}
          <VerticalSpacer height={20} />
        </div>,
      )}
    </Form.Field>,
  ),
  <Form.Field key={VEP_GROUP_OTHER} width={4}>
    {fieldComponents[ANNOTATION_GROUP_INDEX_MAP[VEP_GROUP_OTHER]]}
  </Form.Field>,
]

