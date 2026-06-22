import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getProcessingOptions,
  parsePipelineSettings,
} from "../src/services/pipelineSettingsService.js";

const env = {
  STT_PROVIDER: "whisper",
  WHISPER_MODEL: "small",
  WHISPER_DEVICE: "cpu",
  WHISPER_COMPUTE_TYPE: "int8",
  STT_MODEL_OPTIONS: "tiny,small,medium",
  LLM_MODEL_OPTIONS: "gpt-4.1-mini,gpt-4.1",
  OPENAI_MODEL: "gpt-4.1-mini",
};

test("processing options use env defaults and allowlists", () => {
  const result = getProcessingOptions(env);

  assert.equal(result.defaults.stt.model, "small");
  assert.deepEqual(result.options.sttModels, ["tiny", "small", "medium"]);
  assert.deepEqual(result.options.llmModels, ["gpt-4.1-mini", "gpt-4.1"]);
});

test("pipeline settings parser accepts valid per-stage models", () => {
  const defaults = getProcessingOptions(env).defaults;
  defaults.refine.model = "gpt-4.1";
  defaults.segmenting.chunkSeconds = 240;

  const result = parsePipelineSettings(JSON.stringify(defaults), env);

  assert.equal(result.refine.model, "gpt-4.1");
  assert.equal(result.segmenting.chunkSeconds, 240);
});

test("pipeline settings parser rejects unsupported models", () => {
  const defaults = getProcessingOptions(env).defaults;
  defaults.reasoning.model = "unknown-model";

  assert.throws(
    () => parsePipelineSettings(JSON.stringify(defaults), env),
    /Reasoning model is not supported/
  );
});
