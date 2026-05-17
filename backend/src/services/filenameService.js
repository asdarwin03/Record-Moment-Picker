import path from "path";

export function decodeOriginalFilename(originalName) {
  const filename = String(originalName || "audio");

  if (!looksMojibake(filename)) {
    return filename;
  }

  try {
    return Buffer.from(filename, "latin1").toString("utf8");
  } catch (_error) {
    return filename;
  }
}

export function createStoredFilename(originalName, fallbackBaseName = "audio") {
  const decodedName = decodeOriginalFilename(originalName);
  const ext = path.extname(decodedName);
  const baseName = path
    .basename(decodedName, ext)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9_-]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");

  return `${Date.now()}-${baseName || fallbackBaseName}${ext}`;
}

function looksMojibake(value) {
  return /[ÃÂÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]/.test(
    value
  );
}
