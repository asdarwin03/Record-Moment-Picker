import express from "express";
import multer from "multer";
import path from "path";

import { getUploadDir } from "../services/storageService.js";
import { getPublicUploadUrl } from "../services/storageService.js";
import { authenticate } from "./auth.routes.js";

const router = express.Router();

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, getUploadDir());
  },
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname);
    const baseName = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9_-]/g, "_");
    cb(null, `${Date.now()}-${baseName || "upload"}${ext}`);
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
      original_filename: req.file.originalname,
      stored_filename: req.file.filename,
      size: req.file.size,
      path: req.file.path,
      audioUrl: getPublicUploadUrl(req.file.filename),
    },
    message: null,
  });
});

export default router;
