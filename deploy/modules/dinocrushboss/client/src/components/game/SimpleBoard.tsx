import { useState, useEffect, useRef, useCallback } from "react";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { useAudio } from "@/lib/stores/useAudio";
import { DinoType, SeasonTheme, PowerUpType, SpecialDinoType, Position } from "@/types/game";
import { LEVEL_GOALS, ANIMATION_DURATION, HINT_DELAY, getGridSize, getDinoImage, getDinoIdleClass } from "@/lib/constants";
import { findBestMove, createBoard, wouldCreateMatch, getRandomDinoType } from "@/lib/gameLogic";

const dinoColors = {
  [DinoType.Red]: "#ff4444",
  [DinoType.Green]: "#44cc44",
  [DinoType.Blue]: "#4488ff",
  [DinoType.Yellow]: "#ffcc44",
  [DinoType.Purple]: "#cc44cc",
  [DinoType.Orange]: "#ff8844",
  [DinoType.Pink]: "#ff88cc",
  [DinoType.Cyan]: "#44cccc",
  [DinoType.Brown]: "#8b4513",
  [DinoType.Silver]: "#c0c0c0",
  [DinoType.Gold]: "#ffd700",
  [DinoType.Crystal]: "#b8f2ff",
  [DinoType.Shadow]: "#2d2d2d",
  [DinoType.Rainbow]: "#ff6b6b",
  [DinoType.Volcanic]: "#ff2d00",
  [DinoType.Cosmic]: "#4c0099",
  [DinoType.Lime]: "#32cd32",
  [DinoType.Magenta]: "#ff1493",
  [DinoType.Turquoise]: "#40e0d0",
  [DinoType.Coral]: "#ff7f50",
  [DinoType.Indigo]: "#4b0082",
  [DinoType.Amber]: "#ffbf00",
  [DinoType.Jade]: "#00a86b",
  [DinoType.Ruby]: "#e0115f",
  [DinoType.Sapphire]: "#0f52ba",
  [DinoType.Emerald]: "#50c878",
  [DinoType.Diamond]: "#b9f2ff",
  [DinoType.Pearl]: "#f8f6f0",
  [DinoType.Opal]: "#a8c3bc",
  [DinoType.Onyx]: "#0f0f0f",
};

const specialDinoEmojis = {
  rowCrusher: "🦖",
  columnCrusher: "🦕",
  colorBomb: "🦖",
  megaBomb: "🦕",
};

// Helper function to get special dinosaur emoji
const getSpecialDinoEmoji = (specialType: SpecialDinoType): string => {
  switch (specialType) {
    case SpecialDinoType.RowCrusher:
      return specialDinoEmojis.rowCrusher;
    case SpecialDinoType.ColumnCrusher:
      return specialDinoEmojis.columnCrusher;
    case SpecialDinoType.ColorBomb:
      return specialDinoEmojis.colorBomb;
    case SpecialDinoType.MegaBomb:
      return specialDinoEmojis.megaBomb;
    default:
      return "🦖";
  }
};

const seasonalBackgrounds = {
  [SeasonTheme.Spring]: "bg-gradient-to-br from-green-600 to-emerald-700",
  [SeasonTheme.Summer]: "bg-gradient-to-br from-yellow-500 to-orange-600",
  [SeasonTheme.Autumn]: "bg-gradient-to-br from-orange-600 to-red-700",
  [SeasonTheme.Winter]: "bg-gradient-to-br from-blue-400 to-indigo-600",
};

const seasonalEffects = {
  [SeasonTheme.Spring]: "🌸",
  [SeasonTheme.Summer]: "☀️",
  [SeasonTheme.Autumn]: "🍂",
  [SeasonTheme.Winter]: "❄️",
};

interface SimpleBoardProps {
  onBoardUpdate: (hasMatches: boolean) => void;
}

const SimpleBoard: React.FC<SimpleBoardProps> = ({ onBoardUpdate }) => {
  const { 
    gameState, 
    setSelectedTile, 
    swapTiles, 
    removeMatches, 
    addScore,
    setBoard,
    addMove,
    addCombo,
  } = useDinoCrush();
  
  const { playHit, playSuccess, playCrush } = useAudio();
  const { board, selectedTile } = gameState;
  const [animating, setAnimating] = useState(false);
  const [scoreAnimation, setScoreAnimation] = useState(false);
  const [lastScore, setLastScore] = useState(gameState.score);
  const [currentSeason, setCurrentSeason] = useState<SeasonTheme>(SeasonTheme.Spring);
  const [powerUps, setPowerUps] = useState<{[key: string]: PowerUpType}>({});
  const [specialDinos, setSpecialDinos] = useState<{[key: string]: SpecialDinoType}>({});
  const [comboCount, setComboCount] = useState(0);
  const [dragging, setDragging] = useState<{x: number, y: number} | null>(null);
  const [dragTarget, setDragTarget] = useState<{x: number, y: number} | null>(null);
  const [eliminatingTiles, setEliminatingTiles] = useState<{[key: string]: boolean}>({});
  const [cascading, setCascading] = useState(false);
  const [boardRescuing, setBoardRescuing] = useState(false);
  const [activePowerUps, setActivePowerUps] = useState<{[key: string]: PowerUpType}>({});
  const [scoreMultiplier, setScoreMultiplier] = useState(1);
  const [extraMoves, setExtraMoves] = useState(0);
  const [timeFreeze, setTimeFreeze] = useState(false);
  const [hintTiles, setHintTiles] = useState<{from: Position, to: Position} | null>(null);
  const [showHint, setShowHint] = useState(false);
  const dragStartPos = useRef<{x: number, y: number} | null>(null);
  const hintTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const playerMovedRef = useRef(false);
  
  // Get dynamic grid size based on current level
  const gridSize = getGridSize(gameState.currentLevel);
  const tileSize = gridSize <= 6 ? 64 : gridSize <= 7 ? 56 : gridSize <= 8 ? 48 : 42;
  
  useEffect(() => {
    playerMovedRef.current = false;
  }, [gameState.currentLevel]);

  // Hint system - show bouncing hint after inactivity
  const resetHintTimer = useCallback(() => {
    lastActivityRef.current = Date.now();
    setShowHint(false);
    
    if (hintTimeoutRef.current) {
      clearTimeout(hintTimeoutRef.current);
    }
    
    hintTimeoutRef.current = setTimeout(() => {
      if (board.length > 0 && !animating && !cascading) {
        const bestMove = findBestMove(board);
        if (bestMove) {
          setHintTiles(bestMove);
          setShowHint(true);
        }
      }
    }, HINT_DELAY);
  }, [board, animating, cascading]);
  
  // Reset hint timer on any user interaction
  useEffect(() => {
    resetHintTimer();
    return () => {
      if (hintTimeoutRef.current) {
        clearTimeout(hintTimeoutRef.current);
      }
    };
  }, [resetHintTimer, board]);
  
  // Animate score when it changes
  useEffect(() => {
    if (gameState.score > lastScore) {
      setScoreAnimation(true);
      const timer = setTimeout(() => setScoreAnimation(false), 800);
      setLastScore(gameState.score);
      return () => clearTimeout(timer);
    }
  }, [gameState.score, lastScore]);

  // Change season based on level
  useEffect(() => {
    const seasonIndex = Math.floor((gameState.currentLevel - 1) / 3) % 4;
    setCurrentSeason(seasonIndex as SeasonTheme);
  }, [gameState.currentLevel]);

  // Reference to track cascade state without triggering re-renders
  const cascadeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isProcessingRef = useRef(false);
  
  // Check for matches and handle cascading (like Candy Crush)
  useEffect(() => {
    // Prevent concurrent processing
    if (animating || board.length === 0 || isProcessingRef.current) {
      return;
    }
    
    // Clear any existing timeout
    if (cascadeTimeoutRef.current) {
      clearTimeout(cascadeTimeoutRef.current);
    }
    
    // Delay before checking - longer for cascades to allow visual settling
    const checkDelay = cascading ? 400 : 100;
    
    cascadeTimeoutRef.current = setTimeout(() => {
      import("@/lib/gameLogic").then(({ findMatches, hasValidMoves, findRescuePositions }) => {
        const matches = findMatches(board, activePowerUps, specialDinos);
        
        if (matches.length > 0) {
          isProcessingRef.current = true;
          setCascading(true);

          if (playerMovedRef.current) {
            playCrush();
          }
          
          const powerUpMatches = matches.filter(pos => {
            const key = `${pos.x}-${pos.y}`;
            return activePowerUps[key];
          });
          
          powerUpMatches.forEach(pos => {
            const key = `${pos.x}-${pos.y}`;
            const powerUp = activePowerUps[key];
            if (powerUp) {
              activatePowerUp(pos.x, pos.y, powerUp);
            }
          });
          
          // Calculate points - base 10 per tile
          let points = matches.length * 10;
          
          // Bonus for larger matches (4+)
          if (matches.length === 4) {
            points += 15;
          } else if (matches.length === 5) {
            points += 30;
          } else if (matches.length >= 6) {
            points += 60;
          }
          
          // Cascade combo bonus - increases with each cascade level
          const currentCombo = comboCount;
          if (currentCombo > 0) {
            points += currentCombo * 10;
            addCombo(1);
            console.log(`🔥 Cascade x${currentCombo + 1}! +${currentCombo * 10} bonus`);
          }
          
          addScore(Math.round(points * scoreMultiplier));
          setComboCount(prev => prev + 1);
          
          // Remove matches with a delay for visual effect
          setTimeout(() => {
            removeMatches(matches);
            onBoardUpdate(true);
            isProcessingRef.current = false;
            // Board will update, triggering this effect again for next cascade
          }, 200);
          
        } else {
          // No matches found - cascade complete
          if (cascading) {
            console.log(`✅ Cascade complete! ${comboCount} combo(s)`);
          }
          setCascading(false);
          setComboCount(0);
          onBoardUpdate(false);
          
          // Check if there are any valid moves left
          const movesAvailable = hasValidMoves(board);
          if (!movesAvailable) {
            rescueBoard(board, findRescuePositions);
          }
        }
      });
    }, checkDelay);
    
    return () => {
      if (cascadeTimeoutRef.current) {
        clearTimeout(cascadeTimeoutRef.current);
      }
    };
  }, [animating, board, cascading]);

  const handleTileClick = (x: number, y: number) => {
    if (animating) return;
    
    const specialKey = `${x}-${y}`;
    const specialDino = specialDinos[specialKey];
    const powerUp = activePowerUps[specialKey];
    
    // Handle power-up activation
    if (powerUp) {
      activatePowerUp(x, y, powerUp);
      return;
    }
    
    // Handle special dinosaur activation
    if (specialDino) {
      activateSpecialDino(x, y, specialDino);
      return;
    }
    
    if (selectedTile) {
      const dx = Math.abs(selectedTile.x - x);
      const dy = Math.abs(selectedTile.y - y);
      
      if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
        if (!wouldCreateMatch(board, selectedTile, { x, y })) {
          setSelectedTile({ x, y });
          return;
        }
        playerMovedRef.current = true;
        setAnimating(true);
        playHit();
        addMove();
        swapTiles(selectedTile, { x, y });
        setSelectedTile(null);
        setTimeout(() => {
          setAnimating(false);
        }, ANIMATION_DURATION);
      } else {
        setSelectedTile({ x, y });
      }
    } else {
      // No tile selected, so select this one
      setSelectedTile({ x, y });
    }
  };

  // Function to activate special dinosaur powers with enhanced effects
  const activateSpecialDino = (x: number, y: number, specialType: SpecialDinoType) => {
    setAnimating(true);
    playSuccess();
    
    let eliminatedTiles: {x: number, y: number}[] = [];
    let bonusPoints = 0;
    let isDoubleEffect = false;
    
    // Check for combinations with other special dinosaurs
    const nearbySpecials = findNearbySpecialDinos(x, y);
    if (nearbySpecials.length > 0) {
      isDoubleEffect = true;
      bonusPoints += 200; // Bonus for combining specials
    }
    
    switch (specialType) {
      case SpecialDinoType.RowCrusher:
        // Eliminate entire row(s)
        const rowsToEliminate = isDoubleEffect ? [y-1, y, y+1] : [y];
        rowsToEliminate.forEach(row => {
          if (row >= 0 && row < board.length) {
            for (let col = 0; col < board[0].length; col++) {
              eliminatedTiles.push({ x: col, y: row });
            }
          }
        });
        bonusPoints += isDoubleEffect ? 300 : 150;
        break;
        
      case SpecialDinoType.ColumnCrusher:
        // Eliminate entire column(s)
        const colsToEliminate = isDoubleEffect ? [x-1, x, x+1] : [x];
        colsToEliminate.forEach(col => {
          if (col >= 0 && col < board[0].length) {
            for (let row = 0; row < board.length; row++) {
              eliminatedTiles.push({ x: col, y: row });
            }
          }
        });
        bonusPoints += isDoubleEffect ? 300 : 150;
        break;
        
      case SpecialDinoType.ColorBomb:
        // Eliminate all dinosaurs of the same type(s) on the board
        const targetTypes = isDoubleEffect 
          ? [board[y][x], ...nearbySpecials.map(pos => board[pos.y][pos.x])]
          : [board[y][x]];
        
        targetTypes.forEach(targetType => {
          for (let row = 0; row < board.length; row++) {
            for (let col = 0; col < board[row].length; col++) {
              if (board[row][col] === targetType) {
                eliminatedTiles.push({ x: col, y: row });
              }
            }
          }
        });
        bonusPoints += isDoubleEffect ? 600 : 300;
        break;
        
      case SpecialDinoType.MegaBomb:
        // Eliminate larger area around the clicked tile
        const radius = isDoubleEffect ? 2 : 1;
        for (let dy = -radius; dy <= radius; dy++) {
          for (let dx = -radius; dx <= radius; dx++) {
            const newX = x + dx;
            const newY = y + dy;
            if (newX >= 0 && newX < board[0].length && newY >= 0 && newY < board.length) {
              eliminatedTiles.push({ x: newX, y: newY });
            }
          }
        }
        bonusPoints += isDoubleEffect ? 400 : 200;
        break;
        
      case SpecialDinoType.TimeWarp:
        // Freeze time and add extra moves
        setTimeFreeze(true);
        setExtraMoves(prev => prev + (isDoubleEffect ? 10 : 5));
        setTimeout(() => setTimeFreeze(false), isDoubleEffect ? 15000 : 10000);
        bonusPoints += isDoubleEffect ? 300 : 150;
        break;
        
      case SpecialDinoType.ScoreBurst:
        // Multiply next few match scores
        setScoreMultiplier(isDoubleEffect ? 5 : 3);
        setTimeout(() => setScoreMultiplier(1), isDoubleEffect ? 20000 : 15000);
        bonusPoints += isDoubleEffect ? 250 : 125;
        break;
        
      case SpecialDinoType.ElementalBlast:
        // Clear all tiles of the same type
        const targetType = board[y][x];
        for (let row = 0; row < board.length; row++) {
          for (let col = 0; col < board[row].length; col++) {
            if (board[row][col] === targetType) {
              eliminatedTiles.push({ x: col, y: row });
            }
          }
        }
        bonusPoints += isDoubleEffect ? 500 : 250;
        break;
        
      case SpecialDinoType.ChainLightning:
        // Create cascading explosions
        const chainRadius = isDoubleEffect ? 3 : 2;
        for (let dy = -chainRadius; dy <= chainRadius; dy++) {
          for (let dx = -chainRadius; dx <= chainRadius; dx++) {
            const newX = x + dx;
            const newY = y + dy;
            if (newX >= 0 && newX < board[0].length && newY >= 0 && newY < board.length) {
              eliminatedTiles.push({ x: newX, y: newY });
            }
          }
        }
        bonusPoints += isDoubleEffect ? 600 : 300;
        break;
        
      case SpecialDinoType.WildCard:
        // Acts as any dinosaur type - create multiple matches
        const surroundingTypes = new Set<DinoType>();
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const newX = x + dx;
            const newY = y + dy;
            if (newX >= 0 && newX < board[0].length && newY >= 0 && newY < board.length) {
              surroundingTypes.add(board[newY][newX]);
            }
          }
        }
        
        // Eliminate all surrounding types
        surroundingTypes.forEach(type => {
          for (let row = 0; row < board.length; row++) {
            for (let col = 0; col < board[row].length; col++) {
              if (board[row][col] === type) {
                eliminatedTiles.push({ x: col, y: row });
              }
            }
          }
        });
        bonusPoints += isDoubleEffect ? 800 : 400;
        break;
    }
    
    // Create dramatic visual effects
    createSpecialEffects(x, y, specialType, isDoubleEffect);
    
    // Animate elimination with staggered effects
    animateEliminationSequence(eliminatedTiles, () => {
      // Remove special dinosaurs from tracking
      setSpecialDinos(prev => {
        const newSpecials = { ...prev };
        delete newSpecials[`${x}-${y}`];
        nearbySpecials.forEach(pos => {
          delete newSpecials[`${pos.x}-${pos.y}`];
        });
        return newSpecials;
      });
      
      // Add bonus points and combo
      addScore(bonusPoints);
      setComboCount(prev => prev + (isDoubleEffect ? 2 : 1));
      
      // Trigger cascading after elimination
      cascadeAndCheckMatches(eliminatedTiles);
    });
  };

  // Find nearby special dinosaurs for combination effects
  const findNearbySpecialDinos = (x: number, y: number): {x: number, y: number}[] => {
    const nearby: {x: number, y: number}[] = [];
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (dx === 0 && dy === 0) continue;
        const newX = x + dx;
        const newY = y + dy;
        if (newX >= 0 && newX < board[0].length && newY >= 0 && newY < board.length) {
          const specialKey = `${newX}-${newY}`;
          if (specialDinos[specialKey]) {
            nearby.push({ x: newX, y: newY });
          }
        }
      }
    }
    return nearby;
  };

  // Animate elimination sequence with visual effects
  const animateEliminationSequence = (tiles: {x: number, y: number}[], callback: () => void) => {
    // Mark tiles as eliminating for animation
    const eliminatingKeys: {[key: string]: boolean} = {};
    tiles.forEach(tile => {
      eliminatingKeys[`${tile.x}-${tile.y}`] = true;
    });
    setEliminatingTiles(eliminatingKeys);
    
    // Stagger the elimination animation
    tiles.forEach((tile, index) => {
      setTimeout(() => {
        // Add explosion effect here if needed
      }, index * 50);
    });
    
    // Complete elimination after animation
    setTimeout(() => {
      setEliminatingTiles({});
      callback();
    }, ANIMATION_DURATION + tiles.length * 50);
  };

  // Enhanced cascading system similar to Candy Crush
  const cascadeAndCheckMatches = async (eliminatedTiles: {x: number, y: number}[]) => {
    setCascading(true);
    
    // Create a copy of the board for manipulation
    let newBoard = board.map(row => [...row]);
    
    // Remove eliminated tiles
    eliminatedTiles.forEach(tile => {
      newBoard[tile.y][tile.x] = DinoType.Red; // Temporary placeholder
    });
    
    // Apply gravity - make tiles fall down
    for (let col = 0; col < newBoard[0].length; col++) {
      let writeIndex = newBoard.length - 1;
      
      // Start from bottom and move up
      for (let row = newBoard.length - 1; row >= 0; row--) {
        if (!eliminatedTiles.some(tile => tile.x === col && tile.y === row)) {
          if (writeIndex !== row) {
            newBoard[writeIndex][col] = newBoard[row][col];
            newBoard[row][col] = DinoType.Red; // Clear old position
          }
          writeIndex--;
        }
      }
      
      // Fill empty spaces at top with new random dinosaurs
      for (let row = 0; row <= writeIndex; row++) {
        newBoard[row][col] = getRandomDinoType(gameState.currentLevel);
      }
    }
    
    // Update the board through the store
    // This will trigger the match detection automatically
    setTimeout(() => {
      removeMatches(eliminatedTiles);
      setCascading(false);
      setAnimating(false);
    }, ANIMATION_DURATION * 2);
  };

  // Drag and drop handlers
  const handleDragStart = (x: number, y: number, e: React.DragEvent) => {
    if (animating || cascading) {
      e.preventDefault();
      return;
    }
    setDragging({ x, y });
    dragStartPos.current = { x, y };
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = () => {
    setDragging(null);
    setDragTarget(null);
    dragStartPos.current = null;
  };

  const handleDrop = (x: number, y: number, e: React.DragEvent) => {
    e.preventDefault();
    if (!dragStartPos.current || animating || cascading) return;
    
    const startPos = dragStartPos.current;
    if (isAdjacent(startPos, { x, y })) {
      performSwap(startPos, { x, y });
    }
    
    setDragging(null);
    setDragTarget(null);
    dragStartPos.current = null;
  };

  // Mouse handlers for desktop drag
  const handleMouseDown = (x: number, y: number, e: React.MouseEvent) => {
    if (animating || cascading) return;
    dragStartPos.current = { x, y };
  };

  const handleMouseUp = (x: number, y: number) => {
    if (!dragStartPos.current || animating || cascading) return;
    
    const startPos = dragStartPos.current;
    if (startPos.x !== x || startPos.y !== y) {
      if (isAdjacent(startPos, { x, y })) {
        performSwap(startPos, { x, y });
      }
    }
    
    dragStartPos.current = null;
    setDragTarget(null);
  };

  const handleMouseEnter = (x: number, y: number) => {
    if (dragStartPos.current && !animating && !cascading) {
      setDragTarget({ x, y });
    }
  };

  // Touch handlers for mobile
  const handleTouchStart = (x: number, y: number, e: React.TouchEvent) => {
    if (animating || cascading) return;
    dragStartPos.current = { x, y };
    setDragging({ x, y });
  };

  const handleTouchEnd = (x: number, y: number) => {
    if (!dragStartPos.current || animating || cascading) return;
    
    const startPos = dragStartPos.current;
    if (dragTarget && isAdjacent(startPos, dragTarget)) {
      performSwap(startPos, dragTarget);
    }
    
    setDragging(null);
    setDragTarget(null);
    dragStartPos.current = null;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!dragStartPos.current || animating || cascading) return;
    
    const touch = e.touches[0];
    const element = document.elementFromPoint(touch.clientX, touch.clientY);
    if (element && element.getAttribute('data-tile')) {
      const [x, y] = element.getAttribute('data-tile')!.split('-').map(Number);
      setDragTarget({ x, y });
    }
  };

  // Enhanced swap function with validation
  const performSwap = async (pos1: {x: number, y: number}, pos2: {x: number, y: number}) => {
    if (!wouldCreateMatch(board, pos1, pos2)) {
      return;
    }
    playerMovedRef.current = true;
    setAnimating(true);
    playHit();
    addMove();
    swapTiles(pos1, pos2);
    setTimeout(() => {
      setAnimating(false);
    }, ANIMATION_DURATION);
  };

  // Check if two positions are adjacent
  const isAdjacent = (pos1: {x: number, y: number}, pos2: {x: number, y: number}): boolean => {
    const dx = Math.abs(pos1.x - pos2.x);
    const dy = Math.abs(pos1.y - pos2.y);
    return (dx === 1 && dy === 0) || (dx === 0 && dy === 1);
  };

  // Generate random special abilities for 6+ matches
  const getRandomSpecialAbility = (): SpecialDinoType => {
    const abilities = [
      SpecialDinoType.TimeWarp,
      SpecialDinoType.ScoreBurst,
      SpecialDinoType.ElementalBlast,
      SpecialDinoType.ChainLightning,
      SpecialDinoType.WildCard
    ];
    return abilities[Math.floor(Math.random() * abilities.length)];
  };

  // Activate power-up at position
  const activatePowerUp = (x: number, y: number, powerUpType: PowerUpType) => {
    setAnimating(true);
    playSuccess();
    
    const powerUpKey = `${x}-${y}`;
    
    switch (powerUpType) {
      case PowerUpType.TimeBonus:
        setExtraMoves(prev => prev + 5);
        break;
      case PowerUpType.ScoreMultiplier:
        setScoreMultiplier(prev => prev * 2);
        setTimeout(() => setScoreMultiplier(1), 10000);
        break;
      case PowerUpType.ExtraMoves:
        setExtraMoves(prev => prev + 3);
        break;
      case PowerUpType.MagicWand:
        // Transform random tiles to create matches
        const randomType = Math.floor(Math.random() * 5) as DinoType;
        for (let i = 0; i < 3; i++) {
          const randX = Math.floor(Math.random() * board[0].length);
          const randY = Math.floor(Math.random() * board.length);
          // This would need to update the board through the store
        }
        break;
      case PowerUpType.ChainReaction:
        // Create multiple small explosions
        for (let i = 0; i < 3; i++) {
          setTimeout(() => {
            const randX = Math.floor(Math.random() * board[0].length);
            const randY = Math.floor(Math.random() * board.length);
            activateSpecialDino(randX, randY, SpecialDinoType.MegaBomb);
          }, i * 500);
        }
        break;
    }
    
    // Remove the used power-up
    setActivePowerUps(prev => {
      const newPowerUps = { ...prev };
      delete newPowerUps[powerUpKey];
      return newPowerUps;
    });
    
    addScore(100); // Bonus for using power-up
    setTimeout(() => setAnimating(false), ANIMATION_DURATION);
  };

  // Generate random power-ups at empty positions
  const generateRandomPowerUp = (matchPositions: Position[]) => {
    const powerUpTypes = [
      PowerUpType.TimeBonus,
      PowerUpType.ScoreMultiplier,
      PowerUpType.ExtraMoves,
      PowerUpType.MagicWand,
      PowerUpType.ChainReaction
    ];
    
    // Find empty positions around matches
    const emptyPositions: Position[] = [];
    matchPositions.forEach(pos => {
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const newX = pos.x + dx;
          const newY = pos.y + dy;
          if (newX >= 0 && newX < board[0].length && newY >= 0 && newY < board.length) {
            const key = `${newX}-${newY}`;
            if (!powerUps[key] && !specialDinos[key]) {
              emptyPositions.push({ x: newX, y: newY });
            }
          }
        }
      }
    });
    
    // Place 1-2 random power-ups
    const numPowerUps = Math.min(Math.floor(Math.random() * 2) + 1, emptyPositions.length);
    for (let i = 0; i < numPowerUps; i++) {
      const randomPos = emptyPositions[Math.floor(Math.random() * emptyPositions.length)];
      const randomPowerUp = powerUpTypes[Math.floor(Math.random() * powerUpTypes.length)];
      const key = `${randomPos.x}-${randomPos.y}`;
      
      setActivePowerUps(prev => ({ ...prev, [key]: randomPowerUp }));
      
      // Remove used position
      const index = emptyPositions.indexOf(randomPos);
      if (index > -1) emptyPositions.splice(index, 1);
    }
  };

  // Board rescue system - shuffles board when no moves are available
  const rescueBoard = (currentBoard: DinoType[][], findRescuePositions: any) => {
    console.log('🚨 No valid moves detected! Shuffling board...');
    setBoardRescuing(true);
    
    // Just shuffle the board instead of adding special tiles
    shuffleBoard();
    playSuccess();
    
    setTimeout(() => setBoardRescuing(false), 500);
  };
  
  // Fallback function to shuffle the entire board - creates board with guaranteed valid moves
  const shuffleBoard = () => {
    // Use createBoard which guarantees valid moves exist
    const newBoard = createBoard(gameState.currentLevel);
    setBoard(newBoard);
    console.log('🔄 Board regenerated with guaranteed valid moves');
  };

  // Create dramatic visual effects for special dinosaur activation
  const createSpecialEffects = (x: number, y: number, specialType: SpecialDinoType, isDoubleEffect: boolean) => {
    // Add screen shake effect
    document.body.style.animation = 'screenShake 0.6s ease-in-out';
    setTimeout(() => {
      document.body.style.animation = '';
    }, 600);

    // Create board-wide flash effect based on special type
    const boardElement = document.querySelector('[data-board]');
    if (boardElement) {
      let flashColor = '#ffffff';
      switch (specialType) {
        case SpecialDinoType.RowCrusher:
          flashColor = '#ff4444';
          break;
        case SpecialDinoType.ColumnCrusher:
          flashColor = '#4444ff';
          break;
        case SpecialDinoType.ColorBomb:
          flashColor = '#ff44ff';
          break;
        case SpecialDinoType.MegaBomb:
          flashColor = '#ffff44';
          break;
      }
      
      (boardElement as HTMLElement).style.boxShadow = `0 0 ${isDoubleEffect ? '60px' : '30px'} ${flashColor}`;
      (boardElement as HTMLElement).style.transition = 'all 0.3s ease-out';
      
      setTimeout(() => {
        (boardElement as HTMLElement).style.boxShadow = '';
      }, 600);
    }
  };

  if (!board.length) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <p className="text-white">Loading game board...</p>
      </div>
    );
  }
  
  return (
    <div className="flex flex-col items-center relative">
      {/* Board rescue notification */}
      {boardRescuing && (
        <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-4 z-50">
          <div className="bg-green-500 text-white px-4 py-2 rounded-lg font-bold rescue-sparkle">
            🎯 Board Rescue! Special tiles incoming...
          </div>
        </div>
      )}
      {/* Seasonal floating effects */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="absolute animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${3 + Math.random() * 2}s`
            }}
          >
            <span className="text-2xl opacity-30">
              {seasonalEffects[currentSeason]}
            </span>
          </div>
        ))}
      </div>

      <div 
        data-board 
        className={`grid gap-1 p-3 rounded-xl shadow-2xl border-2 relative ${seasonalBackgrounds[currentSeason]}`}
        style={{ 
          gridTemplateColumns: `repeat(${gridSize}, 1fr)`,
          touchAction: 'none'
        }}
      >
        {board.map((row, y) => 
          row.map((tile, x) => {
            const powerUpKey = `${x}-${y}`;
            const hasPowerUp = powerUps[powerUpKey];
            const specialDino = specialDinos[powerUpKey];
            const isSpecial = specialDino !== undefined && specialDino !== SpecialDinoType.Normal;
            const isEliminating = eliminatingTiles[powerUpKey];
            const isDraggingTile = dragging?.x === x && dragging?.y === y;
            const isDragTarget = dragTarget?.x === x && dragTarget?.y === y;
            const isHintTile = showHint && hintTiles && (
              (hintTiles.from.x === x && hintTiles.from.y === y) ||
              (hintTiles.to.x === x && hintTiles.to.y === y)
            );
            
            return (
              <div 
                key={`${x}-${y}`} 
                data-tile={`${x}-${y}`}
                className={`flex items-center justify-center rounded-lg cursor-pointer 
                  transition-all duration-200 border-2 relative select-none
                  ${selectedTile?.x === x && selectedTile?.y === y 
                    ? 'ring-4 ring-yellow-400 scale-110 z-10 shadow-2xl border-yellow-300'
                    : 'hover:ring-2 hover:ring-white hover:scale-105 shadow-lg border-white/30'}
                  ${hasPowerUp || isSpecial ? 'animate-bounce' : ''}
                  ${isEliminating ? 'scale-75 opacity-50' : ''}
                  ${isDraggingTile ? 'scale-125 z-20 rotate-6 opacity-80' : ''}
                  ${isDragTarget ? 'ring-2 ring-green-400 bg-green-100/20 scale-105' : ''}
                  ${isHintTile ? 'animate-hint-bounce' : ''}`}
                style={{ 
                  width: `${tileSize}px`,
                  height: `${tileSize}px`,
                  backgroundColor: '#1a1a2e',
                  borderColor: isSpecial ? '#ff1744' : hasPowerUp ? '#ffd700' : isHintTile ? '#00ff88' : 'rgba(255,255,255,0.3)',
                  boxShadow: selectedTile?.x === x && selectedTile?.y === y 
                    ? '0 0 20px rgba(255, 255, 0, 0.6)'
                    : isHintTile ? '0 0 25px rgba(0, 255, 136, 0.8), 0 0 10px rgba(0, 255, 136, 0.4)' 
                    : isSpecial ? '0 0 20px rgba(255, 23, 68, 0.7)' 
                    : hasPowerUp ? '0 0 15px rgba(255, 215, 0, 0.5)' : 'none',
                  filter: isSpecial ? 'drop-shadow(0 4px 8px rgba(255, 23, 68, 0.3)) drop-shadow(0 0 15px rgba(255, 107, 53, 0.5))' : 'none',
                  overflow: 'hidden',
                }}
                onClick={() => { resetHintTimer(); handleTileClick(x, y); }}
                onMouseDown={(e) => { resetHintTimer(); handleMouseDown(x, y, e); }}
                onMouseUp={() => handleMouseUp(x, y)}
                onMouseEnter={() => handleMouseEnter(x, y)}
                onTouchStart={(e) => { resetHintTimer(); handleTouchStart(x, y, e); }}
                onTouchEnd={() => handleTouchEnd(x, y)}
                onTouchMove={(e) => handleTouchMove(e)}
                draggable={true}
                onDragStart={(e) => { resetHintTimer(); handleDragStart(x, y, e); }}
                onDragEnd={() => handleDragEnd()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => handleDrop(x, y, e)}
              >
                {/* Special power-up dinosaur indicator - only show small glow border */}
                {isSpecial && (
                  <div className="absolute inset-0 rounded-lg border-2 border-yellow-400 animate-pulse z-10" />
                )}
                
                {/* Power-up indicator */}
                {hasPowerUp && !isSpecial && (
                  <div className="absolute -top-1 -right-1 text-xs bg-yellow-400 rounded-full w-5 h-5 flex items-center justify-center font-bold text-black z-20">
                    💥
                  </div>
                )}
                
                {/* Crush/elimination explosion effect */}
                {isEliminating && (
                  <div className="absolute inset-0 flex items-center justify-center z-30">
                    <div className="text-4xl animate-ping">💥</div>
                  </div>
                )}
                
                {/* Main dinosaur image - simple and clean */}
                <img 
                  src={getDinoImage(tile)}
                  alt="dinosaur"
                  className={`w-full h-full object-contain p-1
                    ${isEliminating ? 'dino-crush' : selectedTile?.x === x && selectedTile?.y === y ? 'dino-selected' : getDinoIdleClass(tile)}`}
                  style={{
                    animationDelay: `${((x * 3 + y * 7) % 11) * 0.11}s`,
                    filter: isEliminating ? 'blur(2px)' : 'drop-shadow(2px 2px 3px rgba(0,0,0,0.5))'
                  }}
                />
              </div>
            );
          })
        )}
      </div>

      <div className={`mt-6 p-4 rounded-lg w-full max-w-md border shadow-lg ${seasonalBackgrounds[currentSeason]} border-white/30`}>
        <div className="flex justify-between items-center text-white mb-2">
          <div className="flex flex-col">
            <span className="text-sm text-white/80">SCORE</span>
            <span className={`text-2xl font-bold ${scoreAnimation ? 'animate-bounce text-yellow-300' : ''}`}>
              {gameState.score}
            </span>
          </div>
          
          <div className="flex flex-col items-center">
            <span className="text-sm text-white/80">COMBO</span>
            <span className={`text-xl font-bold ${comboCount > 0 ? 'text-orange-300 animate-pulse' : 'text-white'}`}>
              {comboCount > 0 ? `${comboCount}x` : '0x'}
            </span>
          </div>
          
          <div className="flex flex-col items-end">
            <span className="text-sm text-white/80">GOAL</span>
            <span className="text-2xl font-bold">{LEVEL_GOALS[gameState.currentLevel - 1]}</span>
          </div>
        </div>
        
        <div className="w-full bg-black/30 rounded-full h-4 overflow-hidden border border-white/20">
          <div 
            className="bg-gradient-to-r from-emerald-400 to-green-300 h-4 rounded-full transition-all duration-500" 
            style={{ 
              width: `${Math.min(100, (gameState.score / LEVEL_GOALS[gameState.currentLevel - 1]) * 100)}%` 
            }}
          >
            {gameState.score >= LEVEL_GOALS[gameState.currentLevel - 1] * 0.95 && 
              <div className="h-full w-full animate-pulse bg-yellow-400 opacity-40"></div>
            }
          </div>
        </div>
        
        <div className="mt-3 flex justify-between items-center text-xs text-white/80">
          <span>Level {gameState.currentLevel}</span>
          <span className="flex items-center gap-1">
            {seasonalEffects[currentSeason]} 
            {currentSeason === SeasonTheme.Spring && "Spring"}
            {currentSeason === SeasonTheme.Summer && "Summer"}
            {currentSeason === SeasonTheme.Autumn && "Autumn"}
            {currentSeason === SeasonTheme.Winter && "Winter"}
          </span>
          <span>Match dinosaurs!</span>
        </div>
      </div>
    </div>
  );
};

export default SimpleBoard;