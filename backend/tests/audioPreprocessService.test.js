import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildAudioPreprocessArgs,
  isAudioPreprocessingEnabled,
  preprocessAudioForAI,
} from "../src/services/audioPreprocessService.js";

test("audio preprocessing can be disabled by env", async () => {
  const result = await preprocessAudioForAI("sample.m4a", {
    env: { AUDIO_PREPROCESSING_ENABLED: "false" },
  });

  assert.equal(result.audioPath, "sample.m4a");
  assert.equal(result.usedPreprocessed, false);
  assert.equal(result.skippedReason, "disabled");
});

test("audio preprocessing builds ffmpeg args for compressed STT-friendly output", () => {
  const args = buildAudioPreprocessArgs("input.m4a", "output.m4a", {});

  assert.deepEqual(args, [
    "-hide_banner",
    "-loglevel",
    "error",
    "-y",
    "-i",
    "input.m4a",
    "-vn",
    "-ac",
    "1",
    "-ar",
    "16000",
    "-af",
    "highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11",
    "-c:a",
    "aac",
    "-b:a",
    "48k",
    "output.m4a",
  ]);
});

test("audio preprocessing uses runner and returns temporary AI audio path", async () => {
  const calls = [];

  const result = await preprocessAudioForAI("quiet.m4a", {
    env: {
      AUDIO_PREPROCESSING_ENABLED: "true",
      FFMPEG_BINARY: "custom-ffmpeg",
      AUDIO_PREPROCESSING_TIMEOUT_MS: "12345",
    },
    runner: async (...args) => {
      calls.push(args);
    },
  });

  assert.equal(result.usedPreprocessed, true);
  assert.match(result.audioPath, /quiet-ai\.m4a$/);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "custom-ffmpeg");
  assert.equal(calls[0][2].timeout, 12345);
  assert.equal(calls[0][2].windowsHide, true);

  await result.cleanup();
});

test("audio preprocessing is enabled unless explicitly false", () => {
  assert.equal(isAudioPreprocessingEnabled({}), true);
  assert.equal(isAudioPreprocessingEnabled({ AUDIO_PREPROCESSING_ENABLED: "true" }), true);
  assert.equal(isAudioPreprocessingEnabled({ AUDIO_PREPROCESSING_ENABLED: "false" }), false);
  assert.equal(isAudioPreprocessingEnabled({ AUDIO_PREPROCESSING_ENABLED: "0" }), false);
  assert.equal(isAudioPreprocessingEnabled({ AUDIO_PREPROCESSING_ENABLED: "off" }), false);
});
