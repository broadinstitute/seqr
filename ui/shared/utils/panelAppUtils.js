import { PANEL_APP_CONFIDENCE_LEVELS, AD_MOI, AR_MOI, XD_MOI, XR_MOI, OTHER_MOI } from 'shared/utils/constants'

export const moiToMoiInitials = (rawMoi, initialsOnly = true) => {
  if (!rawMoi) {
    return []
  }

  const moi = rawMoi.toUpperCase()

  if (moi.startsWith('MONOALLELIC')) {
    if (moi.includes('PATERNALLY IMPRINTED')) {
      return initialsOnly ? [] : [OTHER_MOI]
    }
    if (moi.includes('MATERNALLY IMPRINTED')) {
      return initialsOnly ? [] : [OTHER_MOI]
    }
    return [AD_MOI]
  }
  if (moi.startsWith('X-LINKED') || moi.startsWith('X LINKED')) {
    if (moi.includes('BIALLELIC MUTATIONS')) {
      return [XR_MOI]
    }
    if (moi.includes('MONOALLELIC MUTATIONS')) {
      return [XR_MOI, XD_MOI]
    }
  }
  if (moi.startsWith('BIALLELIC')) {
    return [AR_MOI]
  }
  if (moi.startsWith('BOTH')) {
    return [AD_MOI, AR_MOI]
  }

  return initialsOnly ? [] : [OTHER_MOI]
}

export const panelAppUrl = (apiUrl, panelId, gene) => {
  if (!apiUrl || !panelId || !gene) {
    return ''
  }
  const baseUrl = apiUrl.split('/api')[0]

  return `${baseUrl}/panels/${panelId}/gene/${gene}`
}

export const formatPanelAppItems = (items) => {
  if (!items) {
    return []
  }
  return items.reduce((acc, item) => {
    const color = PANEL_APP_CONFIDENCE_LEVELS[item.pagene?.confidenceLevel] || PANEL_APP_CONFIDENCE_LEVELS[0]
    return { ...acc, [color]: [acc[color], item.display].filter(val => val).join(', ') }
  }, {})
}
