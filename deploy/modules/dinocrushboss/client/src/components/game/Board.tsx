import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useThree } from "@react-three/fiber";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { useAudio } from "@/lib/stores/useAudio";
import DinoTile from "./DinoTile";
import { findMatches, createBoard } from "@/lib/gameLogic";
import { DinoType, Position } from "@/types/game";
import { BOARD_SIZE, TILE_SIZE, ANIMATION_DURATION } from "@/lib/constants";

interface BoardProps {
  onBoardUpdate: (hasMatches: boolean) => void;
}

export const Board = ({ onBoardUpdate }: BoardProps) => {
  const { gameState, setBoard, setSelectedTile, selectedTile, swapTiles, removeMatches, addScore } = useDinoCrush();
  const { playHit, playSuccess } = useAudio();
  const { board } = gameState;
  const [animating, setAnimating] = useState(false);
  const [dragStart, setDragStart] = useState<Position | null>(null);
  const boardContainerRef = useRef<THREE.Group>(null);
  const { size } = useThree();
  
  // Initialize the board
  useEffect(() => {
    if (!board.length) {
      const newBoard = createBoard();
      setBoard(newBoard);
    }
  }, [board, setBoard]);

  // Check for matches after animations complete
  useEffect(() => {
    if (!animating && board.length > 0) {
      const matches = findMatches(board);
      if (matches.length > 0) {
        playSuccess();
        addScore(matches.length * 10);
        removeMatches(matches);
        onBoardUpdate(true);
      } else {
        onBoardUpdate(false);
      }
    }
  }, [animating, board, removeMatches, addScore, playSuccess, onBoardUpdate]);

  const handleTileClick = (x: number, y: number) => {
    if (animating) return;
    
    if (selectedTile) {
      // If already have a selected tile, check if this is an adjacent tile
      const dx = Math.abs(selectedTile.x - x);
      const dy = Math.abs(selectedTile.y - y);
      
      if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
        setAnimating(true);
        playHit();
        
        // Swap tiles
        swapTiles(selectedTile, { x, y });
        
        // Clear selection
        setSelectedTile(null);
        
        // Set timeout to complete animation before checking matches
        setTimeout(() => {
          setAnimating(false);
        }, ANIMATION_DURATION);
      } else {
        // Select new tile if not adjacent
        setSelectedTile({ x, y });
      }
    } else {
      // No tile selected, so select this one
      setSelectedTile({ x, y });
    }
  };

  const handleDragStart = (x: number, y: number) => {
    if (animating) return;
    setDragStart({ x, y });
  };

  const handleDragEnd = (x: number, y: number) => {
    if (animating || !dragStart) return;
    
    // Calculate the drag direction and determine if it's a valid move
    const dx = x - dragStart.x;
    const dy = y - dragStart.y;
    
    // Determine predominant direction
    if (Math.abs(dx) > Math.abs(dy)) {
      // Horizontal drag
      if (Math.abs(dx) === 1) {
        setAnimating(true);
        playHit();
        swapTiles(dragStart, { x, y });
        setTimeout(() => setAnimating(false), ANIMATION_DURATION);
      }
    } else {
      // Vertical drag
      if (Math.abs(dy) === 1) {
        setAnimating(true);
        playHit();
        swapTiles(dragStart, { x, y });
        setTimeout(() => setAnimating(false), ANIMATION_DURATION);
      }
    }
    
    setDragStart(null);
  };

  // Calculate board scale to fit the screen
  const scale = Math.min(
    size.width / (BOARD_SIZE * TILE_SIZE * 1.2),
    size.height / (BOARD_SIZE * TILE_SIZE * 1.2)
  );

  // Debug logging
  console.log("Board state:", board);
  console.log("Board dimensions:", BOARD_SIZE);
  console.log("Scale:", scale);

  return (
    <group 
      ref={boardContainerRef} 
      scale={[scale, scale, scale]} 
      position={[-(BOARD_SIZE * TILE_SIZE) / 2, -(BOARD_SIZE * TILE_SIZE) / 2, 0]}
    >
      {/* Background for the board */}
      <mesh position={[BOARD_SIZE * TILE_SIZE / 2 - TILE_SIZE / 2, BOARD_SIZE * TILE_SIZE / 2 - TILE_SIZE / 2, -0.2]} receiveShadow>
        <planeGeometry args={[BOARD_SIZE * TILE_SIZE, BOARD_SIZE * TILE_SIZE]} />
        <meshStandardMaterial color="#1a1a2e" />
      </mesh>
      
      {/* Map through all tiles in the board */}
      {board.length > 0 && board.map((row, y) => 
        row.map((tile, x) => (
          <DinoTile
            key={`${x}-${y}`}
            type={tile}
            position={[x * TILE_SIZE, y * TILE_SIZE, 0]}
            selected={selectedTile?.x === x && selectedTile?.y === y}
            onClick={() => handleTileClick(x, y)}
            onDragStart={() => handleDragStart(x, y)}
            onDragEnd={() => handleDragEnd(x, y)}
          />
        ))
      )}
    </group>
  );
};

export default Board;
