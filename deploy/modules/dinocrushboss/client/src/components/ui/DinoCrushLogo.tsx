import React from 'react';

interface DinoCrushLogoProps {
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

const DinoCrushLogo: React.FC<DinoCrushLogoProps> = ({ size = 'medium', className = '' }) => {
  const sizeClasses = {
    small: 'text-2xl',
    medium: 'text-4xl',
    large: 'text-6xl'
  };

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="relative">
        {/* 3D Text Effect */}
        <div className={`font-bold ${sizeClasses[size]} relative`}>
          {/* Shadow layers for 3D effect */}
          <span className="absolute text-gray-800 transform translate-x-1 translate-y-1">
            DINO CRUSH
          </span>
          <span className="absolute text-gray-700 transform translate-x-2 translate-y-2">
            DINO CRUSH
          </span>
          <span className="absolute text-gray-600 transform translate-x-3 translate-y-3">
            DINO CRUSH
          </span>
          
          {/* Main text with gradient */}
          <span className="relative bg-gradient-to-r from-orange-400 via-red-500 to-pink-500 bg-clip-text text-transparent">
            DINO CRUSH
          </span>
        </div>

        {/* Decorative dinosaur emojis */}
        <div className="absolute -top-2 -left-4 text-xl animate-bounce">
          🦖
        </div>
        <div className="absolute -top-2 -right-4 text-xl animate-bounce" style={{ animationDelay: '0.5s' }}>
          🦕
        </div>
        <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 text-xl animate-bounce" style={{ animationDelay: '1s' }}>
          💎
        </div>
      </div>
    </div>
  );
};

export default DinoCrushLogo;