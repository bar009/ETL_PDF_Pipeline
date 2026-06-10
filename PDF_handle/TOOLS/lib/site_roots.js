"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const SITE_ROOTS_CONFIG_PATH = path.join(ROOT, "sites", "site_roots.json");

const DEFAULT_SITE_ROOTS_CONFIG = {
  live_site_root: "sites/live/v0.4-current",
  legacy_live_site_root: "0.3",
  work_site_root: "sites/work/v0.4",
  legacy_work_site_root: "0.3-copy",
  sandbox_sites_root: "sandbox_sites",
  published_sites_root: "published_sites",
  legacy_sites_archive_root: "archive/legacy_sites",
};

function loadSiteRootsConfig() {
  if (!fs.existsSync(SITE_ROOTS_CONFIG_PATH)) {
    return { ...DEFAULT_SITE_ROOTS_CONFIG };
  }

  const raw = JSON.parse(fs.readFileSync(SITE_ROOTS_CONFIG_PATH, "utf8"));
  const merged = { ...DEFAULT_SITE_ROOTS_CONFIG };
  for (const [key, value] of Object.entries(raw || {})) {
    if (typeof value === "string" && value.trim()) {
      merged[key] = value.trim();
    }
  }
  return merged;
}

function resolveWorkspacePath(targetPath) {
  if (!targetPath) {
    return ROOT;
  }
  return path.isAbsolute(targetPath) ? path.resolve(targetPath) : path.resolve(ROOT, targetPath);
}

function getConfiguredPath(key) {
  const config = loadSiteRootsConfig();
  return resolveWorkspacePath(config[key]);
}

function looksLikeSiteRoot(siteRoot) {
  const dataDir = path.join(siteRoot, "data");
  return fs.existsSync(dataDir) && fs.existsSync(path.join(dataDir, "content.schema.json"));
}

function looksLikeRuntimeSiteRoot(siteRoot) {
  return looksLikeSiteRoot(siteRoot)
    && fs.existsSync(path.join(siteRoot, "js"))
    && fs.existsSync(path.join(siteRoot, "css"))
    && fs.existsSync(path.join(siteRoot, "index.html"));
}

function requireConfiguredSiteRoot(primaryKey, options = {}) {
  const { requireRuntimeAssets = false } = options;
  const preferred = getConfiguredPath(primaryKey);
  const predicate = requireRuntimeAssets ? looksLikeRuntimeSiteRoot : looksLikeSiteRoot;
  if (predicate(preferred)) {
    return preferred;
  }
  throw new Error(`Configured ${primaryKey} is unavailable or invalid: ${preferred}`);
}

function getLiveSiteRoot(options = {}) {
  return requireConfiguredSiteRoot("live_site_root", options);
}

function getWorkSiteRoot(options = {}) {
  return requireConfiguredSiteRoot("work_site_root", options);
}

function getSandboxSitesRoot() {
  return getConfiguredPath("sandbox_sites_root");
}

function getPublishedSitesRoot() {
  return getConfiguredPath("published_sites_root");
}

function getLegacySitesArchiveRoot() {
  return getConfiguredPath("legacy_sites_archive_root");
}

function inferReleaseLine(siteRoot) {
  const name = path.basename(String(siteRoot || ""));
  const match = name.match(/v?(\d+\.\d+(?:\.\d+)?)/i);
  return match ? match[1] : "site";
}

function getReleaseLineSlug(siteRoot) {
  return inferReleaseLine(siteRoot).replace(/\./g, "_");
}

function sanitizeNameSegment(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9.-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function getResolvedReleaseId({ releaseId, sourceSiteRoot } = {}) {
  if (typeof releaseId === "string" && releaseId.trim()) {
    const explicit = releaseId.trim();
    const match = explicit.match(/^v?(\d+\.\d+(?:\.\d+)?)/i);
    return match ? match[1] : sanitizeNameSegment(explicit);
  }

  return inferReleaseLine(sourceSiteRoot || getLiveSiteRoot());
}

function getReleaseIdSlug({ releaseId, sourceSiteRoot } = {}) {
  return getResolvedReleaseId({ releaseId, sourceSiteRoot }).replace(/\./g, "_");
}

function getLocalDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildPublishedSnapshotName({ releaseId, sourceSiteRoot, label = "live", qualifier = "", suffix = "" } = {}) {
  const resolvedReleaseId = getResolvedReleaseId({ releaseId, sourceSiteRoot });
  const resolvedLabel = sanitizeNameSegment(label) || "live";
  const resolvedQualifier = sanitizeNameSegment(qualifier || suffix);
  const qualifierPart = resolvedQualifier ? `-${resolvedQualifier}` : "";
  return `${resolvedReleaseId}-${resolvedLabel}-${getLocalDateString()}${qualifierPart}`;
}

function getDatedPublishedSiteRoot(options = {}) {
  return path.join(getPublishedSitesRoot(), buildPublishedSnapshotName(options));
}

module.exports = {
  ROOT,
  loadSiteRootsConfig,
  resolveWorkspacePath,
  looksLikeSiteRoot,
  looksLikeRuntimeSiteRoot,
  getLiveSiteRoot,
  getWorkSiteRoot,
  getSandboxSitesRoot,
  getPublishedSitesRoot,
  getLegacySitesArchiveRoot,
  inferReleaseLine,
  getReleaseLineSlug,
  getResolvedReleaseId,
  getReleaseIdSlug,
  buildPublishedSnapshotName,
  getDatedPublishedSiteRoot,
};
