/** This file contains sample state to use for tests */

export const USER = {
  date_joined: '2015-02-19T20:22:50.633Z',
  email: 'test@broadinstitute.org',
  first_name: '',
  id: 1,
  is_active: true,
  is_superuser: true,
  last_login: '2017-03-14T17:44:53.403Z',
  last_name: '',
  username: 'test',
}

export const VARIANT = {
  alt: "T",
  mainTranscriptId: 'ENST00000456743',
  chrom: "1",
  clinvar: { clinsig: "", variantId: null },
  familyGuids: ["F011652_1"],
  functionalDataGuids: ['VFD0000002_1248367227_r0390_100', 'VFD0000001_1248367227_r0390_100'],
  genomeVersion: "37",
  geneIds: ['ENSG00000228198'],
  genotypes: {
    NA19675: [{
      ab: 1,
      ad: "0,74",
      alleles: ["T", "T"],
      dp: "74",
      filter: "pass",
      gq: 99,
      numAlt: 2,
      pl: "358,132,0",
      sampleType: "WES",
    }, {
      ab: 1,
      ad: "0,74",
      alleles: ["T", "T"],
      dp: "74",
      filter: "pass",
      gq: 99,
      numAlt: 2,
      pl: "358,132,0",
      sampleType: "WGS",
    }],
    NA19678: {
      ab: 0,
      ad: "77,0",
      alleles: ["TC", "TC"],
      dp: "77",
      filter: "pass",
      gq: 99,
      numAlt: 0,
      pl: "0,232,3036",
    },
    NA19679: {
      ab: 0,
      ad: "71,0",
      alleles: ["TC", "TC"],
      dp: "71",
      filter: "pass",
      gq: 99,
      numAlt: 0,
      pl: "0,213,1918",
    },
  },
  hgmd: {accession: null, class: null},
  liftedOverChrom: "",
  liftedOverGenomeVersion: "38",
  liftedOverPos: "",
  noteGuids: [],
  origAltAlleles: ["T"],
  projectGuid: 'R0237_1000_genomes_demo',
  pos: 248367227,
  populations: {
    callset: { af: 0.03, ac: 7, an: 1032 },
    g1k: { af: 0 },
    exac: { af: 0.0006726888333653661, hemi: null, hom: null },
    gnomad_genomes: { af: null, ac: null, an: null },
    gnomad_exomes: { af: 0.00006505916317651364 },
    topmed: {},
  },
  predictions: { cadd: '27.2' },
  ref: "TC",
  tagGuids: ['VT1708635_1248367227_r0390_100', 'VT1726942_1248367227_r0390_100'],
  transcripts: {
    ENSG00000228198: [
      {
        aminoAcids: "P/X",
        canonical: "YES",
        cdnaPosition: "897",
        cdsPosition: "859",
        codons: "Ccc/cc",
        consequence: "frameshift_variant",
        hgvsc: "ENST00000456743.1:c.862delC",
        hgvsp: "ENSP00000389625.1:p.Leu288SerfsTer10",
        isChosenTranscript: true,
        transcriptId: "ENST00000456743",
      }
    ],
  },
  variantId: "SV0000002_1248367227_r0390_100",
  variantGuid: "SV0000002_1248367227_r0390_100",
  xpos: 1248367227,
}

export const SV_VARIANT = {
  alt: null,
  chrom: "1",
  familyGuids: ["F011652_1"],
  functionalDataGuids: ['VFD0000002_1248367227_r0390_100', 'VFD0000001_1248367227_r0390_100'],
  genomeVersion: "37",
  geneIds: ['ENSG00000228198', 'ENSG00000164458'],
  genotypes: {
    NA19675: {
      cn: 0,
      qs: 57,
      numAlt: -1,
    },
    NA19678: {
      cn: 2,
      numAlt: -1,
    },
    NA19679: {
      cn: 2,
      numAlt: -1,
    },
  },
  liftedOverChrom: "",
  liftedOverGenomeVersion: "38",
  liftedOverPos: "",
  noteGuids: [],
  projectGuid: 'R0237_1000_genomes_demo',
  pos: 248367227,
  end: 248369100,
  populations: {
    sv_callset: { af: 0.03, ac: 7, an: 1032 },
    g1k: {},
    exac: {},
    gnomad_genomes: {},
    gnomad_exomes: {},
    topmed: {},
  },
  predictions: { strvctvre: '0.272' },
  ref: "TC",
  tagGuids: ['VT1708635_1248367227_r0390_100', 'VT1726942_1248367227_r0390_100'],
  transcripts: {
    ENSG00000164458: [
      {
        transcriptId: "ENST00000456744",
      }
    ],
    ENSG00000228198: [
      {
        transcriptId: "ENST00000456743",
      }
    ],
  },
  variantId: "batch_123_DEL",
  variantGuid: "SV0000002_SV48367227_r0390_100",
  xpos: 1248367227,
}

export const GENE = {
  constraints: {
    lof: { constraint: 0.0671997116609769, rank: 8248, totalGenes: 18225 },
    missense: { constraint: -0.7885573790993861, rank: 15052, totalGenes: 18225 },
  },
  phenotypeInfo: { mimPhenotypes: [], orphanetPhenotypes: [] },
  locusLists: [],
  geneId: "ENSG00000228198",
  symbol: "OR2M3",
}

export const LOCUS_LIST_GUID = "LL00132_2017_monogenic_ibd_gen"
export const LOCUS_LIST = {
  canEdit: false,
  createdBy: "cjmoran@mgh.harvard.edu",
  createdDate: "2017-11-03T00:01:51.912Z",
  description: "",
  isPublic: true,
  lastModifiedDate: "2018-05-02T00:01:24.013Z",
  locusListGuid: LOCUS_LIST_GUID,
  name: "2017 Monogenic IBD Gene List",
  numEntries: 60,
  parsedItems: { items:  [{ geneId: 'ENSG00000164458' }], itemMap: { 'TTN': { geneId: 'ENSG00000164458', symbol: 'TTN' } } }
}

const GENE_ID = 'ENSG00000228198'
export const SEARCH_HASH = 'd380ed0fd28c3127d07a64ea2ba907d7'
export const SEARCH = { projectFamilies: [{ projectGuid: 'R0237_1000_genomes_demo', familyGuid: 'F011652_1'}], search: {} }

export const STATE1 = {
  currentProjectGuid: 'R0237_1000_genomes_demo',
  projectsByGuid: {
    R0237_1000_genomes_demo: {
      createdDate: '2016-05-16T05:37:08.634Z',
      deprecatedLastAccessedDate: '2017-03-14T15:15:42.580Z',
      description: '',
      discoveryTags: [],
      isMmeEnabled: true,
      lastModifiedDate: '2017-03-14T17:37:32.712Z',
      mmePrimaryDataOwner: 'PI',
      name: '1000 Genomes Demo',
      projectCategoryGuids: [],
      projectGuid: 'R0237_1000_genomes_demo',
      variantTagTypes: [],
    },
  },
  familiesByGuid: {
    F011652_1: {
      analysisNotes: 'added note',
      analysisStatus: 'Rcpc',
      analysisSummary: '',
      description: '',
      displayName: '1',
      familyGuid: 'F011652_1',
      familyId: '1',
      internalCaseReviewNotes: '',
      internalCaseReviewSummary: '',
      pedigreeImage: '/media/pedigree_images/1_w677Gyf.png',
      projectGuid: 'R0237_1000_genomes_demo',
      analysedBy: [],
      individualGuids: [
        'I021476_na19678',
        'I021474_na19679',
        'I021475_na19675',
      ],
    },
  },
  individualsByGuid: {
    I021474_na19679: {
      affected: 'N',
      caseReviewStatus: 'I',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: null,
      createdDate: '2016-12-05T10:28:21.303Z',
      displayName: '',
      familyGuid: 'F011652_1',
      individualGuid: 'I021474_na19679',
      individualId: 'NA19679',
      lastModifiedDate: '2017-03-14T17:37:34.002Z',
      maternalId: '',
      paternalId: '',
      features: [
        {
          category: 'HP:0001507',
          id: 'HP:0011405',
          label: 'Childhood onset short-limb short stature',
        },
        {
          category: 'HP:0001507',
          id: 'HP:0004325',
          label: 'Decreased body weight',
        },
        {
          category: 'HP:0040064',
          id: 'HP:0009821',
          label: 'Forearm undergrowth',
        },
        {
          category: 'HP:0003011',
          id: 'HP:0001290',
          label: 'Generalized hypotonia',
        },
        {
          category: 'HP:0000707',
          id: 'HP:0001250',
          label: 'Seizures',
        },
        {
          category: 'HP:0000924',
          id: 'HP:0002652',
          label: 'Skeletal dysplasia',
        },
      ],
      sex: 'F',
      sampleGuids: [],
    },
    I021475_na19675: {
      affected: 'A',
      caseReviewStatus: 'I',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: null,
      createdDate: '2016-12-05T10:28:21.303Z',
      displayName: '',
      individualGuid: 'I021475_na19675',
      individualId: 'NA19675',
      lastModifiedDate: '2017-03-14T17:37:33.838Z',
      maternalId: 'NA19679',
      paternalId: 'NA19678',
      absentFeatures: [
        {
          category: 'HP:0001626',
          id: 'HP:0001631',
          label: 'Defect in the atrial septum',
        },
      ],
      features: [
        {
          category: 'HP:0003011',
          id: 'HP:0001324',
          label: 'Muscle weakness',
        },
      ],
      rejectedGenes: [
        {
          comments: '15 genes, lab A, 2013, NGS, negative ',
          gene: 'LGMD panel',
        },
      ],
      sex: 'M',
      sampleGuids: [],
    },
    I021476_na19678: {
      affected: 'N',
      caseReviewStatus: 'E',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: null,
      createdDate: '2016-12-05T10:28:21.303Z',
      displayName: '',
      individualGuid: 'I021476_na19678',
      individualId: 'NA19678',
      lastModifiedDate: '2017-03-14T17:37:33.676Z',
      maternalId: '',
      paternalId: '',
      sex: 'M',
      sampleGuids: [],
    },
  },
  analysisGroupsByGuid: {},
  samplesByGuid: {},
  igvSamplesByGuid: {
    S2310656_wal_mc16200_mc16203: {
      projectGuid: 'R0237_1000_genomes_demo',
      individualGuid: 'I021474_na19679',
      sampleGuid: 'S2310656_wal_mc16200_mc16203',
      filePath: 'gs://seqr-datasets/GRCh37/cmg_sankaran_wes/CMG_MYOSEQ_MC16203.cram',
    },
  },
  rnaSeqDataByIndividual: {
    I021474_na19679: {
      outliers: { ENSG00000228198: [{ isSignificant: true }] },
      tpms: { ENSG00000228198: { tpm: 1.03, geneId: 'ENSG00000228198' } },
    },
  },
  phenotypeGeneScoresByIndividual: {},
  mmeSubmissionsByGuid: {},
  project: {
    createdDate: '2016-05-16T05:37:08.634Z',
    deprecatedLastAccessedDate: '2017-03-14T15:15:42.580Z',
    description: '',
    discoveryTags: [],
    isMmeEnabled: true,
    lastModifiedDate: '2017-03-14T17:37:32.712Z',
    mmePrimaryDataOwner: 'PI',
    name: '1000 Genomes Demo',
    projectCategoryGuids: [],
    projectGuid: 'R0237_1000_genomes_demo',
  },
  user: USER,
  meta: {
    anvilLoadingDelayDate: null,
  },
  caseReviewTableState: {
    familiesFilter: 'ALL',
    familiesSortOrder: 'FAMILY_NAME',
    familiesSortDirection: 1,
    showDetails: true,
  },
  richTextEditorModal: {
    isVisible: true,
    title: 'test title with unicØde',
    formSubmitUrl: 'http://test/',
  },
  pedigreeImageZoomModal: {
    isVisible: true,
    family: {
      familyGuid: 'F011652_1',
      displayName: '1',
      familyId: '1',
    },
  },
  genesById: { 'ENSG00000228198': GENE },
  genesLoading: {},
  savedVariantsByGuid: { SV0000002_1248367227_r0390_100: VARIANT },
  variantTagsByGuid: {
    VT1726942_1248367227_r0390_100: {
      category: "Collaboration", color: "#668FE3", dateSaved: "2018-05-25T21:00:51.260Z", name: "Review",
      tagGuid: "VT1726942_1248367227_r0390_100", user: "hsnow@broadinstitute.org",
      variantGuids: ['SV0000002_1248367227_r0390_100'],
    },
    VT1708635_1248367227_r0390_100: {
      category: "CMG Discovery Tags",
      color: "#44AA60",
      dateSaved: "2018-03-23T19:59:12.262Z",
      name: "Tier 1 - Phenotype not delineated",
      searchHash: "c2edbeae",
      tagGuid: "VT1708635_1248367227_r0390_100",
      user: "hsnow@broadinstitute.org",
      variantGuids: ['SV0000002_1248367227_r0390_100'],
    },
  },
  variantNotesByGuid: {},
  variantFunctionalDataByGuid: {
    VFD0000002_1248367227_r0390_100: { color: "#311B92", dateSaved: "2018-05-24T15:30:04.483Z",
      metadata: "An updated note", metadataTitle: null, name: "Biochemical Function", user: "hsnow@broadinstitute.org",
      variantGuids: ['SV0000002_1248367227_r0390_100'], tagGuid: 'VFD0000002_1248367227_r0390_100' },
    VFD0000001_1248367227_r0390_100: { color: "#880E4F", dateSaved: "2018-05-24T15:34:01.365Z", metadata: "2",
      metadataTitle: "LOD Score", name: "Genome-wide Linkage", user: "hsnow@broadinstitute.org",
      variantGuids: ['SV0000002_1248367227_r0390_100'], tagGuid: 'VFD0000001_1248367227_r0390_100'},
  },
  locusListsByGuid: { [LOCUS_LIST_GUID]: LOCUS_LIST },
  locusListsLoading: {},
  savedVariantsLoading: {},
  savedVariantTableState: {},
  searchesByHash: { [SEARCH_HASH]: SEARCH },
  searchGeneBreakdown: { [SEARCH_HASH]: {[GENE_ID]: { total: 3, families: { F011652_1: 2 }}} },
  searchGeneBreakdownLoading: { isLoading: false },
}

export const STATE_WITH_2_FAMILIES = {
  familiesByGuid: {
    F011652_1: {
      familyGuid: 'F011652_1',
      displayName: '1',
      familyId: '1',
      individualGuids: [
        'I021476_na19678_1',
        'I021474_na19679_1',
        'I021475_na19675_1',
      ],
    },
    F011652_2: {
      familyGuid: 'F011652_2',
      displayName: '2',
      familyId: '2',
      individualGuids: [
        'I021476_na19678_2',
        'I021474_na19679_2',
        'I021475_na19675_2',
      ],
    },
  },
  individualsByGuid: {
    I021476_na19678_1: {
      affected: 'N',
      caseReviewStatus: 'E',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: '2016-12-05T10:28:00.000Z',
      createdDate: '2016-12-05T10:28:00.000Z',
      sex: 'F',
    },
    I021475_na19675_1: {
      affected: 'A',
      caseReviewStatus: 'I',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: '2016-12-05T10:29:00.000Z',
      createdDate: '2016-12-05T10:29:00.000Z',
      sex: 'M',
    },
    I021474_na19679_1: {
      affected: 'N',
      caseReviewStatus: 'I',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: '2016-12-05T10:30:00.000Z',
      createdDate: '2016-12-05T10:30:00.000Z',
      sex: 'M',
    },

    I021476_na19678_2: {
      affected: 'N',
      caseReviewStatus: 'G',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: '2016-12-06T10:28:00.000Z',
      createdDate: '2016-12-06T10:28:00.000Z',
      sex: 'F',
    },
    I021475_na19675_2: {
      affected: 'A',
      caseReviewStatus: 'I',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: '2016-12-06T10:29:00.000Z',
      createdDate: '2016-12-06T10:29:00.000Z',
      sex: 'M',
    },
    I021474_na19679_2: {
      affected: 'N',
      caseReviewStatus: 'I',
      caseReviewStatusLastModifiedBy: null,
      caseReviewStatusLastModifiedDate: '2016-12-06T10:30:00.000Z',
      createdDate: '2016-12-06T10:30:00.000Z',
      sex: 'M',
    },
  },
  caseReviewTableState: {
    familiesFilter: 'ACCEPTED',
    familiesSortOrder: 'FAMILY_NAME',
    familiesSortDirection: -1,
    showDetails: true,
  },
}
