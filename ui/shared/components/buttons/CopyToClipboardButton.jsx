import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { Loader, Icon } from 'semantic-ui-react'

const CopyToClipboard = React.lazy(() => import('react-copy-to-clipboard'))

const CopyToClipboardButton = ({ children, text }) => {
  const [copied, setCopied] = useState(false)

  return (
    <React.Suspense fallback={<Loader />}>
      <CopyToClipboard
        text={text}
        onCopy={setCopied}
      >
        <span>
          <Icon name="copy" link size="small" />
          {copied && <Icon name="check circle" color="green" size="small" />}
          &nbsp;
          {children || text}
        </span>
      </CopyToClipboard>
    </React.Suspense>
  )
}

CopyToClipboardButton.propTypes = {
  children: PropTypes.node,
  text: PropTypes.string.isRequired,
}

export default CopyToClipboardButton
