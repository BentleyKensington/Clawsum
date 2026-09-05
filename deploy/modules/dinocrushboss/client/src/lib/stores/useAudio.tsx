import { create } from "zustand";

interface AudioState {
  backgroundMusic: HTMLAudioElement | null;
  hitSound: HTMLAudioElement | null;
  successSound: HTMLAudioElement | null;
  crushSound: HTMLAudioElement | null;
  isMuted: boolean;
  audioInitialized: boolean;
  
  // Setter functions
  setBackgroundMusic: (music: HTMLAudioElement) => void;
  setHitSound: (sound: HTMLAudioElement) => void;
  setSuccessSound: (sound: HTMLAudioElement) => void;
  setCrushSound: (sound: HTMLAudioElement) => void;
  
  // Control functions
  toggleMute: () => void;
  playHit: () => void;
  playSuccess: () => void;
  playCrush: () => void;
  playGrowl: () => void;
  playBackgroundMusic: () => void;
  stopBackgroundMusic: () => void;
  unlockAudio: () => void;
  isAudioInitialized: () => boolean;
}

export const useAudio = create<AudioState>((set, get) => ({
  backgroundMusic: null,
  hitSound: null,
  successSound: null,
  crushSound: null,
  isMuted: false,
  audioInitialized: false,
  
  setBackgroundMusic: (music) => {
    const { backgroundMusic: currentMusic, audioInitialized } = get();
    
    // If already initialized, don't create duplicate audio
    if (audioInitialized && currentMusic) {
      console.log('Audio already initialized, skipping duplicate');
      return;
    }
    
    // Keep the track that is already playing. Never rewind it.
    if (currentMusic && !currentMusic.paused) {
      set({ audioInitialized: true });
      return;
    }
    music.loop = true;
    music.volume = 0.2;
    set({ backgroundMusic: music, audioInitialized: true });
  },
  
  isAudioInitialized: () => {
    return get().audioInitialized;
  },
  setHitSound: (sound) => set({ hitSound: sound }),
  setSuccessSound: (sound) => set({ successSound: sound }),
  setCrushSound: (sound) => set({ crushSound: sound }),
  
  toggleMute: () => {
    const { isMuted, backgroundMusic } = get();
    const newMutedState = !isMuted;
    
    // Update the muted state
    set({ isMuted: newMutedState });
    
    // Actually pause or resume background music
    if (backgroundMusic) {
      if (newMutedState) {
        backgroundMusic.pause();
      } else {
        backgroundMusic.play().catch(error => {
          console.log("Background music play prevented:", error);
        });
      }
    }
    
    console.log(`Sound ${newMutedState ? 'muted' : 'unmuted'}`);
  },
  
  playHit: () => {
    const { hitSound, isMuted } = get();
    if (hitSound) {
      // If sound is muted, don't play anything
      if (isMuted) {
        console.log("Hit sound skipped (muted)");
        return;
      }
      
      // Clone the sound to allow overlapping playback
      const soundClone = hitSound.cloneNode() as HTMLAudioElement;
      soundClone.volume = 0.3;
      soundClone.play().catch(error => {
        console.log("Hit sound play prevented:", error);
      });
    }
  },
  
  playSuccess: () => {
    const { successSound, isMuted } = get();
    if (successSound) {
      // If sound is muted, don't play anything
      if (isMuted) {
        console.log("Success sound skipped (muted)");
        return;
      }
      
      successSound.currentTime = 0;
      successSound.play().catch(error => {
        console.log("Success sound play prevented:", error);
      });
    }
  },
  
  playCrush: () => {
    const { crushSound, isMuted } = get();
    if (isMuted) return;
    if (crushSound) {
      try {
        crushSound.pause();
        crushSound.currentTime = 0;
        crushSound.volume = 0.45;
        crushSound.play().catch(() => {});
      } catch {
        /* crush is optional */
      }
    }
    get().playGrowl();
  },

  playGrowl: () => {
    if (get().isMuted) return;
    const { crushSound, backgroundMusic } = get();
    try {
      if (backgroundMusic) {
        backgroundMusic.volume = 0.08;
      }
      const growl = (crushSound?.cloneNode() as HTMLAudioElement | undefined) || new Audio("/sounds/crush.wav");
      growl.playbackRate = 0.55;
      growl.volume = 0.5;
      growl.play().catch(() => {});
      window.setTimeout(() => {
        const music = get().backgroundMusic;
        if (music && !get().isMuted) {
          music.volume = 0.2;
        }
      }, 480);
    } catch {
      if (backgroundMusic && !get().isMuted) {
        backgroundMusic.volume = 0.2;
      }
    }
  },
  
  playBackgroundMusic: () => {
    const { backgroundMusic, isMuted } = get();
    if (backgroundMusic && !isMuted && backgroundMusic.paused) {
      backgroundMusic.loop = true;
      if (backgroundMusic.volume === 0) backgroundMusic.volume = 0.2;
      backgroundMusic.play().catch(error => {
        console.log("Background music play prevented:", error);
      });
    }
  },

  unlockAudio: () => {
    get().playBackgroundMusic();
  },
  
  stopBackgroundMusic: () => {
    const { backgroundMusic } = get();
    if (backgroundMusic) {
      backgroundMusic.pause();
      backgroundMusic.currentTime = 0;
    }
  }
}));
