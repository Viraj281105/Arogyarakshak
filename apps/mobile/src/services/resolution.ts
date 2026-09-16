/** Formats a Kadi match score (similarity evidence, not a probability) as a percentage. */
export const formatMatchScore = (score: number | null | undefined): string | null => {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  return `${Math.round(score * 100)}%`;
};
