import { getDataState, saveDataState } from "./dataStore.js";

export function listFolders(userId) {
  return [...getUserFolders(userId)];
}

export function createFolder(userId, name) {
  const trimmedName = String(name || "").trim();
  if (!trimmedName) {
    const error = new Error("Folder name is required");
    error.statusCode = 400;
    throw error;
  }

  const folder = {
    id: `folder-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: trimmedName,
  };

  const folders = getUserFolders(userId);
  folders.push(folder);
  saveDataState();

  return folder;
}

export function renameFolder(userId, folderId, name) {
  const trimmedName = String(name || "").trim();
  if (!trimmedName) {
    const error = new Error("Folder name is required");
    error.statusCode = 400;
    throw error;
  }

  const folder = getUserFolders(userId).find((item) => item.id === folderId);
  if (!folder) {
    return null;
  }

  folder.name = trimmedName;
  saveDataState();
  return folder;
}

export function deleteFolder(userId, folderId) {
  const folders = getUserFolders(userId);
  const nextFolders = folders.filter((folder) => folder.id !== folderId);

  if (nextFolders.length === folders.length) {
    return false;
  }

  getDataState().foldersByUserId[String(userId)] = nextFolders;
  saveDataState();
  return true;
}

function getUserFolders(userId) {
  const state = getDataState();
  const key = String(userId);

  if (!Array.isArray(state.foldersByUserId[key])) {
    state.foldersByUserId[key] = [];
  }

  return state.foldersByUserId[key];
}
