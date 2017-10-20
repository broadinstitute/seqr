
const groupFeaturesByPresentAbsent = (features) => {

  //yes means present, no means absent
  const groupedHPOTerms = {
    yes: {},
    no: {},
  }

  features.forEach((hpoTerm) => {
    const d = groupedHPOTerms[hpoTerm.observed]
    if (!d[hpoTerm.category]) {
      d[hpoTerm.category] = []  // init array of features
    }

    d[hpoTerm.category].push(hpoTerm)
  })

  return groupedHPOTerms
}

export default groupFeaturesByPresentAbsent
