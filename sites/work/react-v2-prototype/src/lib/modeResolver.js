export const STUDY_DEGREES = new Set(['level1', 'level2', 'level3']);

const ALL_MODES = ['learning', 'encyclopedia', 'research'];

export function legalRefinements(degreeId) {
  if (degreeId === 'library') return [];
  return ['learning', 'encyclopedia'];
}

export function resolveMode({
  route,
  source,
  fromDegreeId = null,
  refinement = null,
  prevResolved = 'encyclopedia'
}) {
  if (route?.degreeId === 'library') return 'research';

  if (source === 'mode-tab-refinement') {
    const legal = legalRefinements(route?.degreeId);
    return legal.includes(refinement) ? refinement : prevResolved;
  }

  if (source === 'home-mode-pick') {
    return ALL_MODES.includes(refinement) ? refinement : 'encyclopedia';
  }

  if (source === 'degree-tab' || source === 'degree-tile') return 'learning';

  if (source === 'internal-link') {
    if (fromDegreeId === route?.degreeId) return prevResolved;
    return 'encyclopedia';
  }

  if (source === 'search-result') return 'encyclopedia';

  if (source === 'path-load') return 'encyclopedia';

  return 'encyclopedia';
}
