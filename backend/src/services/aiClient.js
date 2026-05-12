import axios from "axios";
import FormData from "form-data";
import fs from "fs";

export async function requestAudioProcessing(audioPath) {
  const form = new FormData();
  form.append("file", fs.createReadStream(audioPath));

  const response = await axios.post(
    `${process.env.AI_SERVER_URL}/process-audio`,
    form,
    {
      headers: form.getHeaders(),
    }
  );

  return response.data.data;
}