const DEFAULT_STT_MODELS = ["tiny", "base", "small", "medium", "large-v3", "turbo"];
const DEFAULT_LLM_MODELS = ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"];

export function getProcessingOptions(env = process.env) {
  const defaults = {
    stt: {
      provider: envValue("STT_PROVIDER", "whisper", env),
      model: envValue("WHISPER_MODEL", "base", env),
      device: envValue("WHISPER_DEVICE", "cpu", env),
      computeType: envValue("WHISPER_COMPUTE_TYPE", "int8", env),
      preprocessingEnabled: envBoolean("AUDIO_PREPROCESSING_ENABLED", true, env),
      chunkingEnabled: envBoolean("STT_CHUNKING_ENABLED", true, env),
      chunkSeconds: envNumber("STT_CHUNK_SECONDS", 600, env),
      overlapSeconds: envNumber("STT_CHUNK_OVERLAP_SECONDS", 8, env),
      minDurationSeconds: envNumber("STT_CHUNK_MIN_DURATION_SECONDS", 660, env),
    },
    refine: llmDefaults("LLM_REFINE_MAX_OUTPUT_TOKENS", 4096, env),
    segmenting: {
      ...llmDefaults("LLM_SEGMENT_MAX_OUTPUT_TOKENS", 32768, env),
      chunkSeconds: envNumber("LLM_SEGMENT_CHUNK_SECONDS", 300, env),
      mergeMaxOutputTokens: envNumber("LLM_MERGE_MAX_OUTPUT_TOKENS", 8192, env),
    },
    reasoning: llmDefaults("LLM_REASONING_MAX_OUTPUT_TOKENS", 8192, env),
  };

  return {
    defaults: normalizePipelineSettings(defaults, env),
    options: getCatalog(env),
  };
}

export function normalizePipelineSettings(input, env = process.env) {
  const catalog = getCatalog(env);
  const source = input && typeof input === "object" ? input : {};

  return {
    stt: {
      provider: allowed(source.stt?.provider, catalog.sttProviders, "STT provider"),
      model: allowed(source.stt?.model, catalog.sttModels, "STT model"),
      device: allowed(source.stt?.device, catalog.sttDevices, "STT device"),
      computeType: allowed(
        source.stt?.computeType,
        catalog.sttComputeTypes,
        "STT compute type"
      ),
      preprocessingEnabled: booleanValue(
        source.stt?.preprocessingEnabled,
        "STT preprocessingEnabled"
      ),
      chunkingEnabled: booleanValue(source.stt?.chunkingEnabled, "STT chunkingEnabled"),
      chunkSeconds: numberInRange(source.stt?.chunkSeconds, 30, 3600, "STT chunkSeconds"),
      overlapSeconds: numberInRange(
        source.stt?.overlapSeconds,
        0,
        120,
        "STT overlapSeconds"
      ),
      minDurationSeconds: numberInRange(
        source.stt?.minDurationSeconds,
        30,
        14400,
        "STT minDurationSeconds"
      ),
    },
    refine: normalizeLLMStage(source.refine, catalog.llmModels, "Refine"),
    segmenting: {
      ...normalizeLLMStage(source.segmenting, catalog.llmModels, "Segmenting"),
      chunkSeconds: numberInRange(
        source.segmenting?.chunkSeconds,
        60,
        3600,
        "Segmenting chunkSeconds"
      ),
      mergeMaxOutputTokens: numberInRange(
        source.segmenting?.mergeMaxOutputTokens,
        256,
        65536,
        "Segmenting mergeMaxOutputTokens"
      ),
    },
    reasoning: normalizeLLMStage(source.reasoning, catalog.llmModels, "Reasoning"),
  };
}

export function parsePipelineSettings(value, env = process.env) {
  if (typeof value !== "string" || !value.trim()) {
    return getProcessingOptions(env).defaults;
  }

  try {
    return normalizePipelineSettings(JSON.parse(value), env);
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw badRequest("pipelineSettings must be valid JSON");
    }
    throw error;
  }
}

function getCatalog(env) {
  return {
    sttProviders: envList("STT_PROVIDER_OPTIONS", ["whisper"], env),
    sttModels: envList("STT_MODEL_OPTIONS", DEFAULT_STT_MODELS, env),
    sttDevices: envList("STT_DEVICE_OPTIONS", ["cpu", "cuda"], env),
    sttComputeTypes: ["int8", "float16", "float32"],
    llmModels: envList("LLM_MODEL_OPTIONS", DEFAULT_LLM_MODELS, env),
  };
}

function llmDefaults(tokenName, fallbackTokens, env) {
  return {
    model: envValue("OPENAI_MODEL", "gpt-4.1-mini", env),
    temperature: envNumber("LLM_TEMPERATURE", 0, env),
    maxOutputTokens: envNumber(tokenName, fallbackTokens, env),
  };
}

function normalizeLLMStage(stage, models, label) {
  return {
    model: allowed(stage?.model, models, `${label} model`),
    temperature: numberInRange(stage?.temperature, 0, 2, `${label} temperature`),
    maxOutputTokens: numberInRange(
      stage?.maxOutputTokens,
      256,
      65536,
      `${label} maxOutputTokens`
    ),
  };
}

function allowed(value, choices, label) {
  if (typeof value !== "string" || !choices.includes(value)) {
    throw badRequest(`${label} is not supported`);
  }
  return value;
}

function booleanValue(value, label) {
  if (typeof value !== "boolean") {
    throw badRequest(`${label} must be a boolean`);
  }
  return value;
}

function numberInRange(value, minimum, maximum, label) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < minimum || number > maximum) {
    throw badRequest(`${label} must be between ${minimum} and ${maximum}`);
  }
  return number;
}

function envList(name, defaults, env) {
  const items = String(env[name] || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length > 0 ? items : [...defaults];
}

function envValue(name, fallback, env) {
  return env[name] || fallback;
}

function envNumber(name, fallback, env) {
  const value = Number(env[name]);
  return Number.isFinite(value) ? value : fallback;
}

function envBoolean(name, fallback, env) {
  if (!(name in env)) {
    return fallback;
  }
  return !["0", "false", "no", "off"].includes(String(env[name]).toLowerCase());
}

function badRequest(message) {
  const error = new Error(message);
  error.statusCode = 400;
  return error;
}
