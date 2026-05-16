import express from "express";

import {
  createFolder,
  deleteFolder,
  listFolders,
  renameFolder,
} from "../services/folderService.js";
import { clearRecordFolder } from "../services/recordService.js";
import { authenticate } from "./auth.routes.js";

const router = express.Router();

router.get("/", authenticate, (req, res) => {
  res.json({
    success: true,
    data: listFolders(req.user.user_id),
    message: null,
  });
});

router.post("/", authenticate, (req, res, next) => {
  try {
    const folder = createFolder(req.user.user_id, req.body.name);

    return res.status(201).json({
      success: true,
      data: folder,
      message: null,
    });
  } catch (error) {
    return next(error);
  }
});

router.patch("/:folderId", authenticate, (req, res) => {
  const folder = renameFolder(req.user.user_id, req.params.folderId, req.body.name);

  if (!folder) {
    return res.status(404).json({
      success: false,
      data: null,
      message: "Folder not found",
    });
  }

  return res.json({
    success: true,
    data: folder,
    message: null,
  });
});

router.delete("/:folderId", authenticate, (req, res) => {
  const deleted = deleteFolder(req.user.user_id, req.params.folderId);

  if (!deleted) {
    return res.status(404).json({
      success: false,
      data: null,
      message: "Folder not found",
    });
  }

  clearRecordFolder(req.user.user_id, req.params.folderId);

  return res.json({
    success: true,
    data: {
      id: req.params.folderId,
    },
    message: "Folder deleted",
  });
});

export default router;
