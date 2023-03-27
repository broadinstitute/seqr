import { GENOME_VERSION_DISPLAY_LOOKUP, GENOME_VERSION_LOOKUP } from '../../../utils/constants'
import { IntegerInput, RadioGroup } from '../../form/Inputs'

export const ALIGNMENT_TYPE = 'alignment'
export const COVERAGE_TYPE = 'wig'
export const JUNCTION_TYPE = 'spliceJunctions'
export const GCNV_TYPE = 'gcnv'

export const ALIGNMENT_TRACK_OPTIONS = {
  alignmentShading: 'strand',
  format: 'cram',
  showSoftClips: true,
}

export const BAM_TRACK_OPTIONS = {
  indexed: true,
  format: 'bam',
}

export const COVERAGE_TRACK_OPTIONS = {
  format: 'bigwig',
  height: 170,
}

export const JUNCTION_TRACK_OPTIONS = {
  format: 'bed',
  height: 170,
  minUniquelyMappedReads: 0,
  minTotalReads: 1,
  maxFractionMultiMappedReads: 1,
  minSplicedAlignmentOverhang: 0,
  colorBy: 'isAnnotatedJunction',
  labelUniqueReadCount: true,
}

export const GCNV_TRACK_OPTIONS = {
  format: 'gcnv',
  height: 200,
  min: 0,
  max: 5,
  onlyHandleClicksForHighlightedSamples: true,
}

export const TRACK_OPTIONS = {
  [ALIGNMENT_TYPE]: ALIGNMENT_TRACK_OPTIONS,
  [COVERAGE_TYPE]: COVERAGE_TRACK_OPTIONS,
  [JUNCTION_TYPE]: JUNCTION_TRACK_OPTIONS,
  [GCNV_TYPE]: GCNV_TRACK_OPTIONS,
}

export const BUTTON_PROPS = {
  [ALIGNMENT_TYPE]: { icon: 'options', content: 'SHOW READS' },
  [JUNCTION_TYPE]: { icon: { name: 'dna', rotated: 'clockwise' }, content: 'SHOW RNASeq' },
  [GCNV_TYPE]: { icon: 'industry', content: 'SHOW gCNV' },
}

export const DNA_TRACK_TYPE_OPTIONS = [
  { value: ALIGNMENT_TYPE, text: 'Alignment', description: 'BAMs/CRAMs' },
  { value: GCNV_TYPE, text: 'gCNV' },
]

export const RNA_TRACK_TYPE_OPTIONS = [
  { value: JUNCTION_TYPE, text: 'Splice Junctions' },
  { value: COVERAGE_TYPE, text: 'Coverage', description: 'RNASeq coverage' },
]

export const RNA_TRACK_TYPE_LOOKUP = new Set(RNA_TRACK_TYPE_OPTIONS.map(track => track.value))

export const IGV_OPTIONS = {
  loadDefaultGenomes: false,
  showKaryo: false,
  showIdeogram: true,
  showNavigation: true,
  showRuler: true,
  showCenterGuide: true,
  showCursorTrackingGuide: true,
  showCommandBar: true,
}

const BASE_REFERENCE_URL = '/api/igv_genomes'

const REFERENCE_URLS = [
  {
    key: 'fastaURL',
    baseUrl: BASE_REFERENCE_URL,
    path: {
      37: 's3/igv.broadinstitute.org/genomes/seq/hg19/hg19.fasta',
      38: 'gs/gcp-public-data--broad-references/hg38/v0/Homo_sapiens_assembly38.fasta',
    },
  },
  {
    key: 'cytobandURL',
    baseUrl: `${BASE_REFERENCE_URL}/s3`,
    path: {
      37: 'igv.broadinstitute.org/genomes/seq/hg19/cytoBand.txt',
      38: 'igv.org.genomes/hg38/annotations/cytoBandIdeo.txt.gz',
    },
  },
  {
    key: 'aliasURL',
    baseUrl: `${BASE_REFERENCE_URL}/s3/igv.org.genomes`,
    path: {
      37: 'hg19/hg19_alias.tab',
      38: 'hg38/hg38_alias.tab',
    },
  },
]

const REFERENCE_TRACKS = [
  {
    name: 'Gencode v32',
    indexPostfix: 'tbi',
    baseUrl: 'gs://seqr-reference-data',
    path: {
      37: 'GRCh37/gencode/gencode.v32lift37.annotation.sorted.bed.gz',
      38: 'GRCh38/gencode/gencode_v32_knownGene.sorted.txt.gz',
    },
    format: 'refgene',
    order: 1000,
  },
  {
    name: 'Refseq',
    indexPostfix: 'tbi',
    baseUrl: `${BASE_REFERENCE_URL}/s3/igv.org.genomes`,
    path: {
      37: 'hg19/refGene.sorted.txt.gz',
      38: 'hg38/refGene.sorted.txt.gz',
    },
    format: 'refgene',
    visibilityWindow: -1,
    order: 1001,
  },
]

export const REFERENCE_LOOKUP = ['37', '38'].reduce((acc, genome) => ({
  ...acc,
  [genome]: {
    id: GENOME_VERSION_DISPLAY_LOOKUP[GENOME_VERSION_LOOKUP[genome]],
    tracks: REFERENCE_TRACKS.map(({ baseUrl, path, indexPostfix, ...track }) => ({
      url: `${baseUrl}/${path[genome]}`,
      indexURL: indexPostfix ? `${baseUrl}/${path[genome]}.${indexPostfix}` : null,
      ...track,
    })),
    ...REFERENCE_URLS.reduce((acc2, { key, baseUrl, path }) => ({ ...acc2, [key]: `${baseUrl}/${path[genome]}` }), {}),
  },
}), {})

const NORM_GTEX_TRACKS = [
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_muscle.803_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_muscle.803_samples.normalized.junctions.bed.gz',
      },
    ],
    description: 'Highly expressed junctions from all 803 GTEx v3 muscle samples. The junction-spanning read counts are normalized to represent the average spanning read count per-sample (see formula below). Only junctions with rounded normalized spanning read count > 0 are included in this track.\n\n  average_unique_reads_per_muscle_sample = (total_unqiue_reads_in_all_muscle_samples / number_of_muscle_samples)\n per_sample_normalized_read_count = raw_read_count * average_unique_reads_per_muscle_sample / total_unqiue_reads_in_this_sample\n normalized read count for junction = sum(per_sample_normalized_read_counts) / number_of_muscle_samples',
    value: 'GTEx Muscle',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_blood.755_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_blood.755_samples.normalized.junctions.bed.gz',
      },
    ],
    description: 'Highly expressed junctions from all 755 GTEx v3 blood samples.\n The junction-spanning read counts are normalized to represent the average spanning read count per-sample (see formula below). Only junctions with rounded normalized spanning read count > 0 are included in this track.\n \n average_unique_reads_per_blood_sample = (total_unqiue_reads_in_all_blood_samples / number_of_blood_samples)\n per_sample_normalized_read_count = raw_read_count * average_unique_reads_per_blood_sample / total_unqiue_reads_in_this_sample\n normalized read count for junction = sum(per_sample_normalized_read_counts) / number_of_blood_samples',
    value: 'GTEx Blood',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_fibs.504_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_fibs.504_samples.normalized.junctions.bed.gz',
      },
    ],
    description: 'Highly expressed junctions from all 504 GTEx v3 fibroblast samples.\n The junction-spanning read counts are normalized to represent the average spanning read count per-sample (see formula below). Only junctions with rounded normalized spanning read count > 0 are included in this track.\n \n average_unique_reads_per_fibs_sample = (total_unqiue_reads_in_all_fibs_samples / number_of_fibs_samples)\n per_sample_normalized_read_count = raw_read_count * average_unique_reads_per_fibs_sample / total_unqiue_reads_in_this_sample\n normalized read count for junction = sum(per_sample_normalized_read_counts) / number_of_fibs_samples',
    value: 'GTEx Fibs',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_lymphocytes.174_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_lymphocytes.174_samples.normalized.junctions.bed.gz',
      },
    ],
    description: 'Highly expressed junctions from all 174 GTEx v3 lymphocyte samples.\n The junction-spanning read counts are normalized to represent the average spanning read count per-sample (see formula below). Only junctions with rounded normalized spanning read count > 0 are included in this track.\n \n average_unique_reads_per_lymph_sample = (total_unqiue_reads_in_all_lymph_samples / number_of_lymph_samples)\n per_sample_normalized_read_count = raw_read_count * average_unique_reads_per_lymph_sample / total_unqiue_reads_in_this_sample\n normalized read count for junction = sum(per_sample_normalized_read_counts) / number_of_lymph_samples',
    value: 'GTEx Lymph',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_brain_cortex.255_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_brain_cortex.255_samples.normalized.junctions.bed.gz',
      },
    ],
    description: 'Highly expressed junctions from all 255 GTEx v3 brain cortex samples.\n The junction-spanning read counts are normalized to represent the average spanning read count per-sample (see formula below).\n Only junctions with rounded normalized spanning read count > 0 are included in this track.\n \n average_unique_reads_per_cortex_sample = (total_unqiue_reads_in_all_cortex_samples / number_of_cortex_samples)\n per_sample_normalized_read_count = raw_read_count * average_unique_reads_per_cortex_sample / total_unqiue_reads_in_this_sample\n normalized read count for junction = sum(per_sample_normalized_read_counts) / number_of_cortex_samples',
    value: 'GTEx Brain: Cortex',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_frontal_cortex.209_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_frontal_cortex.209_samples.normalized.junctions.bed.gz',
      },
    ],
    description: 'Highly expressed junctions from all 209 GTEx v3 brain frontal cortex samples.\n The junction-spanning read counts are normalized to represent the average spanning read count per-sample (see formula below).\n Only junctions with rounded normalized spanning read count > 0 are included in this track.\n \n average_unique_reads_per_cortex_sample = (total_unqiue_reads_in_all_cortex_samples / number_of_cortex_samples)\n per_sample_normalized_read_count = raw_read_count * average_unique_reads_per_cortex_sample / total_unqiue_reads_in_this_sample\n normalized read count for junction = sum(per_sample_normalized_read_counts) / number_of_cortex_samples',
    value: 'GTEx Brain: Front. Cortex',
  },
]

const AGG_GTEX_TRACKS = [
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_muscle.803_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_muscle.803_samples.junctions.bed.gz',
      }],
    description: 'All splice junctions from all 803 GTEx v3 muscle samples. The junction-spanning read counts and read coverage are summed across all samples.',
    value: 'GTEx Muscle',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_blood.755_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_blood.755_samples.junctions.bed.gz',
      }],
    description: 'All splice junctions from all 755 GTEx v3 blood samples. The junction-spanning read counts and read coverage are summed across all samples.',
    value: 'GTEx Blood',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_fibs.504_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_fibs.504_samples.junctions.bed.gz',
      },
    ],
    description: 'All splice junctions from all 504 GTEx v3 fibroblast samples. The junction-spanning read counts and read coverage are summed across all samples.',
    value: 'GTEx Fibs',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_lymphocytes.174_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_lymphocytes.174_samples.junctions.bed.gz',
      },
    ],
    description: 'All splice junctions from all 174 GTEx v3 lymphocyte samples. The junction-spanning read counts and read coverage are summed across all samples.',
    value: 'GTEx Lymph',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_brain_cortex.255_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_brain_cortex.255_samples.junctions.bed.gz',
      },
    ],
    description: 'All splice junctions from all 255 GTEx v3 cortex samples. The junction-spanning read counts and read coverage are summed across all samples.',
    value: 'GTEx Brain: Cortex',
  },
  {
    data: [
      {
        type: COVERAGE_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_frontal_cortex.209_samples.bigWig',
      },
      {
        type: JUNCTION_TYPE,
        url: 'gs://tgg-viewer/ref/GRCh38/gtex_v8/GTEX_frontal_cortex.209_samples.junctions.bed.gz',
      },
    ],
    description: 'All splice junctions from all 209 GTEx v3 frontal cortex samples. The junction-spanning read counts and read coverage are summed across all samples.',
    value: 'GTEx Brain: Front. Cortex',
  },
]

const MAPPABILITY_TRACKS = [
  {
    type: COVERAGE_TYPE,
    url: 'gs://tgg-viewer/ref/GRCh38/mappability/GRCh38_no_alt_analysis_set_GCA_000001405.15-k36_m2.bw',
    value: '36-mer mappability',
    description: 'Mappability of 36-mers allowing for 2 mismatches. Generated using the same pipeline as the UCSC hg19 mappability tracks.',
  },
  {
    type: COVERAGE_TYPE,
    url: 'gs://tgg-viewer/ref/GRCh38/mappability/GRCh38_no_alt_analysis_set_GCA_000001405.15-k50_m2.bw',
    value: '50-mer mappability',
    description: 'Mappability of 50-mers allowing for 2 mismatches. Generated using the same pipeline as the UCSC hg19 mappability tracks.',
  },
  {
    type: COVERAGE_TYPE,
    url: 'gs://tgg-viewer/ref/GRCh38/mappability/GRCh38_no_alt_analysis_set_GCA_000001405.15-k75_m2.bw',
    value: '75-mer mappability',
    description: 'Mappability of 75-mers allowing for 2 mismatches. Generated using the same pipeline as the UCSC hg19 mappability tracks.',
  },
  {
    type: COVERAGE_TYPE,
    url: 'gs://tgg-viewer/ref/GRCh38/mappability/GRCh38_no_alt_analysis_set_GCA_000001405.15-k100_m2.bw',
    value: '100-mer mappability',
    description: 'Mappability of 100-mers allowing for 2 mismatches. Generated using the same pipeline as the UCSC hg19 mappability tracks.',
  },
  {
    type: 'annotation',
    options: {
      format: 'gtf',
      height: 100,
    },
    url: 'gs://tgg-viewer/ref/GRCh38/segdups/segdups.gtf.gz',
    value: 'SegDups >1000 bases',
    description: 'Duplications of >1000 Bases of Non-RepeatMasked Sequence downloaded from UCSC',
  },
]

const mapGtexTrack = (trackLabel, orderOffset) => (track, i) => ({
  text: track.value,
  description: track.description,
  value: {
    name: `${trackLabel}. ${track.value}`,
    type: 'merged',
    height: 170,
    order: orderOffset + i,
    tracks: track.data.map(({ type, url }) => {
      const idx = url.endsWith('.gz') ? { indexURL: `${url}.tbi` } : {}
      return { type, url, ...TRACK_OPTIONS[type], ...idx }
    }),
  },
})

export const NORM_GTEX_TRACK_OPTIONS = NORM_GTEX_TRACKS.map(mapGtexTrack('Norm', 300))
export const AGG_GTEX_TRACK_OPTIONS = AGG_GTEX_TRACKS.map(mapGtexTrack('Agg', 300 + NORM_GTEX_TRACKS.length))

export const MAPPABILITY_TRACK_OPTIONS = MAPPABILITY_TRACKS.map((track, i) => {
  const idx = track.url.endsWith('.gz') ? { indexURL: `${track.url}.tbi` } : {}
  return {
    text: track.value,
    description: track.description,
    value: {
      url: track.url,
      name: track.value,
      order: 400 + i,
      ...TRACK_OPTIONS[track.type],
      height: 50,
      ...track.options,
      ...idx,
    },
  }
})

export const JUNCTION_VISIBILITY_OPTIONS = [
  { value: 2, text: 'Show only local junctions' },
  { value: 1, text: 'Show semi-local junctions' },
  { value: 0, text: 'Show all junctions' },
]

export const JUNCTION_TRACK_FIELDS = [
  { component: RadioGroup, name: 'minJunctionEndsVisible', options: JUNCTION_VISIBILITY_OPTIONS, grouped: true },
  { component: IntegerInput, name: 'minUniquelyMappedReads', label: 'Min. Uniquely Mapped Reads', min: 0 },
  { component: IntegerInput, name: 'minTotalReads', label: 'Min. Total Reads', min: 0 },
]
