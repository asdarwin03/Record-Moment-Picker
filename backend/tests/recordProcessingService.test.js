import assert from "node:assert/strict";
import { test } from "node:test";

import { queueRecordProcessing } from "../src/services/recordProcessingService.js";

test("failed status is published only after cleanup releases the active record", async () => {
  let releaseCleanup;
  let notifyCleanupStarted;
  let notifyFailed;

  const cleanupStarted = new Promise((resolve) => {
    notifyCleanupStarted = resolve;
  });
  const cleanupReleased = new Promise((resolve) => {
    releaseCleanup = resolve;
  });
  const failed = new Promise((resolve) => {
    notifyFailed = resolve;
  });

  const dependencies = {
    preprocessAudioForAI: async (filePath) => ({
      audioPath: filePath,
      usedPreprocessed: true,
      cleanup: async () => {
        notifyCleanupStarted();
        await cleanupReleased;
      },
    }),
    requestAudioProcessing: async () => {
      throw new Error("AI failed");
    },
    markRecordProcessing: () => {},
    completeRecord: () => {
      assert.fail("failed processing must not complete the record");
    },
    failRecord: (_recordId, message) => {
      notifyFailed(message);
    },
  };

  const pipelineSettings = {
    stt: { preprocessingEnabled: true },
  };

  assert.equal(
    queueRecordProcessing("race-test", "sample.m4a", pipelineSettings, dependencies),
    true
  );
  await cleanupStarted;

  assert.equal(
    queueRecordProcessing("race-test", "sample.m4a", pipelineSettings, dependencies),
    false
  );

  releaseCleanup();
  assert.equal(await failed, "AI failed");

  const retryCompleted = new Promise((resolve) => {
    dependencies.requestAudioProcessing = async () => [];
    dependencies.completeRecord = () => resolve();
  });

  assert.equal(
    queueRecordProcessing("race-test", "sample.m4a", pipelineSettings, dependencies),
    true
  );
  await retryCompleted;
});
