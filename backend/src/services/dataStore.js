import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.resolve(__dirname, "../../storage");
const dataPath = path.join(dataDir, "data.json");

const defaultState = {
  nextRecordId: 1,
  records: [],
  foldersByUserId: {},
};

const state = loadState();

export function getDataState() {
  return state;
}

export function saveDataState() {
  fs.mkdirSync(dataDir, { recursive: true });
  const tempPath = `${dataPath}.tmp`;
  fs.writeFileSync(tempPath, JSON.stringify(state, null, 2), "utf8");
  fs.renameSync(tempPath, dataPath);
}

function loadState() {
  try {
    if (!fs.existsSync(dataPath)) {
      return structuredClone(defaultState);
    }

    const parsed = JSON.parse(fs.readFileSync(dataPath, "utf8"));
    return {
      ...structuredClone(defaultState),
      ...parsed,
      nextRecordId: Number(parsed.nextRecordId || 1),
      records: Array.isArray(parsed.records) ? parsed.records : [],
      foldersByUserId:
        parsed.foldersByUserId && typeof parsed.foldersByUserId === "object"
          ? parsed.foldersByUserId
          : {},
    };
  } catch (error) {
    console.error("Failed to load backend storage. Starting with empty state.", error);
    return structuredClone(defaultState);
  }
}
