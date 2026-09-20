/**
 * API client for AnalyzeFlow backend.
 *
 * Change API_BASE when the backend is deployed to production.
 * It must point to the root of the versioned API, e.g.
 *   "https://api.analyzeflow.example/api/v1"
 */

// Set this to your deployed backend once it exists, e.g.
//   "https://analyzeflow-api.vercel.app/api/v1"
const PRODUCTION_API_BASE =
  "https://analyzeflow-api-jade.vercel.app/api/v1";
// Local development falls back to the dev server automatically, so nobody has
// to remember to switch this back and forth before committing.
const IS_LOCAL = ["localhost", "127.0.0.1", ""].indexOf(location.hostname) !== -1;
const API_BASE =
  IS_LOCAL || !PRODUCTION_API_BASE
    ? "http://localhost:8000/api/v1"
    : PRODUCTION_API_BASE;

(function () {
  "use strict";

  // --------------- token helpers ---------------

  function getAccessToken() {
    return localStorage.getItem("af_access_token");
  }

  function getRefreshToken() {
    return localStorage.getItem("af_refresh_token");
  }

  function storeTokens(access, refresh) {
    localStorage.setItem("af_access_token", access);
    localStorage.setItem("af_refresh_token", refresh);
  }

  function clearTokens() {
    localStorage.removeItem("af_access_token");
    localStorage.removeItem("af_refresh_token");
    localStorage.removeItem("af_user");
  }

  // --------------- error helper ---------------

  function apiError(body, status) {
    var msg = "Request failed";
    var code = "unknown";
    var details = {};

    if (body && body.error) {
      msg = body.error.message || msg;
      code = body.error.code || code;
      details = body.error.details || details;
    }

    var err = new Error(msg);
    err.code = code;
    err.details = details;
    err.status = status;
    return err;
  }

  // --------------- core request ---------------

  var _refreshing = null; // single in-flight refresh promise

  async function request(method, path, body, auth) {
    var headers = { "Content-Type": "application/json" };
    if (auth !== false) {
      var token = getAccessToken();
      if (token) headers["Authorization"] = "Bearer " + token;
    }

    var opts = { method: method, headers: headers };
    if (body !== undefined) opts.body = JSON.stringify(body);

    var res = await fetch(API_BASE + path, opts);

    // Automatic refresh on 401
    if (res.status === 401 && auth !== false && getRefreshToken()) {
      await doRefresh();
      // Retry once with new token
      headers["Authorization"] = "Bearer " + getAccessToken();
      opts.headers = headers;
      res = await fetch(API_BASE + path, opts);
    }

    if (!res.ok) {
      var errBody;
      try { errBody = await res.json(); } catch (_) { errBody = null; }
      throw apiError(errBody, res.status);
    }

    // 204 No Content
    if (res.status === 204) return null;

    return res.json();
  }

  async function doRefresh() {
    // Deduplicate concurrent refresh calls
    if (_refreshing) return _refreshing;

    _refreshing = (async function () {
      try {
        var res = await fetch(API_BASE + "/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: getRefreshToken() }),
        });

        if (!res.ok) {
          clearTokens();
          throw new Error("Session expired. Please sign in again.");
        }

        var data = await res.json();
        storeTokens(data.access_token, data.refresh_token);
      } catch (e) {
        clearTokens();
        throw e;
      } finally {
        _refreshing = null;
      }
    })();

    return _refreshing;
  }

  // --------------- public API ---------------

  window.API = {
    baseUrl: API_BASE,

    // ---- auth ----
    async register(fullName, email, password) {
      var data = await request("POST", "/auth/register", {
        full_name: fullName,
        email: email,
        password: password,
      }, false);
      storeTokens(data.tokens.access_token, data.tokens.refresh_token);
      localStorage.setItem("af_user", JSON.stringify(data.user));
      return data;
    },

    async login(email, password) {
      var data = await request("POST", "/auth/login", {
        email: email,
        password: password,
      }, false);
      storeTokens(data.tokens.access_token, data.tokens.refresh_token);
      localStorage.setItem("af_user", JSON.stringify(data.user));
      return data;
    },

    logout() {
      clearTokens();
    },

    async me() {
      var data = await request("GET", "/auth/me");
      localStorage.setItem("af_user", JSON.stringify(data));
      return data;
    },

    // ---- lookups ----
    async getLookups() {
      return request("GET", "/lookups", undefined, false);
    },

    // ---- audits ----
    async createAudit(payload) {
      return request("POST", "/audits", payload);
    },

    async getJob(auditId) {
      return request("GET", "/audits/" + auditId + "/job");
    },

    async getReport(auditId) {
      return request("GET", "/audits/" + auditId + "/report");
    },

    async retryAudit(auditId) {
      return request("POST", "/audits/" + auditId + "/retry");
    },

    // Serverless deployments (JOB_RUNNER=request) do the analysis inside this
    // call, because a task started after the response is sent is not
    // guaranteed to run there. Fire it WITHOUT awaiting and poll getJob().
    // On an always-on backend the job has already started and this is a
    // harmless no-op, so it is safe to call either way.
    async runAudit(auditId) {
      return request("POST", "/audits/" + auditId + "/run");
    },

    // ---- stats ----
    async getStats() {
      return request("GET", "/stats", undefined, false);
    },

    // ---- case studies ----
    async getCaseStudies() {
      return request("GET", "/case-studies", undefined, false);
    },

    async getCaseStudy(slug) {
      return request("GET", "/case-studies/" + slug, undefined, false);
    },

    // ---- convenience ----
    isSignedIn() {
      return !!getAccessToken();
    },

    currentUser() {
      var raw = localStorage.getItem("af_user");
      if (!raw) return null;
      try { return JSON.parse(raw); } catch (_) { return null; }
    },
  };
})();
