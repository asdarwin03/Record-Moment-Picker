import fs from "fs/promises";
import os from "os";
import path from "path";
import { execFile } from "child_process";
import { promisify } from "util";

const execFileAsync = promisify(execFile);

const DEFAULT_AUDIO_FILTER = "highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11";

export async function preprocessAudioForAI(inputPath, options = {}) {
  const enabled =
    typeof options.enabled === "boolean"
      ? options.enabled
      : isAudioPreprocessingEnabled(options.env);
  if (!enabled) {
    return originalAudio(inputPath, "disabled");
  }

  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "record-moment-audio-"));
  const outputPath = path.join(tempDir, `${path.parse(inputPath).name || "audio"}-ai.m4a`);
  const ffmpegBinary = envValue("FFMPEG_BINARY", "ffmpeg", options.env);
  const timeoutMs = envNumber("AUDIO_PREPROCESSING_TIMEOUT_MS", 900000, options.env);
  const args = buildAudioPreprocessArgs(inputPath, outputPath, options.env);
  const runner = options.runner || execFileAsync;

  try {
    await runner(ffmpegBinary, args, {
      windowsHide: true,
      timeout: timeoutMs,
      maxBuffer: 1024 * 1024 * 4,
    });

    return {
      audioPath: outputPath,
      cleanup: () => removeDirectory(tempDir),
      usedPreprocessed: true,
      tempDir,
    };
  } catch (error) {
    await removeDirectory(tempDir);
    throw error;
  }
}

export function buildAudioPreprocessArgs(inputPath, outputPath, env = process.env) {
  return [
    "-hide_banner",
    "-loglevel",
    "error",
    "-y",
    "-i",
    inputPath,
    "-vn",
    "-ac",
    "1",
    "-ar",
    "16000",
    "-af",
    envValue("AUDIO_PREPROCESSING_FILTER", DEFAULT_AUDIO_FILTER, env),
    "-c:a",
    "aac",
    "-b:a",
    envValue("AUDIO_PREPROCESSING_AUDIO_BITRATE", "48k", env),
    outputPath,
  ];
}

export function isAudioPreprocessingEnabled(env = process.env) {
  return !["0", "false", "no", "off"].includes(
    envValue("AUDIO_PREPROCESSING_ENABLED", "true", env).trim().toLowerCase()
  );
}

function originalAudio(inputPath, skippedReason) {
  return {
    audioPath: inputPath,
    cleanup: async () => {},
    usedPreprocessed: false,
    skippedReason,
  };
}

function envValue(name, defaultValue, env = process.env) {
  const value = env[name];
  if (value === undefined || value === "") {
    return defaultValue;
  }

  return String(value);
}

function envNumber(name, defaultValue, env = process.env) {
  const value = Number(envValue(name, String(defaultValue), env));
  if (!Number.isFinite(value) || value <= 0) {
    return defaultValue;
  }

  return value;
}

async function removeDirectory(directoryPath) {
  await fs.rm(directoryPath, { recursive: true, force: true });
}
