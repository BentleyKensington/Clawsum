import bcrypt from "bcryptjs";
import { storage } from "./storage";

/** Family save: Gmail + a short play@ alias. Same password, same progress. */
export async function seedBossLogin(): Promise<void> {
  const primary = (process.env.DINOCRUSHBOSS_EMAIL || "dinocrushboss@gmail.com").trim().toLowerCase();
  const easy = (process.env.DINOCRUSHBOSS_PLAY_EMAIL || "play@dinocrushboss.com").trim().toLowerCase();
  const typed = "dincrushboss@gmail.com";
  const password = process.env.DINOCRUSHBOSS_PLAY_PASSWORD || "DinoCrush";
  const aliases = [...new Set([easy, typed, primary].filter(Boolean))];

  try {
    let user = await storage.getUserByUsername(primary);
    if (!user) {
      const hashed = await bcrypt.hash(password, 10);
      user = await storage.createUser({ username: primary, password: hashed });
      await storage.createGameProgress(user.id);
      console.log(`seeded play save ${primary}`);
    }
    for (const alias of aliases) {
      if (alias === user.username.toLowerCase()) continue;
      await storage.addAlias(user.id, alias);
    }
    console.log(`play login emails: ${primary} · ${easy}`);
  } catch (err) {
    console.error("seedBossLogin failed (apply 30-ops-dinocrushboss-login.sql?)", err);
  }
}
