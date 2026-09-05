import React, { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/stores/useAuth";
import { go, withGuest, type PublicUrls } from "@/lib/hosts";

interface AuthScreenProps {
  urls: PublicUrls;
}

const AuthScreen: React.FC<AuthScreenProps> = ({ urls }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { login, signup, playAsGuest, error, isLoading, clearError } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!isLogin && password !== confirmPassword) return;
    const ok = isLogin ? await login(email, password) : await signup(email, password);
    if (ok) go(urls.gameUrl);
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    clearError();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-green-900 flex items-center justify-center p-4 overflow-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-black/40 backdrop-blur-lg rounded-2xl p-6 w-full max-w-md border border-white/20"
      >
        <div className="text-center mb-4">
          <img src="/dino-crush-logo.png" alt="Dino Crush" className="w-24 h-24 mx-auto mb-2 object-contain" />
          <p className="text-emerald-300 text-xs font-bold tracking-[0.2em] uppercase mb-2">Free forever</p>
          <h1 className="text-2xl font-bold text-white mb-1">
            {isLogin ? "Open your save" : "Save your adventure"}
          </h1>
          <p className="text-white/70 text-sm">
            Dino Crush is free. Easy save: <span className="text-yellow-300">play@dinocrushboss.com</span>
            {" "}(or dinocrushboss@gmail.com). Password keeps the stars yours.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-white/80 text-sm mb-1">Email</label>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-green-400"
              placeholder="play@dinocrushboss.com"
              required
            />
          </div>
          <div>
            <label className="block text-white/80 text-sm mb-1">Password</label>
            <input
              type="password"
              autoComplete={isLogin ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-green-400"
              placeholder="Keeps the save yours"
              required
              minLength={6}
            />
          </div>
          {!isLogin && (
            <div>
              <label className="block text-white/80 text-sm mb-1">Confirm password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-green-400"
                placeholder="Confirm password"
                required
                minLength={6}
              />
              {password !== confirmPassword && confirmPassword && (
                <p className="text-red-400 text-sm mt-1">Passwords don't match</p>
              )}
            </div>
          )}
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3">
              <p className="text-red-300 text-sm text-center">{error}</p>
            </div>
          )}
          <Button
            type="submit"
            disabled={isLoading || (!isLogin && password !== confirmPassword)}
            className="w-full py-6 text-lg font-bold bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
          >
            {isLoading ? "Loading..." : isLogin ? "Start game" : "Create free save"}
          </Button>
        </form>

        <div className="mt-4">
          <Button
            type="button"
            variant="outline"
            disabled={isLoading}
            onClick={() => {
              playAsGuest();
              go(withGuest(urls.gameUrl));
            }}
            className="w-full py-6 text-lg font-bold border-yellow-400/60 text-yellow-200 hover:bg-yellow-400/10"
          >
            Play as guest
          </Button>
          <p className="text-white/50 text-xs text-center mt-2">No email. Stars stay on this device until you save.</p>
        </div>

        <div className="mt-6 text-center space-y-3">
          <button type="button" onClick={toggleMode} className="text-white/70 hover:text-white text-sm">
            {isLogin ? "New here? Create a free save" : "Already have a save? Sign in"}
          </button>
          <p>
            <a href={urls.promoUrl} className="text-yellow-300/90 text-sm hover:underline">
              ← Back to dinocrushboss.com
            </a>
          </p>
          <p className="text-yellow-300/80 text-sm">Created by Alex Hennessey</p>
        </div>
      </motion.div>
    </div>
  );
};

export default AuthScreen;
