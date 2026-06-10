export const accessBoundary = {
  status: 'server-required',
  label: 'Access control requires server-side enforcement',
  description:
    'The React prototype can display access state, but it must not be treated as the security boundary.'
};

export function getAccessState() {
  return accessBoundary;
}
