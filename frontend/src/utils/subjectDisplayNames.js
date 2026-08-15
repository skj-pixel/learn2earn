export function withUniqueSubjectDisplayNames(subjects) {
  const originalNames = new Set(subjects.map((subject) => subject.name))
  const usedNames = new Set()
  const displayNames = new Map()

  ;[...subjects]
    .sort((a, b) => Number(a.id) - Number(b.id))
    .forEach((subject) => {
      let displayName = subject.name
      let suffix = 1
      while (usedNames.has(displayName)) {
        displayName = `${subject.name}-${suffix}`
        suffix += 1
        while (originalNames.has(displayName) || usedNames.has(displayName)) {
          displayName = `${subject.name}-${suffix}`
          suffix += 1
        }
      }
      usedNames.add(displayName)
      displayNames.set(subject.id, displayName)
    })

  return subjects.map((subject) => ({
    ...subject,
    displayName: displayNames.get(subject.id) || subject.name,
  }))
}
