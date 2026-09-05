// Dinosaur types for the game pieces
export enum DinoType {
  Red,
  Green,
  Blue,
  Yellow,
  Purple,
  Orange,
  Pink,
  Cyan,
  Brown,
  Silver,      // Metallic armored dinosaur
  Gold,        // Legendary golden dinosaur
  Crystal,     // Crystalline ice dinosaur
  Shadow,      // Dark mysterious dinosaur
  Rainbow,     // Multi-colored mythical dinosaur
  Volcanic,    // Fire-breathing lava dinosaur
  Cosmic,      // Space-themed stellar dinosaur
  Lime,        // Bright lime green
  Magenta,     // Bright magenta pink
  Turquoise,   // Blue-green aquatic
  Coral,       // Coral reef dinosaur
  Indigo,      // Deep indigo blue
  Amber,       // Golden amber fossil
  Jade,        // Green jade stone
  Ruby,        // Deep red ruby
  Sapphire,    // Blue sapphire gem
  Emerald,     // Green emerald gem
  Diamond,     // Clear diamond crystal
  Pearl,       // Lustrous white pearl
  Opal,        // Multicolored opal
  Onyx         // Black onyx stone
}

export enum PowerUpType {
  Bomb,           // Destroys 3x3 area
  Lightning,      // Destroys entire row
  Rainbow,        // Destroys entire column
  Freeze,         // Stops time for extra moves
  RowCrusher,     // Special dino that clears entire row
  ColumnCrusher,  // Special dino that clears entire column
  ColorBomb,      // Destroys all dinos of same color
  MegaBomb,       // Destroys 5x5 area
  TimeBonus,      // Adds extra time
  ScoreMultiplier, // Doubles next match score
  ShuffleBoard,   // Reshuffles entire board
  ExtraMoves,     // Adds extra moves
  DinoBlast,      // Eliminates all of one dinosaur type
  ChainReaction,  // Creates cascading explosions
  MagicWand,      // Transforms random tiles into matches
  PowerOrb        // Charges up for mega effects
}

export enum SpecialDinoType {
  Normal,
  RowCrusher,
  ColumnCrusher,
  ColorBomb,
  MegaBomb,
  TimeWarp,       // Freezes time and adds extra moves
  ScoreBurst,     // Multiplies next few matches
  ElementalBlast, // Clears all tiles of same element
  ChainLightning, // Creates chain reactions
  WildCard        // Can match with any dinosaur type
}

export enum SeasonTheme {
  Spring,
  Summer,
  Autumn,
  Winter
}

// Position on the game board
export interface Position {
  x: number;
  y: number;
}

// Star rating for level completion
export enum StarRating {
  OneStar = 1,
  TwoStars = 2,
  ThreeStars = 3
}

// Level completion statistics
export interface LevelStats {
  level: number;
  score: number;
  stars: StarRating;
  movesUsed: number;
  timeUsed: number;
  comboCount: number;
  specialDinosUsed: number;
  completedAt: Date;
}

// Star requirements for each level
export interface StarRequirements {
  oneStarScore: number;
  twoStarScore: number;
  threeStarScore: number;
  timeBonus?: number;
  moveBonus?: number;
  comboBonus?: number;
}

// Main game state
export interface GameState {
  board: DinoType[][];
  selectedTile: Position | null;
  score: number;
  currentLevel: number;
  levelComplete: boolean;
  moves: number;
  timeRemaining?: number;
  levelStats?: LevelStats;
  starRating?: StarRating;
}
