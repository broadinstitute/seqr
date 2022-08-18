import React from 'react'
import { Button } from 'semantic-ui-react'

import { InlineHeader } from 'shared/components/StyledComponents'
import { CONSENT_CODES } from 'shared/utils/constants'

const Gregor = () => (
  <div>
    <InlineHeader size="medium" content="Download GREGoR Reports for Consent Code:" />
    {CONSENT_CODES.map(
      code => <Button key={code} content={code} secondary icon="download" as="a" href={`/api/report/gregor/${code}`} />,
    )}
  </div>
)

export default Gregor
