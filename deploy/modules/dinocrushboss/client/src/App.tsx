import { useEffect, useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { useAudio } from "./lib/stores/useAudio";
import { useGame } from "./lib/stores/useGame";
import { useAuth } from "./lib/stores/useAuth";
import "@fontsource/inter";
import "./index.css";
import MainMenu from "./components/screens/MainMenu";
import GameScreen from "./components/screens/GameScreen";
import LevelComplete from "./components/screens/LevelComplete";
import LoadingScreen from "./components/LoadingScreen";
import AuthScreen from "./components/screens/AuthScreen";
import { useDinoCrush } from "./lib/stores/useDinoCrush";
import { gameSurface, go, loadPublicUrls, loginSurface, type PublicUrls } from "./lib/hosts";

function App() {
  const { phase } = useGame();
  const { gameState } = useDinoCrush();
  const { toggleMute, unlockAudio } = useAudio();
  const { user, isGuest, checkAuth, playAsGuest, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [urls, setUrls] = useState<PublicUrls>({
    loginUrl: "/login",
    gameUrl: "/",
    promoUrl: "https://dinocrushboss.com",
  });

  useEffect(() => {
    void loadPublicUrls().then(setUrls);
    if (new URLSearchParams(window.location.search).get("guest") === "1") {
      playAsGuest();
    }
    void checkAuth();
  }, []);

  useEffect(() => {
    const unlock = () => unlockAudio();
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, [unlockAudio]);

  useEffect(() => {
    if (isLoading || authLoading) return;
    const canPlay = Boolean(user) || isGuest;
    if (loginSurface() && canPlay) {
      go(urls.gameUrl);
      return;
    }
    if (gameSurface() && !canPlay) {
      go(urls.loginUrl);
    }
  }, [isLoading, authLoading, user, isGuest, urls.gameUrl, urls.loginUrl]);

  useEffect(() => {
    if (isLoading) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "m") toggleMute();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isLoading, toggleMute]);

  const canPlay = Boolean(user) || isGuest;
  const showLogin = loginSurface() || (!canPlay && !authLoading);
  const showGame = canPlay && gameSurface();

  return (
    <QueryClientProvider client={queryClient}>
      <div className="w-full h-full">
        {isLoading && <LoadingScreen onLoadingComplete={() => setIsLoading(false)} />}

        {!isLoading && showLogin && !showGame && <AuthScreen urls={urls} />}

        {!isLoading && showGame && (
          <>
            <div className="fixed top-0 left-0 p-2 z-20 text-sm text-white bg-black/50 rounded-br-md">
              {user?.email}
            </div>
            {phase === "ready" && (
              <div className="fixed top-2 left-1/2 transform -translate-x-1/2 z-20 pointer-events-none">
                <img src="/dino-crush-logo.png" alt="Dino Crush" className="h-12 w-auto opacity-80 drop-shadow-lg" />
              </div>
            )}
            <div className="fixed top-0 right-0 p-2 z-10 text-sm text-white bg-black/50 rounded-bl-md">
              Press 'M' to toggle audio
            </div>
            <div className="fixed bottom-0 right-0 p-4 z-10 text-lg font-semibold text-yellow-300 bg-black/60 rounded-tl-lg">
              Created by Alex Hennessey
            </div>
            {phase === "ready" && <MainMenu loginUrl={urls.loginUrl} />}
            {phase === "playing" && (
              <div className="w-full h-full">
                <GameScreen />
              </div>
            )}
            {phase === "ended" && gameState.levelComplete && <LevelComplete />}
          </>
        )}
      </div>
    </QueryClientProvider>
  );
}

export default App;
