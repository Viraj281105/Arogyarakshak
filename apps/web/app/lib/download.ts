/**
 * Hands bytes to the browser as a file download. Shared by the appeal PDF, the DaaviSetu
 * package and the Claim Pack (the same five lines were repeated in each).
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
