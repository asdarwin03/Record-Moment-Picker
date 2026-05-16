import bcrypt from "bcrypt";
import express from "express";
import jwt from "jsonwebtoken";

const router = express.Router();
const usersByEmail = new Map();
const usersById = new Map();
let nextUserId = 1;

export function authenticate(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    req.user = getMockUser();
    return next();
  }

  const [scheme, token] = authHeader.split(" ");
  if (scheme !== "Bearer" || !token) {
    return res.status(401).json({
      success: false,
      data: null,
      message: "Unauthorized",
    });
  }

  try {
    const payload = jwt.verify(token, getJwtSecret());
    const user = usersById.get(payload.user_id);

    if (!user) {
      return res.status(401).json({
        success: false,
        data: null,
        message: "Unauthorized",
      });
    }

    req.user = toPublicUser(user);
    return next();
  } catch (_error) {
    return res.status(401).json({
      success: false,
      data: null,
      message: "Unauthorized",
    });
  }
}

router.post("/register", async (req, res, next) => {
  try {
    const { email, password, name } = req.body;

    if (!email || !password || !name) {
      return res.status(400).json({
        success: false,
        data: null,
        message: "email, password, name are required",
      });
    }

    if (usersByEmail.has(email)) {
      return res.status(409).json({
        success: false,
        data: null,
        message: "Email already exists",
      });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    const user = {
      user_id: nextUserId,
      email,
      name,
      password_hash: passwordHash,
      created_at: new Date().toISOString(),
    };

    nextUserId += 1;
    usersByEmail.set(email, user);
    usersById.set(user.user_id, user);

    return res.status(201).json({
      success: true,
      data: toPublicUser(user),
      message: null,
    });
  } catch (error) {
    return next(error);
  }
});

router.post("/login", async (req, res, next) => {
  try {
    const { email, password } = req.body;
    const user = usersByEmail.get(email);

    if (!user || !(await bcrypt.compare(password || "", user.password_hash))) {
      return res.status(401).json({
        success: false,
        data: null,
        message: "Invalid email or password",
      });
    }

    const publicUser = toPublicUser(user);
    const accessToken = jwt.sign(publicUser, getJwtSecret(), { expiresIn: "7d" });

    return res.json({
      success: true,
      data: {
        access_token: accessToken,
        user: publicUser,
      },
      message: null,
    });
  } catch (error) {
    return next(error);
  }
});

router.get("/me", authenticate, (req, res) => {
  res.json({
    success: true,
    data: req.user,
    message: null,
  });
});

function getMockUser() {
  return {
    user_id: 1,
    email: "mock@example.com",
    name: "Mock User",
  };
}

function getJwtSecret() {
  return process.env.JWT_SECRET || "dev_secret";
}

function toPublicUser(user) {
  return {
    user_id: user.user_id,
    email: user.email,
    name: user.name,
  };
}

export default router;
