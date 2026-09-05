import { useEffect, useState } from "react";
import { useAudio } from "@/lib/stores/useAudio";
import SimpleBoard from "../game/SimpleBoard";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { useGame } from "@/lib/stores/useGame";
import { LEVEL_GOALS, LEVEL_MECHANICS, STAR_REQUIREMENTS } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import HowToPlayPanel from "./HowToPlayPanel";

const GameScreen: React.FC = () => {
  const { gameState, setLevelComplete, totalMoves, totalCombos, setCurrentLevel, startLevel } = useDinoCrush();
  const { isMuted, toggleMute, unlockAudio } = useAudio();
  const { restart, end } = useGame();
  const [hasCheckedLevelCompletion, setHasCheckedLevelCompletion] = useState(false);
  const [comboAnimation, setComboAnimation] = useState<number | null>(null);
  const [showMobileHelp, setShowMobileHelp] = useState(false);
  
  const currentGoal = LEVEL_GOALS[gameState.currentLevel - 1] || 100;
  const progressPercent = Math.min((gameState.score / currentGoal) * 100, 100);
  const levelMechanics = LEVEL_MECHANICS[gameState.currentLevel] || { moveLimit: undefined };
  const starReqs = STAR_REQUIREMENTS[gameState.currentLevel] || { oneStarScore: currentGoal * 0.6, twoStarScore: currentGoal * 0.85, threeStarScore: currentGoal * 1.2 };
  
  const currentStars = gameState.score >= starReqs.threeStarScore ? 3 : 
                       gameState.score >= starReqs.twoStarScore ? 2 : 
                       gameState.score >= starReqs.oneStarScore ? 1 : 0;
  
  useEffect(() => {
    unlockAudio();
  }, [unlockAudio]);

  useEffect(() => {
    if (totalCombos > 0) {
      setComboAnimation(totalCombos);
      const timer = setTimeout(() => setComboAnimation(null), 1500);
      return () => clearTimeout(timer);
    }
  }, [totalCombos]);

  const handleBoardUpdate = (hasMatches: boolean) => {
    if (!hasMatches && !hasCheckedLevelCompletion) {
      setHasCheckedLevelCompletion(true);
      if (gameState.score >= currentGoal) {
        setLevelComplete(true);
        end();
      }
    }
  };

  useEffect(() => {
    setHasCheckedLevelCompletion(false);
  }, [gameState.score]);

  const handleResetLevel = () => {
    setCurrentLevel(gameState.currentLevel);
    startLevel();
  };
  
  return (
    <div className="relative w-full h-full bg-gradient-to-b from-slate-900 via-purple-900 to-indigo-950 overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-500/20 via-transparent to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-green-900/30 to-transparent" />
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute text-2xl opacity-20"
            initial={{ y: '100vh', x: `${(i * 5) % 100}%` }}
            animate={{ y: '-10vh' }}
            transition={{ duration: 15 + i * 2, repeat: Infinity, ease: 'linear', delay: i * 0.5 }}
          >
            {i % 2 === 0 ? '🦖' : '🦕'}
          </motion.div>
        ))}
      </div>
      
      {/* Main Game Layout - 3 Column */}
      <div className="relative z-10 w-full h-full flex">
        
        {/* Left Panel - How to play + rewards */}
        <div className="hidden lg:flex flex-col w-80 xl:w-96 p-4 bg-black/30 backdrop-blur-sm border-r border-white/10 min-h-0">
          <div className="text-center mb-4 shrink-0">
            <div className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-500">
              Level {gameState.currentLevel}
            </div>
            <div className="text-sm text-gray-400 mt-1">Prehistoric Challenge</div>
          </div>
          
          <div className="bg-white/5 rounded-xl p-4 mb-3 border border-white/10 shrink-0">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Target Score</div>
            <div className="text-3xl font-bold text-yellow-400">{currentGoal.toLocaleString()}</div>
          </div>
          
          <div className="bg-white/5 rounded-xl p-4 mb-3 border border-white/10 shrink-0">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-3">Star Rating</div>
            <div className="flex justify-center gap-2 text-3xl mb-2">
              {[1, 2, 3].map(star => (
                <motion.span 
                  key={star}
                  animate={{ scale: currentStars >= star ? [1, 1.2, 1] : 1 }}
                  transition={{ duration: 0.3 }}
                  className={currentStars >= star ? 'text-yellow-400 drop-shadow-lg' : 'text-gray-600'}
                >
                  ⭐
                </motion.span>
              ))}
            </div>
            <div className="text-xs text-center text-gray-500">
              ⭐ {starReqs.oneStarScore} | ⭐⭐ {starReqs.twoStarScore} | ⭐⭐⭐ {starReqs.threeStarScore}
            </div>
          </div>
          
          <div className="bg-white/5 rounded-xl p-4 border border-white/10 flex-1 min-h-0 overflow-hidden flex flex-col">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-3 shrink-0">How to Play</div>
            <HowToPlayPanel level={gameState.currentLevel} targetScore={currentGoal} />
          </div>
          
          <Button 
            onClick={restart}
            className="mt-4 w-full bg-red-600 hover:bg-red-700 text-white shrink-0"
          >
            ← Exit to Menu
          </Button>
        </div>
        
        {/* Center Panel - Game Board */}
        <div className="flex-1 flex flex-col items-center justify-center p-4">
          {/* Mobile Header */}
          <div className="lg:hidden w-full max-w-md mb-4 flex items-center justify-between bg-black/30 backdrop-blur-sm rounded-xl p-3 border border-white/10">
            <Button 
              onClick={restart}
              variant="ghost"
              className="text-white hover:bg-white/20 px-2"
            >
              ← Exit
            </Button>
            <div className="text-lg font-bold text-white">
              Level <span className="text-green-400">{gameState.currentLevel}</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setShowMobileHelp((open) => !open)}
                variant="ghost"
                className="text-white hover:bg-white/20 px-2 text-xs"
              >
                {showMobileHelp ? "Close" : "How to play"}
              </Button>
              <div className="text-yellow-400 font-bold">{gameState.score}</div>
            </div>
          </div>
          {showMobileHelp && (
            <div className="lg:hidden w-full max-w-md mb-4 bg-black/80 backdrop-blur-sm rounded-xl p-4 border border-white/10 max-h-72 overflow-y-auto">
              <HowToPlayPanel level={gameState.currentLevel} targetScore={currentGoal} compact />
            </div>
          )}
          
          {/* Combo Animation */}
          <AnimatePresence>
            {comboAnimation && comboAnimation > 1 && (
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="absolute top-20 text-4xl font-bold text-orange-400 drop-shadow-lg z-50"
              >
                {comboAnimation}x COMBO! 🔥
              </motion.div>
            )}
          </AnimatePresence>
          
          {/* Game Board */}
          <div className="relative">
            <SimpleBoard onBoardUpdate={handleBoardUpdate} />
          </div>
        </div>
        
        {/* Right Panel - Score & Stats */}
        <div className="hidden lg:flex flex-col w-64 p-4 bg-black/30 backdrop-blur-sm border-l border-white/10">
          {/* Current Score */}
          <div className="bg-gradient-to-br from-yellow-500/20 to-orange-500/20 rounded-xl p-4 mb-4 border border-yellow-500/30">
            <div className="text-xs text-yellow-400 uppercase tracking-wide mb-2">Current Score</div>
            <motion.div 
              key={gameState.score}
              initial={{ scale: 1.2 }}
              animate={{ scale: 1 }}
              className="text-4xl font-bold text-white"
            >
              {gameState.score.toLocaleString()}
            </motion.div>
          </div>
          
          {/* Progress Bar */}
          <div className="bg-white/5 rounded-xl p-4 mb-4 border border-white/10">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Progress</div>
            <div className="w-full h-4 bg-black/30 rounded-full overflow-hidden border border-white/10">
              <motion.div 
                className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
            <div className="text-right text-sm text-gray-400 mt-1">{Math.round(progressPercent)}%</div>
          </div>
          
          {/* Stats */}
          <div className="bg-white/5 rounded-xl p-4 mb-4 border border-white/10">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-3">Session Stats</div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Moves</span>
                <span className="text-white font-bold">{totalMoves}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Combos</span>
                <span className="text-orange-400 font-bold">{totalCombos}</span>
              </div>
              {levelMechanics.moveLimit && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Move Limit</span>
                  <span className="text-red-400 font-bold">{levelMechanics.moveLimit - totalMoves}</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Controls */}
          <div className="mt-auto space-y-3">
            <Button
              onClick={toggleMute}
              variant="outline"
              className="w-full bg-white/5 border-white/20 text-white hover:bg-white/10"
            >
              {isMuted ? '🔇 Unmute' : '🔊 Mute'}
            </Button>
            <Button
              onClick={handleResetLevel}
              variant="outline"
              className="w-full bg-red-500/20 border-red-500/30 text-red-400 hover:bg-red-500/30"
            >
              🔄 Reset Level
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameScreen;
