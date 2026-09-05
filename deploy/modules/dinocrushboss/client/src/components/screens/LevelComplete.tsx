import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { useGame } from "@/lib/stores/useGame";
import { useAudio } from "@/lib/stores/useAudio";
import { useAuth } from "@/lib/stores/useAuth";
import { LEVEL_COUNT, LEVEL_GOALS } from "@/lib/constants";

const LevelComplete: React.FC = () => {
  const { gameState, goToNextLevel, calculateStarRating, setCurrentLevel, resetGame } = useDinoCrush();
  const { start } = useGame();
  const { playSuccess } = useAudio();
  const { user, saveLevelProgress } = useAuth();
  const [showConfetti, setShowConfetti] = useState(true);
  const savedRef = useRef(false);
  
  const isGameComplete = gameState.currentLevel >= LEVEL_COUNT;
  const nextLevelGoal = isGameComplete ? null : LEVEL_GOALS[gameState.currentLevel];
  const starRating = calculateStarRating();
  
  useEffect(() => {
    playSuccess();
    
    if (user && !savedRef.current) {
      savedRef.current = true;
      saveLevelProgress(gameState.currentLevel, gameState.score, starRating);
    }
    
    const confettiTimer = setTimeout(() => {
      setShowConfetti(false);
    }, 3000);
    
    let autoAdvanceTimer: NodeJS.Timeout | undefined;
    if (!isGameComplete) {
      autoAdvanceTimer = setTimeout(() => {
        goToNextLevel();
        start();
      }, 2000);
    }
    
    return () => {
      clearTimeout(confettiTimer);
      if (autoAdvanceTimer) clearTimeout(autoAdvanceTimer);
    };
  }, [playSuccess, isGameComplete, goToNextLevel, start, user, gameState.currentLevel, gameState.score, starRating, saveLevelProgress]);
  
  const handleNextLevel = () => {
    goToNextLevel();
    start();
  };
  
  const handleRestart = () => {
    if (isGameComplete) {
      resetGame();
      start();
      return;
    }
    setCurrentLevel(gameState.currentLevel);
    start();
  };
  
  // Create animated stars for the background
  const starCount = 20;
  const stars = Array.from({ length: starCount }).map((_, i) => ({
    id: i,
    size: Math.random() * 10 + 5,
    x: Math.random() * 100,
    y: Math.random() * 100,
    duration: Math.random() * 2 + 1,
    delay: Math.random() * 2,
  }));
  
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 bg-black/80 overflow-hidden">
      {/* Animated background stars */}
      {stars.map((star) => (
        <motion.div
          key={star.id}
          className="absolute rounded-full bg-yellow-200"
          style={{
            width: star.size,
            height: star.size,
            top: `${star.y}%`,
            left: `${star.x}%`,
            opacity: 0,
          }}
          animate={{
            opacity: [0, 0.8, 0],
            scale: [0, 1, 0],
          }}
          transition={{
            duration: star.duration,
            repeat: Infinity,
            delay: star.delay,
          }}
        />
      ))}
      
      {/* Confetti effect */}
      {showConfetti && (
        <div className="absolute inset-0 z-0">
          {Array.from({ length: 100 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-2 h-8"
              style={{
                top: -20,
                left: `${Math.random() * 100}%`,
                backgroundColor: [
                  '#ff5555', '#55ff55', '#5555ff', '#ffff55', '#ff55ff',
                ][Math.floor(Math.random() * 5)],
                transform: `rotate(${Math.random() * 360}deg)`,
              }}
              animate={{
                y: ['0vh', '100vh'],
                x: [0, Math.random() * 200 - 100],
                rotate: [0, Math.random() * 360 * (Math.random() > 0.5 ? 1 : -1)],
                opacity: [1, 0],
              }}
              transition={{
                duration: Math.random() * 2 + 2,
                ease: 'easeOut',
                delay: Math.random(),
              }}
            />
          ))}
        </div>
      )}
      
      {/* Main content */}
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", duration: 0.5 }}
        className="relative z-10 bg-gradient-to-br from-purple-900 to-indigo-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl border-2 border-yellow-400"
      >
        <div className="flex flex-col items-center text-center">
          <motion.div
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mb-6"
          >
            <h1 className="text-3xl font-bold text-yellow-300 mb-2">
              {isGameComplete ? "🏆 Game Complete! 🏆" : "🎉 Level Complete! 🎉"}
            </h1>
            <p className="text-gray-300">
              {isGameComplete 
                ? "Congratulations! You've conquered all dinosaur challenges!" 
                : `Amazing job completing level ${gameState.currentLevel}!`}
            </p>
          </motion.div>
          
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.6, type: "spring" }}
            className="my-6 bg-black/30 rounded-full p-6 border-2 border-yellow-500"
          >
            <motion.div 
              animate={{ 
                rotate: [0, 5, 0, -5, 0],
                scale: [1, 1.05, 1, 1.05, 1]
              }}
              transition={{ 
                duration: 0.5, 
                repeat: 2,
                repeatDelay: 1
              }}
              className="text-center"
            >
              <p className="text-gray-300 mb-2">Your Score</p>
              <div className="text-5xl font-bold text-white">
                {gameState.score}
              </div>
              
              {!isGameComplete && nextLevelGoal && (
                <p className="text-sm text-gray-400 mt-2">
                  Next level goal: {nextLevelGoal} points
                </p>
              )}
            </motion.div>
          </motion.div>
          
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.9 }}
            className="flex flex-col sm:flex-row gap-4 mt-6"
          >
            {!isGameComplete && (
              <Button 
                onClick={handleNextLevel}
                className="bg-green-600 hover:bg-green-700 text-white px-8 py-3 text-lg"
              >
                Next Level 👉
              </Button>
            )}
            
            <Button 
              onClick={handleRestart}
              variant="outline"
              className="border-white text-white hover:bg-white/10 px-8 py-3 text-lg"
            >
              {isGameComplete ? "Play Again 🔄" : "Retry Level 🔄"}
            </Button>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
};

export default LevelComplete;
