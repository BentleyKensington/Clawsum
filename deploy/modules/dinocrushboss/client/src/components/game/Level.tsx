import { useEffect } from "react";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { useGame } from "@/lib/stores/useGame";
import { LEVEL_GOALS } from "@/lib/constants";

interface LevelProps {
  level: number;
  onComplete?: () => void;
}

const Level: React.FC<LevelProps> = ({ level, onComplete }) => {
  const { gameState, setCurrentLevel, resetBoard, setScore, setLevelComplete } = useDinoCrush();
  const { end } = useGame();
  
  // Initialize level
  useEffect(() => {
    console.log(`Initializing level ${level}`);
    setCurrentLevel(level);
    resetBoard();
    setScore(0);
    setLevelComplete(false);
  }, [level, setCurrentLevel, resetBoard, setScore, setLevelComplete]);
  
  // Check for level completion
  useEffect(() => {
    const levelGoal = LEVEL_GOALS[level - 1];
    if (gameState.score >= levelGoal && !gameState.levelComplete) {
      console.log(`Level ${level} complete!`);
      setLevelComplete(true);
      end();
      if (onComplete) {
        onComplete();
      }
    }
  }, [gameState.score, gameState.levelComplete, level, setLevelComplete, end, onComplete]);
  
  return null; // This is a logic component with no UI
};

export default Level;
