// ==================== Shared Configuration ====================
// Loaded before every other script. Defines the API base URL once so the
// other scripts don't each redeclare it (two top-level `const` declarations
// of the same name across classic scripts is a SyntaxError that silently
// kills the second script).

(function () {
  const PRODUCTION_API = 'https://vaidya-qppb.onrender.com';

  // When the page is served by the backend itself (local development with
  // DEBUG=True), talk to the same origin; otherwise use the deployed API.
  const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);

  window.API_BASE_URL = isLocal ? window.location.origin : PRODUCTION_API;
  window.API_BASE = `${window.API_BASE_URL}/api/v1`;
})();
