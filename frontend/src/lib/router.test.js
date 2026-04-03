import assert from "node:assert/strict";
import test from "node:test";

import { parseHash, buildHash } from "./router.js";

// ── parseHash ──

test("parseHash returns empty object for empty hash", () => {
  assert.deepEqual(parseHash(""), {});
  assert.deepEqual(parseHash("#"), {});
  assert.deepEqual(parseHash("#/"), {});
});

test("parseHash extracts experiment ID from simple hash", () => {
  assert.deepEqual(parseHash("#/exp_001"), {
    experimentId: "exp_001",
    view: "overview",
  });
});

test("parseHash extracts run detail with config and dataset", () => {
  assert.deepEqual(parseHash("#/exp_001/run/gpt-4o/iris"), {
    experimentId: "exp_001",
    view: "run",
    config: "gpt-4o",
    dataset: "iris",
  });
});

test("parseHash extracts artifact detail", () => {
  assert.deepEqual(parseHash("#/exp_001/artifact/art_123"), {
    experimentId: "exp_001",
    view: "artifact",
    artifactId: "art_123",
  });
});

test("parseHash extracts artifacts section with sub-view", () => {
  assert.deepEqual(parseHash("#/exp_001/artifacts/compare"), {
    experimentId: "exp_001",
    view: "artifacts",
    subView: "compare",
  });
});

test("parseHash defaults artifacts sub-view to gallery", () => {
  assert.deepEqual(parseHash("#/exp_001/artifacts"), {
    experimentId: "exp_001",
    view: "artifacts",
    subView: "gallery",
  });
});

test("parseHash decodes URI-encoded segments", () => {
  assert.deepEqual(parseHash("#/exp%20001/run/gpt-4o/my%20dataset"), {
    experimentId: "exp 001",
    view: "run",
    config: "gpt-4o",
    dataset: "my dataset",
  });
});

// ── buildHash ──

test("buildHash returns empty string when no experiment selected", () => {
  assert.equal(
    buildHash({ experimentId: "", selectedRun: null, selectedArtifact: null, activeSection: "overview", artifactSubView: "gallery" }),
    "",
  );
});

test("buildHash returns experiment ID for overview", () => {
  assert.equal(
    buildHash({ experimentId: "exp_001", selectedRun: null, selectedArtifact: null, activeSection: "overview", artifactSubView: "gallery" }),
    "exp_001",
  );
});

test("buildHash encodes run detail path", () => {
  assert.equal(
    buildHash({
      experimentId: "exp_001",
      selectedRun: { config: "gpt-4o", dataset: "iris" },
      selectedArtifact: null,
      activeSection: "overview",
      artifactSubView: "gallery",
    }),
    "exp_001/run/gpt-4o/iris",
  );
});

test("buildHash encodes artifact detail path", () => {
  assert.equal(
    buildHash({
      experimentId: "exp_001",
      selectedRun: null,
      selectedArtifact: { artifact_id: "art_123" },
      activeSection: "overview",
      artifactSubView: "gallery",
    }),
    "exp_001/artifact/art_123",
  );
});

test("buildHash encodes artifacts section with sub-view", () => {
  assert.equal(
    buildHash({
      experimentId: "exp_001",
      selectedRun: null,
      selectedArtifact: null,
      activeSection: "artifacts",
      artifactSubView: "code",
    }),
    "exp_001/artifacts/code",
  );
});

test("buildHash round-trips with parseHash", () => {
  const state = {
    experimentId: "exp_001",
    selectedRun: { config: "claude-3", dataset: "titanic_survival" },
    selectedArtifact: null,
    activeSection: "overview",
    artifactSubView: "gallery",
  };
  const hash = buildHash(state);
  const parsed = parseHash(`#/${hash}`);
  assert.equal(parsed.experimentId, "exp_001");
  assert.equal(parsed.view, "run");
  assert.equal(parsed.config, "claude-3");
  assert.equal(parsed.dataset, "titanic_survival");
});
