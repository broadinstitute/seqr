export const moiToMoiInitials = (rawMoi) => {
  if (!rawMoi) {
    return []
  }

  const moi = rawMoi.toUpperCase()

  if (moi.startsWith('MONOALLELIC')) {
    if (moi.includes('PATERNALLY IMPRINTED')) {
      return []
    }
    if (moi.includes('MATERNALLY IMPRINTED')) {
      return []
    }
    return ['AD']
  }
  if (moi.startsWith('X-LINKED') || moi.startsWith('X LINKED')) {
    if (moi.includes('BIALLELIC MUTATIONS')) {
      return ['XR']
    }
    if (moi.includes('MONOALLELIC MUTATIONS')) {
      return ['XR', 'XD']
    }
  }
  if (moi.startsWith('BIALLELIC')) {
    return ['AR']
  }
  if (moi.startsWith('BOTH')) {
    return ['AD', 'AR']
  }

  return []
}

export const panelAppUrl = (apiUrl, panelId, gene) => {
  if (!apiUrl || !panelId || !gene) {
    return ''
  }
  const baseUrl = apiUrl.split('/api')[0]

  return `${baseUrl}/panels/${panelId}/gene/${gene}`
}
