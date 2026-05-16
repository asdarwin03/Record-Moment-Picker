import axios from "axios";
import FormData from "form-data";
import fs from "fs";

export async function requestAudioProcessing(audioPath) {
  const aiServerUrl = process.env.AI_SERVER_URL || "http://localhost:8000";
  const form = new FormData();
  form.append("file", fs.createReadStream(audioPath));

  const response = await axios.post(`${aiServerUrl}/process-audio`, form, {
    headers: form.getHeaders(),
    maxBodyLength: Infinity,
    timeout: Number(process.env.AI_REQUEST_TIMEOUT_MS || 300000),
  });

  return unwrapAIResponse(response.data);
}

export async function requestTextProcessing(items) {
  const aiServerUrl = process.env.AI_SERVER_URL || "http://localhost:8000";
  const response = await axios.post(
    `${aiServerUrl}/process-text`,
    { items },
    { timeout: Number(process.env.AI_REQUEST_TIMEOUT_MS || 300000) }
  );

  return unwrapAIResponse(response.data);
}

export async function checkAIHealth() {
  const aiServerUrl = process.env.AI_SERVER_URL || "http://localhost:8000";
  const response = await axios.get(`${aiServerUrl}/health`, {
    timeout: Number(process.env.AI_HEALTH_TIMEOUT_MS || 5000),
  });

  return response.data;
}

function unwrapAIResponse(payload) {
  if (payload?.status === "failed") {
    const error = new Error(payload.message || "AI service failed");
    error.statusCode = 502;
    throw error;
  }

  if (!Array.isArray(payload?.data)) {
    const error = new Error("AI service returned an invalid result");
    error.statusCode = 502;
    throw error;
  }

  return payload.data;
}
