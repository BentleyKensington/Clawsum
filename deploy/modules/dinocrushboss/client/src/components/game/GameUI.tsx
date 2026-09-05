import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { LEVEL_GOALS } from "@/lib/constants";
import { useGame } from "@/lib/stores/useGame";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const GameUI: React.FC = () => {
  const { gameState } = useDinoCrush();
  const { restart } = useGame();
  const currentLevelGoal = LEVEL_GOALS[gameState.currentLevel - 1];
  const progressPercentage = Math.min(100, (gameState.score / currentLevelGoal) * 100);
  
  return (
    <div className="absolute top-0 left-0 w-full p-4 z-10">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 bg-black/60 rounded-xl p-4 backdrop-blur-sm">
        <div className="flex flex-col items-center md:items-start">
          <h2 className="text-xl font-bold text-white">Level {gameState.currentLevel}</h2>
          <p className="text-sm text-white/80">Goal: {currentLevelGoal} points</p>
        </div>
        
        <div className="flex-1 w-full max-w-md">
          <Progress value={progressPercentage} className="h-4" />
          <div className="flex justify-between mt-1">
            <span className="text-xs text-white/80">Current: {gameState.score}</span>
            <span className="text-xs text-white/80">Goal: {currentLevelGoal}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="text-2xl font-bold text-white">{gameState.score}</div>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => restart()}
            className="ml-4"
          >
            Reset
          </Button>
        </div>
      </div>
    </div>
  );
};

export default GameUI;
