import { DinoType, Position, PowerUpType, SpecialDinoType } from "@/types/game";
import { BOARD_SIZE, getDinosForLevel, getGridSize, getMatchSetupCount } from "@/lib/constants";

/**
 * Creates a board with no ready-made 3-in-a-rows, but lots of one-swap matches on easy levels.
 */
export function createBoard(level: number = 1): DinoType[][] {
  const gridSize = getGridSize(level);
  let board: DinoType[][] = [];
  let attempts = 0;
  const maxAttempts = 12;

  do {
    board = [];
    for (let y = 0; y < gridSize; y++) {
      const row: DinoType[] = [];
      for (let x = 0; x < gridSize; x++) {
        let newTile: DinoType;
        do {
          newTile = getRandomDinoType(level);
        } while (
          (x >= 2 && row[x - 1] === newTile && row[x - 2] === newTile) ||
          (y >= 2 && board[y - 1][x] === newTile && board[y - 2][x] === newTile)
        );
        row.push(newTile);
      }
      board.push(row);
    }
    attempts++;
  } while (!hasValidMoves(board) && attempts < maxAttempts);

  board = injectMatchOpportunities(board, getMatchSetupCount(level));
  board = clearAccidentalMatches(board, level);
  if (!hasValidMoves(board)) {
    board = injectMatchOpportunities(board, 8);
    board = clearAccidentalMatches(board, level);
  }
  return board;
}

/**
 * Opportunity inject can accidentally create a ready-made 3-in-a-row.
 * Replace one tile at a time until the board has no free matches.
 */
function clearAccidentalMatches(board: DinoType[][], level: number): DinoType[][] {
  const pool = getDinosForLevel(level);
  const next = board.map((row) => [...row]);
  for (let guard = 0; guard < 60; guard++) {
    const matches = findMatches(next);
    if (matches.length === 0) break;
    const pos = matches[0];
    const current = next[pos.y][pos.x];
    const others = pool.filter((t) => t !== current);
    if (others.length === 0) break;
    next[pos.y][pos.x] = others[Math.floor(Math.random() * others.length)];
  }
  return next;
}

/**
 * Injects matching opportunities into a board, including 4+ match setups
 */
function injectMatchOpportunities(board: DinoType[][], count = 6): DinoType[][] {
  const newBoard = board.map(row => [...row]);
  const height = board.length;
  const width = board[0]?.length || 0;
  const numOpportunities = Math.min(count, Math.max(4, Math.floor((height * width) / 6)));
  
  for (let i = 0; i < numOpportunities; i++) {
    const matchSize = Math.random() < 0.3 ? 4 : (Math.random() < 0.2 ? 5 : 3);
    
    if (matchSize === 3) {
      // Standard 3-match: [A][B][A] pattern
      const x = Math.floor(Math.random() * (width - 2));
      const y = Math.floor(Math.random() * height);
      const matchType = newBoard[y][x];
      if (x + 2 < width) {
        newBoard[y][x + 2] = matchType;
      }
    } else if (matchSize === 4) {
      // 4-match opportunity: [A][A][B][A] or [A][B][A][A]
      const x = Math.floor(Math.random() * (width - 3));
      const y = Math.floor(Math.random() * height);
      const matchType = newBoard[y][x];
      if (x + 3 < width) {
        newBoard[y][x + 1] = matchType;
        newBoard[y][x + 3] = matchType;
      }
    } else if (matchSize === 5) {
      // 5-match opportunity: [A][A][B][A][A]
      const x = Math.floor(Math.random() * (width - 4));
      const y = Math.floor(Math.random() * height);
      const matchType = newBoard[y][x];
      if (x + 4 < width) {
        newBoard[y][x + 1] = matchType;
        newBoard[y][x + 3] = matchType;
        newBoard[y][x + 4] = matchType;
      }
    }
    
    // Also create vertical opportunities for variety
    if (i % 2 === 0) {
      const vx = Math.floor(Math.random() * width);
      const vy = Math.floor(Math.random() * (height - 3));
      if (vy + 3 < height) {
        const vType = newBoard[vy][vx];
        newBoard[vy + 1][vx] = vType;
        newBoard[vy + 3][vx] = vType;
      }
    }
  }
  
  return newBoard;
}

/**
 * Extended tile info that includes power-ups and special dinosaurs
 */
interface ExtendedTileInfo {
  dinoType: DinoType;
  powerUp?: PowerUpType;
  specialDino?: SpecialDinoType;
}

/**
 * Finds all matching groups of 3 or more in the board
 * Now supports power-ups as matchable items based on their underlying dinosaur type
 */
export function findMatches(
  board: DinoType[][],
  powerUps?: {[key: string]: PowerUpType},
  specialDinos?: {[key: string]: SpecialDinoType}
): Position[] {
  const matches: Position[] = [];
  const visited = new Set<string>();
  
  // Helper function to get effective tile type for matching
  const getEffectiveTileType = (x: number, y: number): DinoType => {
    const key = `${x}-${y}`;
    
    // Power-ups can match with their underlying dinosaur type
    if (powerUps && powerUps[key]) {
      return board[y][x]; // Use the base dinosaur type
    }
    
    // Special dinosaurs can also match with their base type
    if (specialDinos && specialDinos[key]) {
      return board[y][x]; // Use the base dinosaur type
    }
    
    return board[y][x];
  };
  
  const boardHeight = board.length;
  const boardWidth = board[0]?.length || 0;
  
  // Check for horizontal matches
  for (let y = 0; y < boardHeight; y++) {
    for (let x = 0; x < boardWidth - 2; x++) {
      const current = getEffectiveTileType(x, y);
      if (current < 0) continue; // Skip empty spaces
      
      // Check if we have at least 3 in a row horizontally
      if (getEffectiveTileType(x + 1, y) === current && getEffectiveTileType(x + 2, y) === current) {
        // Found a horizontal match of at least 3
        let matchLength = 3;
        
        // See if the match extends further
        while (x + matchLength < boardWidth && getEffectiveTileType(x + matchLength, y) === current) {
          matchLength++;
        }
        
        // Add all positions in this match
        for (let i = 0; i < matchLength; i++) {
          const key = `${x + i},${y}`;
          if (!visited.has(key)) {
            visited.add(key);
            matches.push({ x: x + i, y });
          }
        }
      }
    }
  }
  
  // Check for vertical matches
  for (let x = 0; x < boardWidth; x++) {
    for (let y = 0; y < boardHeight - 2; y++) {
      const current = getEffectiveTileType(x, y);
      if (current < 0) continue; // Skip empty spaces
      
      // Check if we have at least 3 in a row vertically
      if (getEffectiveTileType(x, y + 1) === current && getEffectiveTileType(x, y + 2) === current) {
        // Found a vertical match of at least 3
        let matchLength = 3;
        
        // See if the match extends further
        while (y + matchLength < boardHeight && getEffectiveTileType(x, y + matchLength) === current) {
          matchLength++;
        }
        
        // Add all positions in this match
        for (let i = 0; i < matchLength; i++) {
          const key = `${x},${y + i}`;
          if (!visited.has(key)) {
            visited.add(key);
            matches.push({ x, y: y + i });
          }
        }
      }
    }
  }
  
  return matches;
}

/**
 * Analyzes the board to find all possible valid moves
 * Returns true if there are valid moves available, false if board needs rescue
 */
export function hasValidMoves(board: DinoType[][]): boolean {
  const boardHeight = board.length;
  const boardWidth = board[0]?.length || 0;
  
  // Check all possible swaps between adjacent tiles
  for (let y = 0; y < boardHeight; y++) {
    for (let x = 0; x < boardWidth; x++) {
      // Check right neighbor
      if (x < boardWidth - 1) {
        const tempBoard = board.map(row => [...row]);
        // Swap current tile with right neighbor
        [tempBoard[y][x], tempBoard[y][x + 1]] = [tempBoard[y][x + 1], tempBoard[y][x]];
        
        // Check if this swap creates matches
        if (findMatches(tempBoard).length > 0) {
          return true;
        }
      }
      
      // Check bottom neighbor  
      if (y < boardHeight - 1) {
        const tempBoard = board.map(row => [...row]);
        // Swap current tile with bottom neighbor
        [tempBoard[y][x], tempBoard[y + 1][x]] = [tempBoard[y + 1][x], tempBoard[y][x]];
        
        // Check if this swap creates matches
        if (findMatches(tempBoard).length > 0) {
          return true;
        }
      }
    }
  }
  
  return false;
}

/**
 * Finds the best available move for the hint system
 * Returns the position pair that would create the best match
 */
export function findBestMove(board: DinoType[][]): { from: Position, to: Position } | null {
  const boardHeight = board.length;
  const boardWidth = board[0]?.length || 0;
  let bestMove: { from: Position, to: Position, score: number } | null = null;
  
  // Check all possible swaps between adjacent tiles
  for (let y = 0; y < boardHeight; y++) {
    for (let x = 0; x < boardWidth; x++) {
      // Check right neighbor
      if (x < boardWidth - 1) {
        const tempBoard = board.map(row => [...row]);
        [tempBoard[y][x], tempBoard[y][x + 1]] = [tempBoard[y][x + 1], tempBoard[y][x]];
        const matches = findMatches(tempBoard);
        if (matches.length > 0) {
          const score = matches.length;
          if (!bestMove || score > bestMove.score) {
            bestMove = { from: { x, y }, to: { x: x + 1, y }, score };
          }
        }
      }
      
      // Check bottom neighbor  
      if (y < boardHeight - 1) {
        const tempBoard = board.map(row => [...row]);
        [tempBoard[y][x], tempBoard[y + 1][x]] = [tempBoard[y + 1][x], tempBoard[y][x]];
        const matches = findMatches(tempBoard);
        if (matches.length > 0) {
          const score = matches.length;
          if (!bestMove || score > bestMove.score) {
            bestMove = { from: { x, y }, to: { x, y: y + 1 }, score };
          }
        }
      }
    }
  }
  
  return bestMove ? { from: bestMove.from, to: bestMove.to } : null;
}

/**
 * Finds strategic positions to place special tiles for maximum board shake-up
 * Returns positions that would create the most disruption
 */
export function findRescuePositions(board: DinoType[][]): Position[] {
  const positions: Position[] = [];
  const typeCount: { [key: number]: number } = {};
  const boardHeight = board.length;
  const boardWidth = board[0]?.length || 0;
  
  // Count frequency of each dinosaur type
  for (let y = 0; y < boardHeight; y++) {
    for (let x = 0; x < boardWidth; x++) {
      const type = board[y][x];
      typeCount[type] = (typeCount[type] || 0) + 1;
    }
  }
  
  // Find the most common dinosaur type
  const mostCommonType = Object.keys(typeCount).reduce((a, b) => 
    typeCount[parseInt(a)] > typeCount[parseInt(b)] ? a : b
  );
  
  // Find positions with the most common type for strategic placement
  for (let y = 0; y < boardHeight; y++) {
    for (let x = 0; x < boardWidth; x++) {
      if (board[y][x] === parseInt(mostCommonType)) {
        // Prioritize center positions and corners for maximum impact
        const centerDistance = Math.abs(x - BOARD_SIZE/2) + Math.abs(y - BOARD_SIZE/2);
        const isCorner = (x === 0 || x === BOARD_SIZE-1) && (y === 0 || y === BOARD_SIZE-1);
        const priority = isCorner ? 100 : (50 - centerDistance * 10);
        
        positions.push({ x, y, priority } as Position & { priority: number });
      }
    }
  }
  
  // Sort by priority and return top 3 positions
  return positions
    .sort((a: any, b: any) => b.priority - a.priority)
    .slice(0, 3)
    .map(pos => ({ x: pos.x, y: pos.y }));
}

/**
 * Apply gravity to the board, making tiles fall to fill empty spaces
 */
export function applyGravity(board: DinoType[][]): DinoType[][] {
  const newBoard = [...board.map(row => [...row])];
  const boardHeight = board.length;
  const boardWidth = board[0]?.length || 0;
  
  // For each column
  for (let x = 0; x < boardWidth; x++) {
    // Start from the bottom and move upwards
    let emptyPos = -1;
    
    for (let y = boardHeight - 1; y >= 0; y--) {
      // If we find an empty space, record its position
      if (newBoard[y][x] < 0 && emptyPos === -1) {
        emptyPos = y;
      }
      
      // If we have an empty position and find a tile, move the tile down
      if (emptyPos !== -1 && newBoard[y][x] >= 0) {
        newBoard[emptyPos][x] = newBoard[y][x];
        newBoard[y][x] = -1 as DinoType;
        
        // Move the empty position up
        emptyPos--;
        
        // Reset the search to look for the next empty position
        y = boardHeight;
        emptyPos = -1;
      }
    }
  }
  
  return newBoard;
}

/**
 * Fill empty spaces in the board with new random tiles
 */
export function fillEmptySpaces(board: DinoType[][], level: number = 1): DinoType[][] {
  const newBoard = [...board.map(row => [...row])];
  const boardHeight = board.length;
  const boardWidth = board[0]?.length || 0;
  
  for (let y = 0; y < boardHeight; y++) {
    for (let x = 0; x < boardWidth; x++) {
      if (newBoard[y][x] < 0) {
        newBoard[y][x] = getRandomDinoType(level);
      }
    }
  }
  
  return newBoard;
}

/**
 * Random dinosaur from this level's unlock pool (famous first, obscure later).
 */
export function getRandomDinoType(level: number = 1): DinoType {
  const availableTypes = getDinosForLevel(level);
  return availableTypes[Math.floor(Math.random() * availableTypes.length)];
}

/**
 * Check if swapping two positions would create a match
 */
export function wouldCreateMatch(board: DinoType[][], pos1: Position, pos2: Position): boolean {
  // Create a copy of the board with the tiles swapped
  const testBoard = board.map(row => [...row]);
  
  // Swap the tiles
  const temp = testBoard[pos1.y][pos1.x];
  testBoard[pos1.y][pos1.x] = testBoard[pos2.y][pos2.x];
  testBoard[pos2.y][pos2.x] = temp;
  
  // Check if this creates any matches
  const matches = findMatches(testBoard);
  return matches.length > 0;
}
