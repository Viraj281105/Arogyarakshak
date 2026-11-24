// Everything the API accepts (ALLOWED_UPLOAD_EXTENSIONS in apps/api/.../kadi.py): scans and
// photos, PDFs, and plain-text/CSV exports. Text files were previously filtered out of the
// picker although the server accepts them, so the synthetic demo documents could not be chosen.
// Its own module so the case frame can use it without the upload panel's copy.
export const DOCUMENT_ACCEPT = "image/*,application/pdf,.pdf,.txt,text/plain,.csv,text/csv";
