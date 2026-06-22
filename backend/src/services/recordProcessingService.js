import { preprocessAudioForAI } from "./audioPreprocessService.js";
import { requestAudioProcessing } from "./aiClient.js";
import { getProcessingOptions } from "./pipelineSettingsService.js";
import {
  completeRecord,
  failRecord,
  listProcessableRecords,
  markRecordProcessing,
} from "./recordService.js";

const activeRecordIds = new Set();

const defaultDependencies = {
  preprocessAudioForAI,
  requestAudioProcessing,
  completeRecord,
  failRecord,
  markRecordProcessing,
};

export function queueRecordProcessing(
  recordId,
  filePath,
  pipelineSettings,
  dependencyOverrides = {}
) {
  const dependencies = {
    ...defaultDependencies,
    ...dependencyOverrides,
  };
  const activeRecordId = String(recordId);
  const runtimeSettings = pipelineSettings || getProcessingOptions().defaults;

  if (activeRecordIds.has(activeRecordId)) {
    return false;
  }

  activeRecordIds.add(activeRecordId);

  try {
    dependencies.markRecordProcessing(recordId);
  } catch (error) {
    activeRecordIds.delete(activeRecordId);
    throw error;
  }

  setImmediate(async () => {
    let preparedAudio = {
      audioPath: filePath,
      cleanup: async () => {},
      usedPreprocessed: false,
    };
    let processingError = null;
    let result;

    try {
      try {
        preparedAudio = await dependencies.preprocessAudioForAI(filePath, {
          enabled: runtimeSettings.stt.preprocessingEnabled,
        });
        if (preparedAudio.usedPreprocessed) {
          console.log(
            `[Backend][record:${recordId}] audio_preprocessing_completed path=${preparedAudio.audioPath}`
          );
        } else {
          console.log(
            `[Backend][record:${recordId}] audio_preprocessing_skipped reason=${preparedAudio.skippedReason}`
          );
        }
      } catch (error) {
        console.warn(
          `[Backend][record:${recordId}] audio_preprocessing_failed fallback=original error=${error.message}`
        );
        preparedAudio = {
          audioPath: filePath,
          cleanup: async () => {},
          usedPreprocessed: false,
        };
      }

      result = await dependencies.requestAudioProcessing(
        preparedAudio.audioPath,
        runtimeSettings
      );
    } catch (error) {
      processingError = error;
    } finally {
      try {
        await preparedAudio.cleanup();
      } catch (error) {
        console.warn(
          `[Backend][record:${recordId}] audio_preprocessing_cleanup_failed error=${error.message}`
        );
      }
      activeRecordIds.delete(activeRecordId);
    }

    if (processingError) {
      dependencies.failRecord(recordId, processingError.message);
    } else {
      dependencies.completeRecord(recordId, result);
    }
  });

  return true;
}

export function resumePendingRecordProcessing() {
  const records = listProcessableRecords();

  records.forEach((record) => {
    queueRecordProcessing(
      record.record_id,
      record.file_path,
      record.pipeline_settings
    );
  });

  return records.length;
}
