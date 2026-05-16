const foldersByUserId = new Map();

export function listFolders(userId) {
  return getUserFolders(userId);
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
  foldersByUserId.set(userId, folders);

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
  return folder;
}

export function deleteFolder(userId, folderId) {
  const folders = getUserFolders(userId);
  const nextFolders = folders.filter((folder) => folder.id !== folderId);

  if (nextFolders.length === folders.length) {
    return false;
  }

  foldersByUserId.set(userId, nextFolders);
  return true;
}

function getUserFolders(userId) {
  if (!foldersByUserId.has(userId)) {
    foldersByUserId.set(userId, []);
  }

  return foldersByUserId.get(userId);
}
