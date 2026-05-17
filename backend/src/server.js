import path from "path";
import { fileURLToPath } from "url";

import cors from "cors";
import dotenv from "dotenv";
import express from "express";

import aiRoutes from "./routes/ai.routes.js";
import authRoutes from "./routes/auth.routes.js";
import folderRoutes from "./routes/folder.routes.js";
import recordRoutes from "./routes/record.routes.js";
import uploadRoutes from "./routes/upload.routes.js";
import { listFolders } from "./services/folderService.js";
import { listRecords } from "./services/recordService.js";
import { resumePendingRecordProcessing } from "./services/recordProcessingService.js";
import { getUploadDir } from "./services/storageService.js";
import { authenticate } from "./routes/auth.routes.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.resolve(__dirname, "../../.env") });
dotenv.config();

const app = express();
const port = Number(process.env.BACKEND_PORT || 3000);

app.use(cors());
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true }));
app.use("/uploads", express.static(getUploadDir()));

app.get("/health", (_req, res) => {
  res.json({ success: true, data: { status: "ok" }, message: null });
});

app.use("/api/auth", authRoutes);
app.use("/api/records", recordRoutes);
app.use("/api/recordings", recordRoutes);
app.use("/api/folders", folderRoutes);
app.use("/api/upload", uploadRoutes);
app.use("/api/ai", aiRoutes);

app.get("/api/bootstrap", authenticate, (req, res) => {
  res.json({
    success: true,
    data: {
      recordings: listRecords(req.user.user_id),
      folders: listFolders(req.user.user_id),
    },
    message: null,
  });
});

app.use((req, res) => {
  res.status(404).json({
    success: false,
    data: null,
    message: `Route not found: ${req.method} ${req.originalUrl}`,
  });
});

app.use((error, _req, res, _next) => {
  const statusCode = error.statusCode || 500;

  if (process.env.NODE_ENV !== "test") {
    console.error(error);
  }

  res.status(statusCode).json({
    success: false,
    data: null,
    message: error.message || "Internal server error",
  });
});

app.listen(port, () => {
  console.log(`Backend server listening on http://localhost:${port}`);
  const resumedCount = resumePendingRecordProcessing();
  if (resumedCount > 0) {
    console.log(`Resumed ${resumedCount} pending record processing job(s).`);
  }
});
