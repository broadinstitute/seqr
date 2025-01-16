import { PANEL_APP_CONFIDENCE_LEVELS, AD_MOI, AR_MOI, XD_MOI, XR_MOI, OTHER_MOI } from './constants'

/**
 * Converts a Mode of Inheritance (MOI) string to MOI initials.
 *
 * @param {string | undefined | null} rawMoi - The Mode of Inheritance (MOI) string to convert.
 * @param {boolean} [initialsOnly=true] - A flag to indicate whether to return only the initials (default is true).
 * @returns {string[]} An array of MOI initials or an empty array if `rawMoi` is falsy.
 */
export const moiToMoiInitials = (rawMoi: string | undefined | null, initialsOnly: boolean = true): string[] => {
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

/**
 * Constructs a PanelApp URL based on API URL, panel ID, and gene.
 *
 * @param {string | undefined | null} apiUrl - The API URL.
 * @param {number | undefined | null} panelId - The panel ID.
 * @param {string | undefined | null} gene - The gene.
 * @returns {string} The constructed PanelApp URL, or an empty string if any of the parameters are falsy.
 */
export const panelAppUrl = (
  apiUrl: string | undefined | null,
  panelId: number | undefined | null,
  gene: string | undefined | null,
) => {
  if (!apiUrl || !panelId || !gene) {
    return ''
  }
  const baseUrl = apiUrl.split('/api')[0]

  return `${baseUrl}/panels/${panelId}/gene/${gene}`
}

export type PanelAppItem = {
  pagene?: {
    modeOfInheritance?: string;
    confidenceLevel?: 0 | 1 | 2 | 3 | 4
  }
  display: string
}

/**
 * Formats an array of PanelApp items into a record with confidence levels as keys
 * and concatenated item displays as values.
 *
 * @param {PanelAppItem[] | null | undefined} items - The array of PanelApp items to format.
 * @param {string[] | null | undefined} selectedMOIs - Optional array of selected MOIs for filtering.
 * @returns {Record<string, string> | never[]} A record where keys represent confidence levels and values
 * are concatenated item displays, or an empty array if `items` is falsy.
 */
export const formatPanelAppItems = (
  items: PanelAppItem[] | null | undefined,
  selectedMOIs?: string[] | null
): Record<string, string> | never[] => {
  if (!items) {
    return []
  }

  const hasSelectedMoi = (item: { pagene?: any; display?: string }, selectedMOIs: any[]) => {
    if (!selectedMOIs || selectedMOIs.length === 0) {
      return true
    }
    const initials = moiToMoiInitials(item.pagene?.modeOfInheritance, false)
    return selectedMOIs.some((moi) => initials.includes(moi))
  }

  return items.reduce((acc, item) => {
    if (!hasSelectedMoi(item, selectedMOIs)) {
      return acc
    }
    const color: string = PANEL_APP_CONFIDENCE_LEVELS[item.pagene?.confidenceLevel] || PANEL_APP_CONFIDENCE_LEVELS[0]
    return { ...acc, [color]: [acc[color], item.display].filter(val => val).join(', ') }
  }, {} as Record<string, string>)
}
