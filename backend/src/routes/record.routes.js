import express from "express";
import multer from "multer";
import path from "path";

import { requestAudioProcessing } from "../services/aiClient.js";
import {
  completeRecord,
  createRecord,
  deleteRecord,
  failRecord,
  getRecord,
  getRecordStatus,
  hideRecords,
  listRecords,
  markRecordProcessing,
  updateRecord,
} from "../services/recordService.js";
import { getUploadDir } from "../services/storageService.js";
import { authenticate } from "./auth.routes.js";

const router = express.Router();

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, getUploadDir());
  },
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname);
    const baseName = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9_-]/g, "_");
    cb(null, `${Date.now()}-${baseName || "audio"}${ext}`);
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

router.post("/", authenticate, upload.single("file"), async (req, res, next) => {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      data: null,
      message: "Audio file is required",
    });
  }

  const record = createRecord({
    userId: req.user.user_id,
    originalFilename: req.file.originalname,
    storedFilename: req.file.filename,
    filePath: req.file.path,
  });

  try {
    markRecordProcessing(record.record_id);
    const result = await requestAudioProcessing(req.file.path);
    const completedRecord = completeRecord(record.record_id, result);

    return res.status(201).json({
      success: true,
      data: {
        record_id: completedRecord.record_id,
        id: completedRecord.id,
        status: completedRecord.status,
        frontend_status: completedRecord.frontend_status,
        result: completedRecord.result,
        segments: completedRecord.segments,
        recording: completedRecord.recording,
      },
      message: null,
    });
  } catch (error) {
    failRecord(record.record_id, error.message);
    return next(error);
  }
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
