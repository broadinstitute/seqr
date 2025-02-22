import { PanelAppItem, formatPanelAppItems, moiToMoiInitials, panelAppUrl } from './panelAppUtils'

const moiArray = [['1', 'PanelApp_AU', 'BIALLELIC', 'AR', 'BIALLELIC, autosomal or pseudoautosomal'],
  ['2', 'PanelApp_AU', 'MONOALLELIC', 'AD', 'MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted'],
  ['3', 'PanelApp_AU', 'UNKNOWN', '', 'Unknown'],
  ['4', 'PanelApp_AU', 'MONOALLELIC,BIALLELIC', 'AD,AR', 'BOTH monoallelic and biallelic, autosomal or pseudoautosomal'],
  ['5', 'PanelApp_AU', 'MONOALLELIC', 'AD', 'MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown'],
  ['6', 'PanelApp_AU', 'X_LINKED_RECESSIVE', 'XR', 'X-LINKED: hemizygous mutation in males, biallelic mutations in females'],
  ['7', 'PanelApp_AU', 'OTHER', '', 'Other'],
  ['8', 'PanelApp_AU', 'X_LINKED_RECESSIVE,X_LINKED_DOMINANT', 'XR,XD', 'X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)'],
  ['9', 'PanelApp_AU', 'UNKNOWN', '', 'NULL'],
  ['10', 'PanelApp_AU', 'MONOALLELIC,BIALLELIC', 'AD,AR', 'BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal'],
  ['11', 'PanelApp_AU', 'MITOCHONDRIAL', '', 'MITOCHONDRIAL'],
  ['12', 'PanelApp_AU', 'IMPRINTED_MATERNALY_EXPRESSED', '', 'MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)'],
  ['13', 'PanelApp_AU', 'IMPRINTED_PATERNALY_EXPRESSED', '', 'MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)'],
  ['14', 'PanelApp_UK', 'BIALLELIC', 'AR', 'BIALLELIC, autosomal or pseudoautosomal'],
  ['15', 'PanelApp_UK', 'UNKNOWN', '', 'NULL'],
  ['16', 'PanelApp_UK', 'MONOALLELIC', 'AD', 'MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown'],
  ['17', 'PanelApp_UK', 'MONOALLELIC', 'AD', 'MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted'],
  ['18', 'PanelApp_UK', 'MONOALLELIC,BIALLELIC', 'AD,AR', 'BOTH monoallelic and biallelic, autosomal or pseudoautosomal'],
  ['19', 'PanelApp_UK', 'UNKNOWN', '', 'Unknown'],
  ['20', 'PanelApp_UK', 'X_LINKED_RECESSIVE', 'XR', 'X-LINKED: hemizygous mutation in males, biallelic mutations in females'],
  ['21', 'PanelApp_UK', 'X_LINKED_RECESSIVE,X_LINKED_DOMINANT', 'XR,XD', 'X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)'],
  ['22', 'PanelApp_UK', 'IMPRINTED_MATERNALY_EXPRESSED', '', 'MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)'],
  ['23', 'PanelApp_UK', 'MONOALLELIC,BIALLELIC', 'AD,AR', 'BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal'],
  ['24', 'PanelApp_UK', 'MITOCHONDRIAL', '', 'MITOCHONDRIAL'],
  ['25', 'PanelApp_UK', 'IMPRINTED_PATERNALY_EXPRESSED', '', 'MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)'],
  ['26', 'PanelApp_UK', 'OTHER', '', 'Other'],
  ['27', 'PanelApp_UK', 'UNKNOWN', '', 'Other - please specifiy in evaluation comments'],
  ['28', 'PanelApp_UK', 'UNKNOWN', '', 'Other - please specify in evaluation comments'],
  ['29', 'PanelApp_UK', 'MONOALLELIC', 'AD', 'MONOALLELIC, autosomal or pseudoautosomal'],
  ['30', 'PanelApp_UK', 'IMPRINTED_PATERNALY_EXPRESSED', '', 'MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)'],
  ['31', 'PanelApp_UK', 'X_LINKED_RECESSIVE,X_LINKED_DOMINANT', 'XR,XD', 'X linked: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)']]

describe('Test moiToMoiInitials()', () => {
  test.each(moiArray)('%s| %s: %s', (index, origin, moiType, initials, moi) => {
    expect(moiToMoiInitials(moi)).toEqual(initials.split(',').filter(x => x))
  })

  test('Negative test', () => {
    expect(moiToMoiInitials('some invalid string')).toEqual([])
    expect(moiToMoiInitials(null)).toEqual([])
  })

  test('Test initialsOnly flag', () => {
    expect(moiToMoiInitials(null, true)).toEqual([])
    expect(moiToMoiInitials(null, false)).toEqual([])
    expect(moiToMoiInitials('An unknown string', true)).toEqual([])
    expect(moiToMoiInitials('An unknown string', false)).toEqual(['other'])
    expect(moiToMoiInitials(moiArray[12][4], true)).toEqual([])
    expect(moiToMoiInitials(moiArray[12][4], false)).toEqual(['other'])
    expect(moiToMoiInitials(moiArray[27][4], true)).toEqual([])
    expect(moiToMoiInitials(moiArray[27][4], false)).toEqual(['other'])
  })
})

const panelAppData = [{
  url: 'https://panelapp-aus.org/api/v1/panels/40/genes',
  panel: 40,
  gene: 'SLC2A1',
  result: 'https://panelapp-aus.org/panels/40/gene/SLC2A1',
}, {
  url: 'https://panelapp-aus.org/api/v1/panels/40/genes',
  panel: 40,
  gene: 'SLC1A3',
  result: 'https://panelapp-aus.org/panels/40/gene/SLC1A3',
}, {
  url: 'https://panelapp.genomicsengland.co.uk/api/v1',
  panel: 486,
  gene: 'GRIA2',
  result: 'https://panelapp.genomicsengland.co.uk/panels/486/gene/GRIA2',
}, {
  url: 'https://panelapp.genomicsengland.co.uk/api/v1',
  panel: 486,
  gene: 'KIRREL3',
  result: 'https://panelapp.genomicsengland.co.uk/panels/486/gene/KIRREL3',
}, {
  url: 'https://panelapp.genomicsengland.co.uk/api/v1',
  panel: 486,
  gene: 'ACOX1',
  result: 'https://panelapp.genomicsengland.co.uk/panels/486/gene/ACOX1',
}].map(account => Object.assign(account, { toString() { return this.gene } }))

describe('Test panelAppUrl()', () => {
  test.each(panelAppData)('panelAppUrl for gene: %s', (data) => {
    const { url, panel, gene } = data
    expect(panelAppUrl(url, panel, gene)).toEqual(data.result)
  })
})

describe('Test formatPanelAppItems()', () => {
  test('Test return values', () => {
    let items: PanelAppItem[] | null | undefined

    expect(formatPanelAppItems(items)).toEqual([])

    items = null
    expect(formatPanelAppItems(items)).toEqual([])

    items = [
      {
        pagene: {
          confidenceLevel: 1,
        },
        display: 'Variant A',
      },
      {
        pagene: {
          confidenceLevel: 4,
        },
        display: 'Variant B',
      },
      {
        pagene: {
          confidenceLevel: 4,
        },
        display: 'Variant C',
      },
      {
        pagene: {
          confidenceLevel: 1,
        },
        display: 'Variant D',
      },
    ]
    expect(formatPanelAppItems(items)).toEqual({ red: 'Variant A, Variant D', green: 'Variant B, Variant C' })
  })
})
