import { createClient } from "../shared/api-client";
import { API_BASE } from "./apiBase";
import { requestCredentials } from "./session";

/**
 * The shared typed client (packages/api-client, vendored into app/shared/api-client) bound to
 * the web API origin. Only the demo-status fetch (`fetchDemoStatus`, the one status data fetch) uses it so
 * far; the remaining web fetches move over page by page (WS4).
 */
export const api = createClient({ baseUrl: API_BASE, credentials: requestCredentials });
