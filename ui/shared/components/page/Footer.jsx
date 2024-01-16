import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Modal, Header } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getVersion } from 'redux/selectors'
import { FAQ_PATH, PRIVACY_PATH, TOS_PATH } from 'shared/utils/constants'
import { ButtonLink } from '../StyledComponents'

const TableHeaderCell = styled(Table.HeaderCell)`
  border-radius: 0 !important;
  font-weight: normal !important;
  
  &.disabled {
    color: grey !important;
  }
`

const FOOTER_LINKS = [
  { to: FAQ_PATH, content: 'FAQ' },
  { to: PRIVACY_PATH, content: 'Privacy Policy' },
  { to: TOS_PATH, content: 'Terms of Service' },
]

const SEQR_PAPER_URL = 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9903206'
export const SeqrPaperLink =
  ({ content }) => <a target="_blank" rel="noreferrer" href={SEQR_PAPER_URL}>{content || SEQR_PAPER_URL}</a>

SeqrPaperLink.propTypes = {
  content: PropTypes.node,
}

const Footer = React.memo(({ version }) => (
  <Table>
    <Table.Header>
      <Table.Row>
        <TableHeaderCell width={1} />
        <TableHeaderCell collapsing disabled>{`seqr ${version}`}</TableHeaderCell>
        <TableHeaderCell collapsing>
          <Modal
            // eslint-disable-next-line react/jsx-one-expression-per-line
            trigger={<ButtonLink content={<span>Cite <i>seqr</i></span>} />}
            header={<Modal.Header content="For discoveries made using seqr, please cite:" as={Header} size="small" />}
            content={
              <Modal.Content>
                Pais, L., Snow, H., Weisburd, B., Zhang, S., Baxter, S., DiTroia, S., O’Heir, E., England, E.,
                Chao, K., Lemire, G., Osei-Owusu, I., VanNoy, G., Wilson, M., Nguyen, K., Arachchi, H., Phu, W.,
                Solomson, M., Mano, S., O’Leary, M., … O’Donnell-Luria, A.
                <br />
                seqr: a web-based analysis and collaboration tool for rare disease genomics. Human Mutation (2022).
                &nbsp;
                <SeqrPaperLink />
              </Modal.Content>
            }
          />
        </TableHeaderCell>
        {FOOTER_LINKS.map(({ content, ...props }) => (
          <TableHeaderCell key={content} collapsing><Link {...props}>{content}</Link></TableHeaderCell>
        ))}
        <TableHeaderCell>
          For bug reports or feature requests please submit  &nbsp;
          <a href="https://github.com/populationgenomics/seqr/issues">Github Issues</a>
        </TableHeaderCell>
        <TableHeaderCell collapsing textAlign="right">
          If you have questions or feedback, &nbsp;
          <a
            href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;tf=1&amp;to=seqr@populationgenomics.org.au"
            target="_blank"
            rel="noreferrer"
          >
            Contact Us
          </a>
        </TableHeaderCell>
        <TableHeaderCell width={1} />
      </Table.Row>
    </Table.Header>
  </Table>
))

Footer.propTypes = {
  version: PropTypes.string,
}

const mapStateToProps = state => ({
  version: getVersion(state),
})

export default connect(mapStateToProps)(Footer)
