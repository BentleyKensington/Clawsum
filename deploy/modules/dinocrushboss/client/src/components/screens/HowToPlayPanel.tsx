import { useAuth } from "@/lib/stores/useAuth";
import {
  DINO_NAMES,
  LEVEL_COUNT,
  STAR_REQUIREMENTS,
  getDinoIdleClass,
  getDinoImage,
  getDinoNamesForLevel,
  getDinosForLevel,
} from "@/lib/constants";

interface HowToPlayPanelProps {
  level: number;
  targetScore: number;
  compact?: boolean;
}

const HowToPlayPanel: React.FC<HowToPlayPanelProps> = ({
  level,
  targetScore,
  compact = false,
}) => {
  const { progress, levelScores, isGuest } = useAuth();
  const dinos = getDinosForLevel(level);
  const starReqs =
    STAR_REQUIREMENTS[level] || {
      oneStarScore: Math.floor(targetScore * 0.6),
      twoStarScore: Math.floor(targetScore * 0.85),
      threeStarScore: Math.floor(targetScore * 1.2),
    };
  const saved = levelScores.find((ls) => ls.level === level);
  const highScore = saved?.highScore || 0;
  const earnedStars = saved?.stars || 0;
  const totalStars = progress?.totalStars || 0;
  const highest = progress?.highestLevel || 1;

  return (
    <div className={`flex flex-col gap-3 text-sm text-gray-200 ${compact ? "" : "flex-1 min-h-0 overflow-y-auto pr-1"}`}>
      <div>
        <div className="text-xs text-amber-300 uppercase tracking-wide mb-1">Why play</div>
        <p className="text-gray-300 leading-relaxed">
          Crush dinos, chain combos, and chase a higher score every round. Each level has a target,
          a personal high score, and up to three stars. Beat your best. Unlock rarer dinos. Become
          the Crush Boss.
        </p>
      </div>

      <div className="bg-yellow-500/10 border border-yellow-400/20 rounded-xl p-3">
        <div className="text-xs text-yellow-300 uppercase tracking-wide mb-2">Rewards</div>
        <ul className="space-y-1.5 text-xs text-gray-200">
          <li>
            <span className="text-yellow-300 font-bold">Stars</span> — hit {starReqs.oneStarScore.toLocaleString()} / {starReqs.twoStarScore.toLocaleString()} / {starReqs.threeStarScore.toLocaleString()} for ⭐ ⭐⭐ ⭐⭐⭐
          </li>
          <li>
            <span className="text-yellow-300 font-bold">High score</span> — this level best:{" "}
            {highScore > 0 ? highScore.toLocaleString() : "none yet. Set one!"}
          </li>
          <li>
            <span className="text-yellow-300 font-bold">Album</span> — you have {totalStars} star{totalStars === 1 ? "" : "s"} across {LEVEL_COUNT} levels (reached {Math.min(highest, LEVEL_COUNT)})
          </li>
          <li>
            <span className="text-yellow-300 font-bold">Unlocks</span> — later levels add lesser-known dinos and a bigger board
          </li>
          {earnedStars > 0 && (
            <li>
              You already earned {"⭐".repeat(earnedStars)} here. Can you beat it?
            </li>
          )}
          {isGuest && (
            <li className="text-amber-200">
              Guest scores stay on this device. Save with email so stars follow you.
            </li>
          )}
        </ul>
      </div>

      <div>
        <div className="text-xs text-green-400 uppercase tracking-wide mb-2">How to crush</div>
        <ol className="space-y-2 text-xs text-gray-200 list-decimal list-inside leading-relaxed">
          <li>
            Tap a dino, then tap a neighbor <span className="text-white">(up, down, left, or right — not diagonal)</span>.
          </li>
          <li>Or drag a dino onto its neighbor. Same thing, faster on a tablet.</li>
          <li>
            Make a line of <span className="text-white font-semibold">3 or more of the same dino</span>. They crush and growl. New dinos fall in from above.
          </li>
          <li>
            Keep matching until you hit the target:{" "}
            <span className="text-yellow-300 font-bold">{targetScore.toLocaleString()}</span>.
          </li>
          <li>
            Cascades are the fun part: one crush can make another, then another. Combos add bonus points.
          </li>
          <li>
            Match <span className="text-white">4</span> for extra points. Match <span className="text-white">5+</span> for a power-up crush.
          </li>
          <li>
            If you stall, two dinos bounce — that is a hint. Press <span className="text-white">M</span> to mute.
          </li>
        </ol>
      </div>

      <div>
        <div className="text-xs text-purple-300 uppercase tracking-wide mb-2">
          This level — {getDinoNamesForLevel(level).length} dinos
        </div>
        <p className="text-[11px] text-gray-400 mb-2">
          Level 1 is famous faces only. New species sneak in as you climb.
        </p>
        <div className="grid grid-cols-3 gap-2">
          {dinos.map((type) => (
            <div
              key={type}
              className="bg-black/40 rounded-lg p-1.5 border border-white/10 flex flex-col items-center"
            >
              <img
                src={getDinoImage(type)}
                alt={DINO_NAMES[type]}
                className={`w-10 h-10 object-contain ${getDinoIdleClass(type)}`}
              />
              <div className="text-[10px] text-center text-gray-300 leading-tight mt-0.5">
                {DINO_NAMES[type]}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white/5 rounded-xl p-3 border border-white/10">
        <div className="text-xs text-blue-300 uppercase tracking-wide mb-2">Score like a boss</div>
        <ul className="text-xs text-gray-300 space-y-1.5">
          <li>3-match: 10 points per dino</li>
          <li>4-match: extra +15 · 5-match: +30 · 6+: +60</li>
          <li>Each cascade wave adds +10 more</li>
          <li>Stars use your score plus speed and combo bonuses</li>
        </ul>
      </div>
    </div>
  );
};

export default HowToPlayPanel;
