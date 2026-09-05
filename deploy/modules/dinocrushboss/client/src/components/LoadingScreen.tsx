import React, { useEffect, useState, useRef } from 'react';
import { useAudio } from '@/lib/stores/useAudio';

interface LoadingScreenProps {
  onLoadingComplete: () => void;
}

// Global flag to prevent multiple audio loads across hot reloads
let audioLoadedGlobal = false;

const LoadingScreen: React.FC<LoadingScreenProps> = ({ onLoadingComplete }) => {
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [fadeOut, setFadeOut] = useState(false);
  const { setBackgroundMusic, setHitSound, setSuccessSound, setCrushSound, playBackgroundMusic, isAudioInitialized, backgroundMusic } = useAudio();
  const audioLoadedRef = useRef(false);

  useEffect(() => {
    // Start progress animation immediately
    let progress = 0;
    const progressInterval = setInterval(() => {
      progress += 8; // Deterministic progress increment
      setLoadingProgress(Math.min(progress, 100));
      
      if (progress >= 100) {
        clearInterval(progressInterval);
        setTimeout(() => {
          // Try to load and play background music, but don't block completion
          // Check the store to prevent duplicate audio on hot reloads
          if (!audioLoadedRef.current && !audioLoadedGlobal && !isAudioInitialized()) {
            audioLoadedRef.current = true;
            audioLoadedGlobal = true;
            loadAudioFiles();
          } else if (backgroundMusic) {
            // Audio already loaded, just try to play it
            playBackgroundMusic();
          }
          
          // Begin fade out
          setFadeOut(true);
          setTimeout(() => {
            onLoadingComplete();
          }, 1000);
        }, 500);
      }
    }, 100);

    // Load audio files in background (don't block loading completion)
    const loadAudioFiles = () => {
      try {
        // Load background music (only once)
        const backgroundMusic = new Audio('/background-music.mp3');
        backgroundMusic.preload = 'auto';
        backgroundMusic.loop = true;
        backgroundMusic.volume = 0.2;
        setBackgroundMusic(backgroundMusic);
        
        // Load sound effects
        const hitSound = new Audio('/sounds/hit.mp3');
        hitSound.preload = 'auto';
        setHitSound(hitSound);
        
        const successSound = new Audio('/sounds/success.mp3');
        successSound.preload = 'auto';
        setSuccessSound(successSound);
        
        // Load crush sound (monster bite/crunch effect)
        const crushSound = new Audio('/sounds/crush.wav');
        crushSound.preload = 'auto';
        setCrushSound(crushSound);
        
        console.log('Audio files loaded successfully (once only)');
        
        // Try to play background music after short delay
        setTimeout(() => {
          playBackgroundMusic();
        }, 200);
        
      } catch (error) {
        console.log('Audio loading failed:', error);
      }
    };
    
    // Cleanup function to stop any playing audio on unmount
    return () => {
      clearInterval(progressInterval);
    };

  }, [setBackgroundMusic, setHitSound, setSuccessSound, setCrushSound, playBackgroundMusic, onLoadingComplete, isAudioInitialized, backgroundMusic]);

  return (
    <div 
      className={`fixed inset-0 bg-gradient-to-br from-purple-900 via-blue-900 to-green-900 
                  flex items-center justify-center z-50 transition-opacity duration-1000 
                  ${fadeOut ? 'opacity-0' : 'opacity-100'}`}
    >
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(50)].map((_, i) => {
          // Pre-calculate random values to avoid re-rendering issues
          const left = (i * 17) % 100;
          const top = (i * 23) % 100;
          const delay = (i * 0.1) % 2;
          const duration = 2 + (i * 0.05) % 2;
          
          return (
            <div
              key={i}
              className="absolute animate-pulse"
              style={{
                left: `${left}%`,
                top: `${top}%`,
                animationDelay: `${delay}s`,
                animationDuration: `${duration}s`
              }}
            >
              {i % 4 === 0 ? '🦖' : i % 4 === 1 ? '🦕' : i % 4 === 2 ? '💎' : '🌟'}
            </div>
          );
        })}
      </div>
      
      <div className="text-center z-10">
        {/* Logo */}
        <div className="mb-8 animate-bounce">
          <img 
            src="/dino-crush-logo.png" 
            alt="Dino Crush Logo"
            className="w-96 h-96 object-contain mx-auto drop-shadow-2xl"
            style={{
              filter: 'drop-shadow(0 0 30px rgba(255, 255, 255, 0.3))'
            }}
          />
        </div>
        
        {/* Loading text */}
        <div className="mb-6">
          <h2 className="text-4xl font-bold text-white animate-pulse">
            Loading Dino Crush by Alex Hennessey
          </h2>
        </div>
        
        {/* Progress bar */}
        <div className="w-80 h-4 bg-black/30 rounded-full mx-auto overflow-hidden border border-white/20">
          <div 
            className="bg-gradient-to-r from-green-400 via-blue-500 to-purple-600 h-full rounded-full transition-all duration-300 relative"
            style={{ width: `${loadingProgress}%` }}
          >
            <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
          </div>
        </div>
        
        {/* Progress percentage */}
        <div className="mt-4 text-2xl font-bold text-white">
          {Math.round(loadingProgress)}%
        </div>
        
        {/* Fun loading messages */}
        <div className="mt-6 text-lg text-white/80">
          {loadingProgress < 20 && "Awakening ancient dinosaurs..."}
          {loadingProgress >= 20 && loadingProgress < 40 && "Preparing prehistoric puzzles..."}
          {loadingProgress >= 40 && loadingProgress < 60 && "Loading magical power-ups..."}
          {loadingProgress >= 60 && loadingProgress < 80 && "Creating matching challenges..."}
          {loadingProgress >= 80 && loadingProgress < 100 && "Almost ready for adventure..."}
          {loadingProgress >= 100 && "Welcome to Dino Crush!"}
        </div>
        
        {/* Creator credit */}
        <div className="mt-8 text-xl font-semibold text-yellow-300 animate-pulse">
          Created by Alex Hennessey
        </div>
      </div>
    </div>
  );
};

export default LoadingScreen;