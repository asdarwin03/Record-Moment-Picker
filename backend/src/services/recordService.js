import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import { getDataState, saveDataState } from "./dataStore.js";
import { getPublicUploadUrl, removeStoredFile } from "./storageService.js";

const mockUserId = 1;

seedDemoRecordsIfNeeded();

export function createRecord({ userId, originalFilename, storedFilename, filePath }) {
  const state = getDataState();
  const now = new Date().toISOString();
  const record = {
    record_id: state.nextRecordId,
    id: String(state.nextRecordId),
    user_id: userId,
    name: originalFilename,
    original_filename: originalFilename,
    stored_filename: storedFilename,
    file_path: filePath,
    status: "uploaded",
    result: null,
    error_message: null,
    created_at: now,
    updated_at: now,
    completed_at: null,
  };

  state.nextRecordId += 1;
  state.records.push(record);
  saveDataState();
  return toRecordDetail(record);
}

export function markRecordProcessing(recordId) {
  const record = requireRecord(recordId);
  record.status = "processing";
  record.updated_at = new Date().toISOString();
  saveDataState();
  return toRecordDetail(record);
}

export function completeRecord(recordId, result) {
  const record = requireRecord(recordId);
  const now = new Date().toISOString();
  record.status = "completed";
  record.result = result;
  record.error_message = null;
  record.updated_at = now;
  record.completed_at = now;
  saveDataState();
  return toRecordDetail(record);
}

export function failRecord(recordId, message) {
  const record = requireRecord(recordId);
  record.status = "failed";
  record.error_message = message;
  record.updated_at = new Date().toISOString();
  saveDataState();
  return toRecordDetail(record);
}

export function listRecords(userId) {
  return getDataState().records
    .filter((record) => record.user_id === userId)
    .sort((a, b) => b.record_id - a.record_id)
    .map(toFrontendRecording);
}

export function getRecord(recordId, userId) {
  const record = findRecord(recordId);
  if (!record || record.user_id !== userId) {
    return null;
  }

  return toRecordDetail(record);
}

export function deleteRecord(recordId, userId) {
  const record = findRecord(recordId);
  if (!record || record.user_id !== userId) {
    return false;
  }

  removeStoredFile(record.file_path);
  const state = getDataState();
  state.records = state.records.filter((item) => item.record_id !== record.record_id);
  saveDataState();
  return true;
}

export function updateRecord(recordId, userId, updates) {
  const record = findRecord(recordId);
  if (!record || record.user_id !== userId) {
    return null;
  }

  if (Object.prototype.hasOwnProperty.call(updates, "name")) {
    const nextName = String(updates.name || "").trim();
    if (!nextName) {
      const error = new Error("Record name is required");
      error.statusCode = 400;
      throw error;
    }

    record.name = nextName;
  }

  if (Object.prototype.hasOwnProperty.call(updates, "folderId")) {
    record.folder_id = updates.folderId || undefined;
  }

  if (Object.prototype.hasOwnProperty.call(updates, "isHidden")) {
    record.is_hidden = Boolean(updates.isHidden);
  }

  record.updated_at = new Date().toISOString();
  saveDataState();
  return toRecordDetail(record);
}

export function clearRecordFolder(userId, folderId) {
  let didUpdate = false;
  getDataState().records.forEach((record) => {
    if (record.user_id === userId && record.folder_id === folderId) {
      record.folder_id = undefined;
      record.updated_at = new Date().toISOString();
      didUpdate = true;
    }
  });

  if (didUpdate) {
    saveDataState();
  }
}

export function hideRecords(recordIds, userId) {
  const ids = new Set(recordIds.map((id) => String(id)));
  const updated = [];

  getDataState().records.forEach((record) => {
    if (record.user_id === userId && ids.has(String(record.id))) {
      record.is_hidden = true;
      record.updated_at = new Date().toISOString();
      updated.push(toFrontendRecording(record));
    }
  });

  if (updated.length > 0) {
    saveDataState();
  }

  return updated;
}

export function getRecordStatus(recordId, userId) {
  const record = findRecord(recordId);
  if (!record || record.user_id !== userId) {
    return null;
  }

  return {
    record_id: record.record_id,
    id: record.id,
    status: record.status,
    frontend_status: toFrontendStatus(record.status),
    progress: getProgress(record.status),
    error_message: record.error_message,
  };
}

export function listProcessableRecords() {
  return getDataState().records
    .filter((record) => ["uploaded", "processing"].includes(record.status))
    .filter((record) => record.file_path)
    .map((record) => ({ ...record }));
}

function requireRecord(recordId) {
  const record = findRecord(recordId);
  if (!record) {
    const error = new Error("Record not found");
    error.statusCode = 404;
    throw error;
  }

  return record;
}

function findRecord(recordId) {
  const numericId = Number(recordId);
  const records = getDataState().records;

  if (Number.isInteger(numericId)) {
    const numericRecord = records.find((record) => record.record_id === numericId);
    if (numericRecord) {
      return numericRecord;
    }
  }

  return records.find((record) => record.id === String(recordId));
}

function getProgress(status) {
  const progressByStatus = {
    uploaded: { stage: "uploaded", percentage: 10 },
    processing: { stage: "stt", percentage: 40 },
    completed: { stage: "completed", percentage: 100 },
    failed: { stage: "failed", percentage: 100 },
  };

  return progressByStatus[status] || progressByStatus.uploaded;
}

function toRecordSummary(record) {
  return {
    record_id: record.record_id,
    id: record.id,
    original_filename: record.original_filename,
    name: record.name,
    date: toDateOnly(record.created_at),
    status: record.status,
    frontend_status: toFrontendStatus(record.status),
    created_at: record.created_at,
    completed_at: record.completed_at,
  };
}

function toRecordDetail(record) {
  return {
    ...toRecordSummary(record),
    result: record.result,
    segments: record.result || [],
    recording: toFrontendRecording(record),
    error_message: record.error_message,
  };
}

function toFrontendRecording(record) {
  const recording = {
    id: record.id,
    name: record.name || record.original_filename,
    date: toDateOnly(record.created_at),
    status: toFrontendStatus(record.status),
    segments: record.result || [],
  };

  const audioUrl = getPublicUploadUrl(record.stored_filename);
  if (audioUrl) {
    recording.audioUrl = audioUrl;
  }

  if (record.folder_id) {
    recording.folderId = record.folder_id;
  }

  if (record.is_hidden) {
    recording.isHidden = true;
  }

  return recording;
}

function toFrontendStatus(status) {
  return status === "completed" ? "done" : "waiting";
}

function toDateOnly(value) {
  return new Date(value).toISOString().slice(0, 10);
}

function seedDemoRecordsIfNeeded() {
  const state = getDataState();
  if (state.records.length > 0) {
    return;
  }

  const demoSegments = loadDemoSegments();
  const now = new Date().toISOString();

  const waitingRecord = {
    record_id: state.nextRecordId,
    id: "os",
    user_id: mockUserId,
    name: "운영체제 7강.m4a",
    original_filename: "운영체제 7강.m4a",
    stored_filename: null,
    file_path: null,
    status: "uploaded",
    result: null,
    error_message: null,
    created_at: "2026-03-21T00:00:00.000Z",
    updated_at: now,
    completed_at: null,
  };
  state.nextRecordId += 1;

  const doneRecord = {
    record_id: state.nextRecordId,
    id: "club",
    user_id: mockUserId,
    name: "동아리 회의.m4a",
    original_filename: "동아리 회의.m4a",
    stored_filename: null,
    file_path: null,
    status: "completed",
    result: demoSegments,
    error_message: null,
    created_at: "2026-03-29T00:00:00.000Z",
    updated_at: now,
    completed_at: "2026-03-29T00:00:00.000Z",
  };
  state.nextRecordId += 1;

  state.records.push(waitingRecord, doneRecord);
  saveDataState();
}

function loadDemoSegments() {
  try {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const crossTopicPath = path.resolve(
      __dirname,
      "../../../shared/examples/final-result.cross-topic-evidence.example.json"
    );
    const fallbackPath = path.resolve(__dirname, "../../../shared/examples/final-result.example.json");
    const demoPath = fs.existsSync(crossTopicPath) ? crossTopicPath : fallbackPath;

    return JSON.parse(fs.readFileSync(demoPath, "utf8"));
  } catch (_error) {
    return [];
  }
}
