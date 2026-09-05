import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useGame } from "@/lib/stores/useGame";
import { useAudio } from "@/lib/stores/useAudio";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { useAuth } from "@/lib/stores/useAuth";
import { LEVEL_COUNT, LEVEL_GOALS } from "@/lib/constants";

const MainMenu: React.FC<{ loginUrl: string }> = ({ loginUrl }) => {
  const { start } = useGame();
  const { toggleMute, isMuted, unlockAudio } = useAudio();
  const { resetGame, setCurrentLevel } = useDinoCrush();
  const { user, isGuest, progress, levelScores, logout } = useAuth();
  
  const handleStartGame = () => {
    unlockAudio();
    resetGame();
    const startLevel = progress?.currentLevel || 1;
    setCurrentLevel(startLevel);
    start();
  };
  
  const availableLevels = Array.from({ length: LEVEL_COUNT }, (_, i) => i + 1);
  
  const handleLevelSelect = (level: number) => {
    unlockAudio();
    resetGame();
    setCurrentLevel(level);
    start();
  };
  
  const getLevelStars = (level: number) => {
    const score = levelScores.find(ls => ls.level === level);
    return score?.stars || 0;
  };
  
  const isLevelUnlocked = (level: number) => {
    if (!user || !progress) return true;
    return level <= progress.highestLevel;
  };
  
  const handleLogout = async () => {
    await logout();
    window.location.href = loginUrl;
  };
  
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gradient-to-b from-slate-900 via-purple-900 to-indigo-950 overflow-auto">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-purple-500/10 via-transparent to-transparent" />
        {[...Array(30)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute text-4xl opacity-10"
            initial={{ y: '110vh', x: `${(i * 3.3) % 100}%`, rotate: 0 }}
            animate={{ y: '-10vh', rotate: 360 }}
            transition={{ duration: 20 + i * 1.5, repeat: Infinity, ease: 'linear', delay: i * 0.3 }}
          >
            {i % 2 === 0 ? '🦖' : '🦕'}
          </motion.div>
        ))}
      </div>
      
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 flex flex-col items-center max-w-xl w-full mx-4 py-8"
      >
        {/* Logo */}
        <motion.div 
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", duration: 0.8 }}
          className="mb-6"
        >
          <img 
            src="/dino-crush-logo.png" 
            alt="Dino Crush"
            className="h-32 w-auto drop-shadow-2xl"
          />
        </motion.div>
        
        {/* Creator Credit */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-yellow-400 text-lg font-semibold mb-6"
        >
          Created by Alex Hennessey
        </motion.div>
        
        {/* How to Play Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="w-full bg-black/40 backdrop-blur-sm rounded-2xl p-6 mb-6 border border-white/10"
        >
          <h3 className="text-xl font-bold text-white mb-4 text-center flex items-center justify-center gap-2">
            <span className="text-2xl">🦖</span> How to Play <span className="text-2xl">🦕</span>
          </h3>
          <ol className="text-sm text-gray-200 space-y-2 mb-4 list-decimal list-inside">
            <li>Tap one dino, then tap a neighbor beside it (not diagonal).</li>
            <li>You can also drag a dino onto its neighbor.</li>
            <li>Make a line of <strong className="text-white">3 or more of the same dino</strong>.</li>
            <li>They crush (you will hear a growl). New dinos fall in from above.</li>
            <li>Keep matching until you hit the <strong className="text-yellow-300">target score</strong>.</li>
            <li>Earn <strong className="text-yellow-300">1–3 stars</strong> and beat your <strong className="text-white">high score</strong> on every level.</li>
            <li>Level 1 is easy: only T-Rex, Triceratops, and Stegosaurus — lots of matches.</li>
            <li>Later levels add lesser-known dinos and a bigger board.</li>
            <li>Match 4 or 5 in a row for extra points and power-ups. Combos pay more.</li>
            <li>If tiles sit still, bouncing dinos are a hint. Press <strong className="text-white">M</strong> to mute.</li>
          </ol>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">👆</div>
              <div className="text-xs text-gray-300">Swap neighbors</div>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">🦖</div>
              <div className="text-xs text-gray-300">3+ same dinos crush</div>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">🔥</div>
              <div className="text-xs text-gray-300">Combos score extra</div>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">⭐</div>
              <div className="text-xs text-gray-300">Stars + high scores</div>
            </div>
          </div>
        </motion.div>
        
        {/* Start Button */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
          className="w-full mb-6"
        >
          <Button 
            onClick={handleStartGame} 
            className="w-full py-8 text-xl font-bold bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 transition-all shadow-lg shadow-green-500/30 rounded-xl"
          >
            🎮 Start Adventure
          </Button>
        </motion.div>
        
        {/* User Stats and Controls */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mb-6 flex flex-wrap gap-3 justify-center items-center"
        >
          {user && progress && (
            <div className="bg-white/10 rounded-lg px-4 py-2 text-white text-sm">
              <span className="font-bold">{isGuest ? "Guest" : user.email || user.username}</span>
              <span className="mx-2">|</span>
              <span>⭐ {progress.totalStars}</span>
              <span className="mx-2">|</span>
              <span>🏆 Level {progress.highestLevel}</span>
            </div>
          )}
          {isGuest && (
            <Button
              onClick={() => {
                window.location.href = loginUrl;
              }}
              className="bg-yellow-500/90 hover:bg-yellow-400 text-black font-bold px-4"
            >
              Save with email
            </Button>
          )}
          <Button 
            onClick={toggleMute} 
            variant="outline" 
            className="border-white/30 text-white hover:bg-white/10 px-4"
          >
            {isMuted ? "🔇" : "🔊"}
          </Button>
          {user && (
            <Button 
              onClick={handleLogout} 
              variant="outline" 
              className="border-red-500/30 text-red-400 hover:bg-red-500/10 px-4"
            >
              {isGuest ? "Exit guest" : "Logout"}
            </Button>
          )}
        </motion.div>
        
        {/* Level Selection */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="w-full bg-black/40 backdrop-blur-sm rounded-2xl p-6 border border-white/10"
        >
          <h3 className="text-lg font-bold text-white mb-4 text-center">Select Level</h3>
          <div className="grid grid-cols-5 gap-2">
            {availableLevels.map(level => {
              const stars = getLevelStars(level);
              const unlocked = isLevelUnlocked(level);
              return (
                <motion.div
                  key={level}
                  whileHover={unlocked ? { scale: 1.1 } : {}}
                  whileTap={unlocked ? { scale: 0.95 } : {}}
                >
                  <Button
                    onClick={() => unlocked && handleLevelSelect(level)}
                    variant="ghost"
                    disabled={!unlocked}
                    className={`w-full aspect-square text-white font-bold border rounded-xl ${
                      unlocked 
                        ? "bg-gradient-to-br from-purple-500/30 to-indigo-500/30 hover:from-purple-500/50 hover:to-indigo-500/50 border-white/10" 
                        : "bg-gray-800/50 border-gray-700/30 opacity-50 cursor-not-allowed"
                    }`}
                  >
                    <div className="flex flex-col items-center">
                      <span className="text-lg">{unlocked ? level : "🔒"}</span>
                      {stars > 0 && (
                        <span className="text-xs text-yellow-400">{"⭐".repeat(stars)}</span>
                      )}
                      {unlocked && stars === 0 && (
                        <span className="text-xs text-gray-400">{(LEVEL_GOALS[level-1] || 100).toLocaleString()}</span>
                      )}
                    </div>
                  </Button>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default MainMenu;
