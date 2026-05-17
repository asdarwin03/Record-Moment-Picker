import express from "express";
import multer from "multer";

import { createStoredFilename, decodeOriginalFilename } from "../services/filenameService.js";
import { getUploadDir } from "../services/storageService.js";
import { getPublicUploadUrl } from "../services/storageService.js";
import { authenticate } from "./auth.routes.js";

const router = express.Router();

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, getUploadDir());
  },
  filename: (_req, file, cb) => {
    cb(null, createStoredFilename(file.originalname, "upload"));
  },
});

const upload = multer({ storage });

router.post("/", authenticate, upload.single("file"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      data: null,
      message: "File is required",
    });
  }

  return res.status(201).json({
    success: true,
    data: {
      original_filename: decodeOriginalFilename(req.file.originalname),
      stored_filename: req.file.filename,
      size: req.file.size,
      path: req.file.path,
      audioUrl: getPublicUploadUrl(req.file.filename),
    },
    message: null,
  });
});

export default router;
