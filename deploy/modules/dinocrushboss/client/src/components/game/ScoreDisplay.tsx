import { useEffect, useState } from "react";
import { useDinoCrush } from "@/lib/stores/useDinoCrush";
import { motion, AnimatePresence } from "framer-motion";

const ScoreDisplay: React.FC = () => {
  const { gameState } = useDinoCrush();
  const [prevScore, setPrevScore] = useState(0);
  const [scoreAdded, setScoreAdded] = useState(0);
  const [showScorePopup, setShowScorePopup] = useState(false);
  
  useEffect(() => {
    if (gameState.score > prevScore) {
      const newPoints = gameState.score - prevScore;
      setScoreAdded(newPoints);
      setShowScorePopup(true);
      
      const timer = setTimeout(() => {
        setShowScorePopup(false);
      }, 1000);
      
      return () => clearTimeout(timer);
    }
    
    setPrevScore(gameState.score);
  }, [gameState.score, prevScore]);
  
  return (
    <div className="relative">
      <AnimatePresence>
        {showScorePopup && (
          <motion.div
            initial={{ opacity: 0, y: 0 }}
            animate={{ opacity: 1, y: -20 }}
            exit={{ opacity: 0 }}
            className="absolute top-0 left-1/2 transform -translate-x-1/2 text-yellow-300 font-bold text-lg"
          >
            +{scoreAdded}
          </motion.div>
        )}
      </AnimatePresence>
      
      <motion.div
        key={gameState.score}
        initial={{ scale: 1 }}
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 0.3 }}
        className="text-3xl font-bold text-white"
      >
        {gameState.score}
      </motion.div>
    </div>
  );
};

export default ScoreDisplay;
