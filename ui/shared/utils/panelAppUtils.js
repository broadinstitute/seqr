export const moiToMoiTypes = (rawMoi) => {
  if (!rawMoi) {
    return 'UNKNOWN'
  }

  const moi = rawMoi.toUpperCase()

  if (moi.startsWith('MONOALLELIC')) {
    if (moi.includes('PATERNALLY IMPRINTED')) {
      return ['IMPRINTED_PATERNALY_EXPRESSED']
    }
    if (moi.includes('MATERNALLY IMPRINTED')) {
      return ['IMPRINTED_MATERNALY_EXPRESSED']
    }
    return ['MONOALLELIC']
  }
  if (moi.startsWith('X-LINKED') || moi.startsWith('X LINKED')) {
    if (moi.includes('BIALLELIC MUTATIONS')) {
      return ['X_LINKED_RECESSIVE']
    }
    if (moi.includes('MONOALLELIC MUTATIONS')) {
      return ['X_LINKED_RECESSIVE', 'X_LINKED_DOMINANT']
    }
  }
  if (moi.startsWith('BIALLELIC')) {
    return ['BIALLELIC']
  }
  if (moi.startsWith('BOTH')) {
    return ['MONOALLELIC', 'BIALLELIC']
  }
  if (moi.startsWith('MITOCHONDRIAL')) {
    return ['MITOCHONDRIAL']
  }
  if (moi.startsWith('OTHER')) {
    if (moi.includes('EVALUATION COMMENTS')) {
      return ['UNKNOWN']
    }
    return ['OTHER']
  }
  if (moi.startsWith('UNKNOWN')) {
    return ['UNKNOWN']
  }

  return ['OTHER']
}

export const panelAppUrl = (apiUrl, panelId, gene) => {
  const baseUrl = apiUrl.split('/api')[0]

  return `${baseUrl}/panels/${panelId}/gene/${gene}`
}
