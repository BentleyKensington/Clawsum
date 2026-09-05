import { Suspense, useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import Board from "./Board";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { LEVEL_GOALS } from "@/lib/constants";
import { useGame } from "@/lib/stores/useGame";
import { DinoType } from "@/types/game";
import { useAudio } from "@/lib/stores/useAudio";

const dinoColors = {
  [DinoType.Red]: "#ff5555",
  [DinoType.Green]: "#55ff55",
  [DinoType.Blue]: "#5555ff",
  [DinoType.Yellow]: "#ffff55",
  [DinoType.Purple]: "#ff55ff",
};

const GameBoard: React.FC = () => {
  const { gameState, resetBoard, setLevelComplete, setSelectedTile, swapTiles } = useDinoCrush();
  const { playHit } = useAudio();
  const { end } = useGame();
  const [hasCheckedLevelCompletion, setHasCheckedLevelCompletion] = useState(false);
  
  const handleBoardUpdate = (hasMatches: boolean) => {
    if (!hasMatches && !hasCheckedLevelCompletion) {
      setHasCheckedLevelCompletion(true);
      
      // Check if level is complete
      const currentLevelGoal = LEVEL_GOALS[gameState.currentLevel - 1];
      if (gameState.score >= currentLevelGoal) {
        console.log("Level complete!", gameState.score, currentLevelGoal);
        setLevelComplete(true);
        end();
      }
    }
  };
  
  // Reset the check flag when score changes
  useEffect(() => {
    setHasCheckedLevelCompletion(false);
  }, [gameState.score]);
  
  return (
    <div className="w-full h-full relative">
      {/* Fallback Simple 2D Board */}
      <div className="absolute inset-0 z-10 bg-indigo-900 p-4 flex flex-col items-center justify-center">
        <h2 className="text-xl font-bold text-white mb-4">Dino Crush - Level {gameState.currentLevel}</h2>
        <div className="grid grid-cols-6 gap-1 bg-indigo-800 p-2 rounded-lg shadow-lg">
          {gameState.board.map((row, y) => 
            row.map((tile, x) => (
              <div 
                key={`${x}-${y}`} 
                className={`w-12 h-12 flex items-center justify-center rounded-md cursor-pointer transition-all
                  ${gameState.selectedTile?.x === x && gameState.selectedTile?.y === y 
                    ? 'ring-4 ring-yellow-400 scale-110'
                    : 'hover:ring-2 hover:ring-white hover:scale-105'}`}
                style={{ backgroundColor: dinoColors[tile] }}
                onClick={() => handleTileClick(x, y)}
              >
                <span className="text-2xl">
                  {tile === DinoType.Red ? "🦖" : 
                   tile === DinoType.Green ? "🦕" : 
                   tile === DinoType.Blue ? "🐊" : 
                   tile === DinoType.Yellow ? "🦎" : 
                   tile === DinoType.Purple ? "🐉" : "?"}
                </span>
              </div>
            ))
          )}
        </div>
        <div className="mt-4 bg-indigo-800 p-2 rounded-lg w-full max-w-md">
          <div className="flex justify-between text-white mb-1">
            <span>Score: {gameState.score}</span>
            <span>Goal: {LEVEL_GOALS[gameState.currentLevel - 1]}</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-4">
            <div 
              className="bg-green-500 h-4 rounded-full transition-all" 
              style={{ 
                width: `${Math.min(100, (gameState.score / LEVEL_GOALS[gameState.currentLevel - 1]) * 100)}%` 
              }}
            ></div>
          </div>
        </div>
      </div>

      {/* Original 3D Canvas (hidden) */}
      <div className="absolute inset-0 z-0 opacity-0 pointer-events-none">
        <Canvas gl={{ antialias: true }} shadows>
          <Suspense fallback={null}>
            <PerspectiveCamera makeDefault position={[0, 0, 15]} />
            <ambientLight intensity={0.7} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <Board onBoardUpdate={handleBoardUpdate} />
          </Suspense>
        </Canvas>
      </div>
    </div>
  );
  
  function handleTileClick(x: number, y: number) {
    if (!gameState.board.length) return;
    
    if (gameState.selectedTile) {
      // If already have a selected tile, check if this is an adjacent tile
      const dx = Math.abs(gameState.selectedTile.x - x);
      const dy = Math.abs(gameState.selectedTile.y - y);
      
      if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
        playHit();
        
        // Swap tiles
        swapTiles(gameState.selectedTile, { x, y });
        
        // Clear selection
        setSelectedTile(null);
      } else {
        // Select new tile if not adjacent
        setSelectedTile({ x, y });
      }
    } else {
      // No tile selected, so select this one
      setSelectedTile({ x, y });
    }
  }
};

export default GameBoard;
