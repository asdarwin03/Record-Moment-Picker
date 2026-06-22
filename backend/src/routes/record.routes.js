import express from "express";
import multer from "multer";

import { createStoredFilename, decodeOriginalFilename } from "../services/filenameService.js";
import {
  createRecord,
  deleteRecord,
  getRecord,
  getRecordStatus,
  hideRecords,
  listRecords,
  prepareRecordRetry,
  updateRecord,
} from "../services/recordService.js";
import { queueRecordProcessing } from "../services/recordProcessingService.js";
import {
  getProcessingOptions,
  parsePipelineSettings,
} from "../services/pipelineSettingsService.js";
import { getUploadDir, removeStoredFile } from "../services/storageService.js";
import { authenticate } from "./auth.routes.js";

const router = express.Router();

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, getUploadDir());
  },
  filename: (_req, file, cb) => {
    cb(null, createStoredFilename(file.originalname, "audio"));
  },
});

const upload = multer({
  storage,
  limits: {
    fileSize: Number(process.env.MAX_UPLOAD_BYTES || 1024 * 1024 * 200),
  },
});

router.get("/", authenticate, (req, res) => {
  res.json({
    success: true,
    data: listRecords(req.user.user_id),
    message: null,
  });
});

router.patch("/bulk/hide", authenticate, (req, res) => {
  const { ids } = req.body;

  if (!Array.isArray(ids)) {
    return res.status(400).json({
      success: false,
      data: null,
      message: "ids must be an array",
    });
  }

  return res.json({
    success: true,
    data: hideRecords(ids, req.user.user_id),
    message: null,
  });
});

router.get("/processing-options", authenticate, (_req, res) => {
  return res.json({
    success: true,
    data: getProcessingOptions(),
    message: null,
  });
});

router.post("/", authenticate, upload.single("file"), (req, res, next) => {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      data: null,
      message: "Audio file is required",
    });
  }

  let pipelineSettings;
  try {
    pipelineSettings = parsePipelineSettings(req.body.pipelineSettings);
  } catch (error) {
    removeStoredFile(req.file.path);
    return next(error);
  }

  const record = createRecord({
    userId: req.user.user_id,
    originalFilename: decodeOriginalFilename(req.file.originalname),
    storedFilename: req.file.filename,
    filePath: req.file.path,
    pipelineSettings,
  });

  queueRecordProcessing(record.record_id, req.file.path, pipelineSettings);

  return res.status(202).json({
    success: true,
    data: {
      record_id: record.record_id,
      id: record.id,
      status: "processing",
      frontend_status: "waiting",
      result: null,
      segments: [],
      recording: {
        ...record.recording,
        status: "waiting",
      },
    },
    message: "Record uploaded and queued for processing",
  });
});

router.get("/:recordId/status", authenticate, (req, res) => {
  const status = getRecordStatus(req.params.recordId, req.user.user_id);

  if (!status) {
    return res.status(404).json({
      success: false,
      data: null,
      message: "Record not found",
    });
  }

  return res.json({
    success: true,
    data: status,
    message: null,
  });
});

router.post("/:recordId/retry", authenticate, (req, res, next) => {
  try {
    const retryRecord = prepareRecordRetry(req.params.recordId, req.user.user_id);

    if (!retryRecord) {
      return res.status(404).json({
        success: false,
        data: null,
        message: "Record not found",
      });
    }

    queueRecordProcessing(
      retryRecord.record_id,
      retryRecord.file_path,
      retryRecord.pipeline_settings
    );

    return res.status(202).json({
      success: true,
      data: {
        ...retryRecord.detail,
        recording: {
          ...retryRecord.detail.recording,
          status: "waiting",
          error_message: null,
        },
      },
      message: "Record queued for retry",
    });
  } catch (error) {
    return next(error);
  }
});

router.patch("/:recordId", authenticate, (req, res, next) => {
  try {
    const record = updateRecord(req.params.recordId, req.user.user_id, req.body);

    if (!record) {
      return res.status(404).json({
        success: false,
        data: null,
        message: "Record not found",
      });
    }

    return res.json({
      success: true,
      data: record,
      message: null,
    });
  } catch (error) {
    return next(error);
  }
});

router.get("/:recordId", authenticate, (req, res) => {
  const record = getRecord(req.params.recordId, req.user.user_id);

  if (!record) {
    return res.status(404).json({
      success: false,
      data: null,
      message: "Record not found",
    });
  }

  return res.json({
    success: true,
    data: record,
    message: null,
  });
});

router.delete("/:recordId", authenticate, (req, res) => {
  const deleted = deleteRecord(req.params.recordId, req.user.user_id);

  if (!deleted) {
    return res.status(404).json({
      success: false,
      data: null,
      message: "Record not found",
    });
  }

  return res.json({
    success: true,
    data: {
      record_id: Number.isNaN(Number(req.params.recordId))
        ? req.params.recordId
        : Number(req.params.recordId),
      id: String(req.params.recordId),
    },
    message: "Record deleted",
  });
});

export default router;
