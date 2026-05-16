import express from "express";

import { checkAIHealth, requestTextProcessing } from "../services/aiClient.js";

const router = express.Router();

router.get("/health", async (_req, res, next) => {
  try {
    const health = await checkAIHealth();

    return res.json({
      success: true,
      data: health,
      message: null,
    });
  } catch (error) {
    return next(error);
  }
});

router.post("/process-text", async (req, res, next) => {
  try {
    const { items } = req.body;

    if (!Array.isArray(items)) {
      return res.status(400).json({
        success: false,
        data: null,
        message: "items must be an array",
      });
    }

    const result = await requestTextProcessing(items);

    return res.json({
      success: true,
      data: result,
      message: null,
    });
  } catch (error) {
    return next(error);
  }
});

export default router;
