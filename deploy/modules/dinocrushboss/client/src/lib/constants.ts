import { DinoType } from "@/types/game";

// Game board configuration
export const BOARD_SIZE = 6;
export const TILE_SIZE = 2;
export const ANIMATION_DURATION = 300;
export const HINT_DELAY = 4000;

/**
 * Famous dinos first (easy to spot), lesser-known names later.
 * T-Rex, Triceratops, Stegosaurus → … → Utahraptor.
 */
export const DINO_UNLOCK_ORDER: DinoType[] = [
  DinoType.Red,      // T-Rex
  DinoType.Cosmic,   // Triceratops
  DinoType.Volcanic, // Stegosaurus
  DinoType.Shadow,   // Brachiosaurus
  DinoType.Lime,     // Velociraptor
  DinoType.Rainbow,  // Pterodactyl
  DinoType.Yellow,   // Spinosaurus
  DinoType.Green,    // Ankylosaurus
  DinoType.Orange,   // Dilophosaurus
  DinoType.Gold,     // Diplodocus
  DinoType.Blue,     // Parasaurolophus
  DinoType.Purple,   // Carnotaurus
  DinoType.Cyan,     // Gallimimus
  DinoType.Brown,    // Iguanodon
  DinoType.Pink,     // Oviraptor
  DinoType.Silver,   // Pachycephalosaurus
  DinoType.Crystal,  // Utahraptor
];

export const DINO_NAMES: Record<number, string> = {
  [DinoType.Red]: "T-Rex",
  [DinoType.Cosmic]: "Triceratops",
  [DinoType.Volcanic]: "Stegosaurus",
  [DinoType.Shadow]: "Brachiosaurus",
  [DinoType.Lime]: "Velociraptor",
  [DinoType.Rainbow]: "Pterodactyl",
  [DinoType.Yellow]: "Spinosaurus",
  [DinoType.Green]: "Ankylosaurus",
  [DinoType.Orange]: "Dilophosaurus",
  [DinoType.Gold]: "Diplodocus",
  [DinoType.Blue]: "Parasaurolophus",
  [DinoType.Purple]: "Carnotaurus",
  [DinoType.Cyan]: "Gallimimus",
  [DinoType.Brown]: "Iguanodon",
  [DinoType.Pink]: "Oviraptor",
  [DinoType.Silver]: "Pachycephalosaurus",
  [DinoType.Crystal]: "Utahraptor",
};

export const DINO_IMAGES: Record<number, string> = {
  [DinoType.Red]: "/dinos/trex.png",
  [DinoType.Green]: "/dinos/ankylosaurus.png",
  [DinoType.Blue]: "/dinos/parasaurolophus.png",
  [DinoType.Yellow]: "/dinos/spinosaurus.png",
  [DinoType.Purple]: "/dinos/carnotaurus.png",
  [DinoType.Orange]: "/dinos/dilophosaurus.png",
  [DinoType.Pink]: "/dinos/oviraptor.png",
  [DinoType.Cyan]: "/dinos/gallimimus.png",
  [DinoType.Brown]: "/dinos/iguanodon.png",
  [DinoType.Silver]: "/dinos/pachycephalosaurus.png",
  [DinoType.Gold]: "/dinos/diplodocus.png",
  [DinoType.Crystal]: "/dinos/utahraptor.png",
  [DinoType.Shadow]: "/dinos/brachiosaurus.png",
  [DinoType.Rainbow]: "/dinos/pterodactyl.png",
  [DinoType.Volcanic]: "/dinos/stegosaurus.png",
  [DinoType.Cosmic]: "/dinos/triceratops.png",
  [DinoType.Lime]: "/dinos/velociraptor.png",
};

export const getDinoImage = (type: DinoType): string => {
  return DINO_IMAGES[type] || "/dinos/trex.png";
};

/** Idle motion class so each species feels alive on the board. */
export const getDinoIdleClass = (type: DinoType): string => {
  switch (type) {
    case DinoType.Red:
      return "dino-idle-stomp";
    case DinoType.Cosmic:
      return "dino-idle-sway";
    case DinoType.Volcanic:
      return "dino-idle-wiggle";
    case DinoType.Shadow:
      return "dino-idle-bob";
    case DinoType.Lime:
      return "dino-idle-dart";
    case DinoType.Rainbow:
      return "dino-idle-glide";
    case DinoType.Yellow:
      return "dino-idle-snap";
    case DinoType.Green:
      return "dino-idle-sway";
    case DinoType.Orange:
      return "dino-idle-wiggle";
    case DinoType.Gold:
      return "dino-idle-bob";
    case DinoType.Blue:
      return "dino-idle-bob";
    case DinoType.Purple:
      return "dino-idle-stomp";
    case DinoType.Cyan:
      return "dino-idle-dart";
    case DinoType.Brown:
      return "dino-idle-stomp";
    case DinoType.Pink:
      return "dino-idle-peck";
    case DinoType.Silver:
      return "dino-idle-wiggle";
    case DinoType.Crystal:
      return "dino-idle-dart";
    default:
      return "dino-idle-bob";
  }
};

/** How many dinosaur kinds appear on this level. Level 1 is three famous faces. */
export const getTypeCountForLevel = (level: number): number => {
  if (level <= 2) return 3;
  if (level <= 4) return 4;
  if (level <= 7) return 5;
  if (level <= 10) return 6;
  if (level <= 14) return 8;
  if (level <= 19) return 11;
  if (level <= 24) return 14;
  return 17;
};

export const getDinosForLevel = (level: number): DinoType[] => {
  return DINO_UNLOCK_ORDER.slice(0, getTypeCountForLevel(level));
};

export const getDinoNamesForLevel = (level: number): string[] => {
  return getDinosForLevel(level).map((t) => DINO_NAMES[t] || "Dino");
};

/** Near-match setups to plant on a fresh board. More on easy levels = more swaps that work. */
export const getMatchSetupCount = (level: number): number => {
  if (level <= 2) return 14;
  if (level <= 5) return 10;
  if (level <= 10) return 7;
  return 5;
};

export const getGridSize = (level: number): number => {
  if (level <= 8) return 6;
  if (level <= 16) return 7;
  if (level <= 24) return 8;
  return 8;
};

const generateLevelGoals = (): number[] => {
  const goals: number[] = [];
  for (let level = 1; level <= 500; level++) {
    let baseScore: number;
    if (level === 1) {
      baseScore = 90;
    } else if (level === 2) {
      baseScore = 120;
    } else if (level <= 5) {
      baseScore = 120 + (level - 2) * 40;
    } else if (level <= 10) {
      baseScore = 240 + (level - 5) * 40;
    } else if (level <= 20) {
      baseScore = 440 + (level - 10) * 50;
    } else if (level <= 30) {
      baseScore = 940 + (level - 20) * 60;
    } else if (level <= 100) {
      baseScore = 1540 + (level - 30) * 30;
    } else {
      baseScore = 3640 + (level - 100) * 20;
    }
    goals.push(Math.floor(baseScore));
  }
  return goals;
};

export const LEVEL_GOALS = generateLevelGoals();
export const LEVEL_COUNT = 30;

const generateStarRequirements = () => {
  const requirements: { [key: number]: any } = {};
  for (let level = 1; level <= 500; level++) {
    const baseScore = LEVEL_GOALS[level - 1];
    requirements[level] = {
      oneStarScore: Math.floor(baseScore * 0.6),
      twoStarScore: Math.floor(baseScore * 0.85),
      threeStarScore: Math.floor(baseScore * 1.2),
      timeBonus: level <= 50 ? 500 : level <= 150 ? 1000 : 1500,
      moveBonus: level <= 50 ? 300 : 600,
      comboBonus: level <= 50 ? 100 : 200,
    };
  }
  return requirements;
};

export const STAR_REQUIREMENTS = generateStarRequirements();

const generateLevelMechanics = (): {
  [key: number]: {
    minDinoTypes: number;
    maxDinoTypes: number;
    powerUpChance: number;
    moveLimit?: number;
    timeLimit?: number;
    specialChallenges?: string[];
  };
} => {
  const mechanics: { [key: number]: any } = {};
  for (let level = 1; level <= 500; level++) {
    const types = getTypeCountForLevel(level);
    let powerUpChance = 0.05;
    let moveLimit: number | undefined;
    let timeLimit: number | undefined;
    const specialChallenges: string[] = [];

    if (level <= 5) {
      powerUpChance = 0.04;
    } else if (level <= 10) {
      powerUpChance = 0.08;
    } else if (level <= 20) {
      powerUpChance = 0.12;
    } else if (level <= 30) {
      powerUpChance = 0.18;
    } else {
      powerUpChance = Math.min(0.2 + (level - 30) * 0.004, 1.4);
      if (level > 40) moveLimit = Math.max(40 - Math.floor((level - 40) / 8), 18);
      if (level > 80) timeLimit = Math.max(150 - Math.floor((level - 80) / 5), 75);
    }

    mechanics[level] = {
      minDinoTypes: types,
      maxDinoTypes: types,
      powerUpChance,
      ...(moveLimit && { moveLimit }),
      ...(timeLimit && { timeLimit }),
      ...(specialChallenges.length > 0 && { specialChallenges }),
    };
  }
  return mechanics;
};

export const LEVEL_MECHANICS = generateLevelMechanics();
