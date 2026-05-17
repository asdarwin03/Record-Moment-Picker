import { requestAudioProcessing } from "./aiClient.js";
import {
  completeRecord,
  failRecord,
  listProcessableRecords,
  markRecordProcessing,
} from "./recordService.js";

const activeRecordIds = new Set();

export function queueRecordProcessing(recordId, filePath) {
  if (activeRecordIds.has(String(recordId))) {
    return;
  }

  activeRecordIds.add(String(recordId));
  markRecordProcessing(recordId);

  setImmediate(async () => {
    try {
      const result = await requestAudioProcessing(filePath);
      completeRecord(recordId, result);
    } catch (error) {
      failRecord(recordId, error.message);
    } finally {
      activeRecordIds.delete(String(recordId));
    }
  });
}

export function resumePendingRecordProcessing() {
  const records = listProcessableRecords();

  records.forEach((record) => {
    queueRecordProcessing(record.record_id, record.file_path);
  });

  return records.length;
}
