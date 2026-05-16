import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const uploadDir = path.resolve(__dirname, "../../uploads");

export function ensureUploadDir() {
  fs.mkdirSync(uploadDir, { recursive: true });
  return uploadDir;
}

export function getUploadDir() {
  return ensureUploadDir();
}

export function getPublicUploadUrl(storedFilename) {
  if (!storedFilename) {
    return undefined;
  }

  return `/uploads/${encodeURIComponent(storedFilename)}`;
}

export function removeStoredFile(filePath) {
  if (!filePath) {
    return;
  }

  try {
    fs.unlinkSync(filePath);
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }
}
