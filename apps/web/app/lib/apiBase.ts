/**
 * The API origin, inlined at build time from NEXT_PUBLIC_API_URL. The single definition
 * every request in the web client uses (it was previously repeated in four places).
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
