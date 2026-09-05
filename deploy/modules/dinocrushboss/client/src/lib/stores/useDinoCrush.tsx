import { create } from "zustand";
import { Position, DinoType, GameState, StarRating, LevelStats } from "@/types/game";
import { createBoard, findMatches, applyGravity, fillEmptySpaces } from "@/lib/gameLogic";
import { LEVEL_COUNT, STAR_REQUIREMENTS } from "@/lib/constants";

interface DinoCrushState {
  gameState: GameState;
  
  // Star rating and statistics
  levelStartTime: number;
  totalMoves: number;
  totalCombos: number;
  specialDinosUsed: number;
  
  // Actions
  setBoard: (board: DinoType[][]) => void;
  setSelectedTile: (position: Position | null) => void;
  swapTiles: (pos1: Position, pos2: Position) => void;
  removeMatches: (positions: Position[]) => void;
  addScore: (points: number) => void;
  setScore: (score: number) => void;
  setCurrentLevel: (level: number) => void;
  resetBoard: () => void;
  resetGame: () => void;
  setLevelComplete: (complete: boolean) => void;
  goToNextLevel: () => void;
  calculateStarRating: () => StarRating;
  addMove: () => void;
  addCombo: (count: number) => void;
  addSpecialDinoUsed: () => void;
  startLevel: () => void;
}

export const useDinoCrush = create<DinoCrushState>((set, get) => ({
  gameState: {
    board: createBoard(1),
    selectedTile: null,
    score: 0,
    currentLevel: 1,
    levelComplete: false,
    moves: 0,
    timeRemaining: undefined,
    levelStats: undefined,
    starRating: undefined
  },
  
  // Star rating and statistics
  levelStartTime: Date.now(),
  totalMoves: 0,
  totalCombos: 0,
  specialDinosUsed: 0,
  
  setBoard: (board) => {
    set((state) => ({
      gameState: {
        ...state.gameState,
        board
      }
    }));
  },
  
  setSelectedTile: (position) => {
    set((state) => ({
      gameState: {
        ...state.gameState,
        selectedTile: position
      }
    }));
  },
  
  swapTiles: (pos1, pos2) => {
    const { board } = get().gameState;
    
    // Create a copy of the board
    const newBoard = [...board.map(row => [...row])];
    
    // Swap the tiles
    const temp = newBoard[pos1.y][pos1.x];
    newBoard[pos1.y][pos1.x] = newBoard[pos2.y][pos2.x];
    newBoard[pos2.y][pos2.x] = temp;
    
    // Update the board
    set((state) => ({
      gameState: {
        ...state.gameState,
        board: newBoard
      }
    }));
    
    // Check if the swap created any matches
    const matches = findMatches(newBoard);
    if (matches.length === 0) {
      // If no matches, swap back after a delay
      setTimeout(() => {
        set((state) => {
          const revertBoard = [...state.gameState.board.map(row => [...row])];
          const temp = revertBoard[pos1.y][pos1.x];
          revertBoard[pos1.y][pos1.x] = revertBoard[pos2.y][pos2.x];
          revertBoard[pos2.y][pos2.x] = temp;
          
          return {
            gameState: {
              ...state.gameState,
              board: revertBoard
            }
          };
        });
      }, 500);
    }
  },
  
  removeMatches: (positions) => {
    const state = get();
    let { board } = state.gameState;
    const level = state.gameState.currentLevel;
    
    // Mark matched positions with null
    let newBoard = [...board.map(row => [...row])];
    positions.forEach(pos => {
      newBoard[pos.y][pos.x] = -1 as DinoType; // Temporarily mark as removed
    });
    
    // Apply gravity to make tiles fall
    newBoard = applyGravity(newBoard);
    
    // Fill empty spaces with new tiles (pass level for appropriate tile types)
    newBoard = fillEmptySpaces(newBoard, level);
    
    // Update the board
    set((prevState) => ({
      gameState: {
        ...prevState.gameState,
        board: newBoard
      }
    }));
  },
  
  addScore: (points) => {
    set((state) => ({
      gameState: {
        ...state.gameState,
        score: state.gameState.score + points
      }
    }));
  },
  
  setScore: (score) => {
    set((state) => ({
      gameState: {
        ...state.gameState,
        score
      }
    }));
  },
  
  setCurrentLevel: (level) => {
    set((state) => ({
      gameState: {
        ...state.gameState,
        currentLevel: level,
        board: createBoard(level),
        score: 0,
        selectedTile: null,
        levelComplete: false,
        moves: 0
      },
      levelStartTime: Date.now(),
      totalMoves: 0,
      totalCombos: 0,
      specialDinosUsed: 0
    }));
  },
  
  resetBoard: () => {
    const state = get();
    const newBoard = createBoard(state.gameState.currentLevel);
    set((state) => ({
      gameState: {
        ...state.gameState,
        board: newBoard,
        selectedTile: null
      }
    }));
  },
  
  resetGame: () => {
    set({
      gameState: {
        board: createBoard(1),
        selectedTile: null,
        score: 0,
        currentLevel: 1,
        levelComplete: false,
        moves: 0,
        timeRemaining: undefined,
        levelStats: undefined,
        starRating: undefined
      },
      levelStartTime: Date.now(),
      totalMoves: 0,
      totalCombos: 0,
      specialDinosUsed: 0
    });
  },
  
  setLevelComplete: (complete) => {
    set((state) => ({
      gameState: {
        ...state.gameState,
        levelComplete: complete
      }
    }));
  },
  
  goToNextLevel: () => {
    const state = get();
    if (state.gameState.currentLevel < LEVEL_COUNT) {
      set((prev) => ({
        gameState: {
          ...prev.gameState,
          currentLevel: prev.gameState.currentLevel + 1,
          board: createBoard(prev.gameState.currentLevel + 1),
          score: 0,
          selectedTile: null,
          levelComplete: false,
          moves: 0,
          starRating: undefined
        },
        levelStartTime: Date.now(),
        totalMoves: 0,
        totalCombos: 0,
        specialDinosUsed: 0
      }));
    }
  },

  calculateStarRating: () => {
    const state = get();
    const level = state.gameState.currentLevel;
    const score = state.gameState.score;
    const requirements = STAR_REQUIREMENTS[level];
    
    if (!requirements) return StarRating.OneStar;
    
    // Calculate time bonus (faster completion = bonus)
    const timeUsed = Date.now() - state.levelStartTime;
    const timeInSeconds = Math.floor(timeUsed / 1000);
    const timeBonus = Math.max(0, requirements.timeBonus - timeInSeconds);
    
    // Calculate move efficiency bonus (fewer moves = bonus)
    const moveBonus = Math.max(0, requirements.moveBonus - state.totalMoves * 10);
    
    // Calculate combo bonus
    const comboBonus = state.totalCombos * requirements.comboBonus;
    
    // Total adjusted score
    const finalScore = score + timeBonus + moveBonus + comboBonus;
    
    // Determine star rating
    if (finalScore >= requirements.threeStarScore) {
      return StarRating.ThreeStars;
    } else if (finalScore >= requirements.twoStarScore) {
      return StarRating.TwoStars;
    } else {
      return StarRating.OneStar;
    }
  },

  addMove: () => {
    set((state) => ({
      ...state,
      totalMoves: state.totalMoves + 1,
      gameState: {
        ...state.gameState,
        moves: state.gameState.moves + 1
      }
    }));
  },

  addCombo: (count: number) => {
    set((state) => ({
      ...state,
      totalCombos: state.totalCombos + count
    }));
  },

  addSpecialDinoUsed: () => {
    set((state) => ({
      ...state,
      specialDinosUsed: state.specialDinosUsed + 1
    }));
  },

  startLevel: () => {
    set((state) => ({
      ...state,
      levelStartTime: Date.now(),
      totalMoves: 0,
      totalCombos: 0,
      specialDinosUsed: 0
    }));
  }
}));
