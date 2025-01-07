import React from 'react'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { connect } from 'react-redux'
import { getLocusListsWithGenes } from 'redux/selectors'
import { moiToMoiInitials, formatPanelAppItems } from 'shared/utils/panelAppUtils'
import PropTypes from 'prop-types'

const EMPTY_STRING = ''

class PaLocusListSelector extends React.Component {
  static propTypes = {
    locus: PropTypes.object,
    locusList: PropTypes.object,
    onChange: PropTypes.func,
    value: PropTypes.string,
    color: PropTypes.string,
  }

  shouldComponentUpdate(nextProps) {
    const { locusList, locus, onChange } = this.props
    return nextProps.locus.selectedMOIs !== locus.selectedMOIs ||
      nextProps.onChange !== onChange ||
      nextProps.locusList.locusListGuid !== locusList.locusListGuid ||
      (!!locusList.locusListGuid && nextProps.locusList.rawItems !== locusList.rawItems)
  }

  componentDidUpdate(prevProps) {
    const { locus, locusList, onChange, color } = this.props
    const { selectedMOIs } = locus

    if (prevProps.locus.selectedMOIs !== selectedMOIs) {
      const panelAppItems = formatPanelAppItems(
        locusList?.items?.filter((item) => {
          let result = true
          const initials = moiToMoiInitials(item.pagene?.modeOfInheritance, false)
          if (selectedMOIs && selectedMOIs.length > 0) {
            result = selectedMOIs.some(moi => initials.includes(moi))
          }
          return result
        }),
      )

      if (panelAppItems[color]) {
        onChange(panelAppItems[color])
      } else {
        onChange(EMPTY_STRING)
      }
    }
  }

  render() {
    return <BaseSemanticInput {...this.props} />
  }

}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsWithGenes(state)[ownProps.locus.locusListGuid],
})

export default connect(mapStateToProps)(PaLocusListSelector)
