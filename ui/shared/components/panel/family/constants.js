export const ALIGNMENT_TYPE = 'alignment'
export const COVERAGE_TYPE = 'wig'
export const JUNCTION_TYPE = 'spliceJunctions'
export const GCNV_TYPE = 'gcnv'

const BASE_REFERENCE_URL = '/api/igv_genomes'

export const REFERENCE_URLS = [
  {
    key: 'fastaURL',
    baseUrl: `${BASE_REFERENCE_URL}/broadinstitute.org/genomes/seq`,
    path: {
      37: 'hg19/hg19.fasta',
      38: 'hg38/hg38.fa',
    },
  },
  {
    key: 'cytobandURL',
    baseUrl: BASE_REFERENCE_URL,
    path: {
      37: 'broadinstitute.org/genomes/seq/hg19/cytoBand.txt',
      38: 'org.genomes/hg38/annotations/cytoBandIdeo.txt.gz',
    },
  },
  {
    key: 'aliasURL',
    baseUrl: `${BASE_REFERENCE_URL}/org.genomes`,
    path: {
      37: 'hg19/hg19_alias.tab',
      38: 'hg38/hg38_alias.tab',
    },
  },
]

export const REFERENCE_TRACKS = [
  {
    name: 'Gencode v32',
    indexPostfix: 'tbi',
    baseUrl: 'https://storage.googleapis.com/seqr-reference-data',
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
    baseUrl: `${BASE_REFERENCE_URL}/org.genomes`,
    path: {
      37: 'hg19/refGene.sorted.txt.gz',
      38: 'hg38/refGene.sorted.txt.gz',
    },
    format: 'refgene',
    visibilityWindow: -1,
    order: 1001,
  },
]

export const GTEX_TRACKS = [
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
    value: 'Norm. GTEx Muscle',
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
    value: 'Norm. GTEx Blood',
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
    value: 'Norm. GTEx Fibs',
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
    value: 'Norm. GTEx Lymph',
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
    value: 'Norm. GTEx Brain: Cortex',
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
    value: 'Norm. GTEx Brain: Front. Cortex',
  },
]

export const MAPPABILITY_TRACKS = [
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
