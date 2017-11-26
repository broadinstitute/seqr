
const UNKNOWN_CATEGORY = 'Other'

const CATEGORY_NAMES = {
  'HP:0000119': 'Genitourinary',
  'HP:0000152': 'Head or Neck',
  'HP:0000478': 'Eye',
  'HP:0000598': 'Ear',
  'HP:0000707': 'Nervous System',
  'HP:0000769': 'Breast',
  'HP:0000818': 'Endocrine',
  'HP:0000924': 'Skeletal',
  'HP:0001197': 'Prenatal or birth',
  'HP:0001507': 'Growth Abnormality',
  'HP:0001574': 'Integument',
  'HP:0001608': 'Voice',
  'HP:0001626': 'Cardiovascular',
  'HP:0001871': 'Blood',
  'HP:0001939': 'Metabolism/Homeostasis',
  'HP:0002086': 'Respiratory',
  'HP:0002664': 'Neoplasm',
  'HP:0002715': 'Immune System',
  'HP:0003011': 'Musculature',
  'HP:0003549': 'Connective Tissue',
  'HP:0025031': 'Digestive',
  'HP:0040064': 'Limbs',
  'HP:0045027': 'Thoracic Cavity',
  'HP:0500014': 'Test Result',
  'HP:0025354': 'Cellular Phenotype',
}

export const getNameForCategoryHpoId = categoryHpoId => CATEGORY_NAMES[categoryHpoId] || UNKNOWN_CATEGORY
