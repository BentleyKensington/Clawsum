import { useState, useRef, useEffect } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import { DinoType } from "@/types/game";
import { TILE_SIZE } from "@/lib/constants";

interface DinoTileProps {
  type: DinoType;
  position: [number, number, number];
  selected: boolean;
  onClick: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
}

const dinoColors = {
  [DinoType.Red]: "#ff5555",
  [DinoType.Green]: "#55ff55",
  [DinoType.Blue]: "#5555ff",
  [DinoType.Yellow]: "#ffff55",
  [DinoType.Purple]: "#ff55ff",
};

const DinoTile: React.FC<DinoTileProps> = ({ 
  type, 
  position, 
  selected, 
  onClick, 
  onDragStart, 
  onDragEnd 
}) => {
  const [hover, setHover] = useState(false);
  const meshRef = useRef<THREE.Mesh>(null);
  const [targetScale, setTargetScale] = useState(1);
  const [dragging, setDragging] = useState(false);
  
  useEffect(() => {
    setTargetScale(selected || hover ? 1.1 : 1);
  }, [selected, hover]);
  
  // Handle animation
  useFrame(() => {
    if (meshRef.current) {
      // Smooth scale animation
      meshRef.current.scale.x = THREE.MathUtils.lerp(meshRef.current.scale.x, targetScale, 0.2);
      meshRef.current.scale.y = THREE.MathUtils.lerp(meshRef.current.scale.y, targetScale, 0.2);
      meshRef.current.scale.z = THREE.MathUtils.lerp(meshRef.current.scale.z, targetScale, 0.2);
      
      // Animation for selection
      if (selected) {
        meshRef.current.rotation.z = Math.sin(Date.now() * 0.005) * 0.1;
      } else {
        meshRef.current.rotation.z = THREE.MathUtils.lerp(meshRef.current.rotation.z, 0, 0.2);
      }
    }
  });
  
  const handlePointerDown = () => {
    setDragging(true);
    onDragStart();
  };
  
  const handlePointerUp = () => {
    if (dragging) {
      setDragging(false);
      onDragEnd();
    } else {
      onClick();
    }
  };
  
  const handlePointerOut = () => {
    setHover(false);
    if (dragging) {
      setDragging(false);
    }
  };

  // Debug the tile rendering
  console.log("Rendering tile:", type, "at position:", position);

  return (
    <group position={position}>
      {/* Tile background */}
      <mesh
        ref={meshRef}
        onPointerOver={() => setHover(true)}
        onPointerOut={handlePointerOut}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        castShadow
        receiveShadow
      >
        <boxGeometry args={[TILE_SIZE * 0.9, TILE_SIZE * 0.9, 0.2]} />
        <meshStandardMaterial color={dinoColors[type]} />
      </mesh>
      
      {/* Dino icon on top */}
      <mesh position={[0, 0, 0.15]}>
        <planeGeometry args={[TILE_SIZE * 0.7, TILE_SIZE * 0.7]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.8} />
      </mesh>
      
      {/* Border when hovering or selected */}
      {(hover || selected) && (
        <mesh position={[0, 0, 0.11]}>
          <planeGeometry args={[TILE_SIZE * 0.95, TILE_SIZE * 0.95]} />
          <meshBasicMaterial color={selected ? "#ffff00" : "#ffffff"} transparent opacity={0.3} />
        </mesh>
      )}
      
      {/* Selection highlight underneath */}
      {selected && (
        <mesh position={[0, 0, -0.1]}>
          <planeGeometry args={[TILE_SIZE * 1.05, TILE_SIZE * 1.05]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={0.3} />
        </mesh>
      )}
      
      {/* Text to indicate tile type */}
      <Html center position={[0, 0, 0.3]} transform>
        <div 
          className="font-bold text-lg" 
          style={{ 
            color: "white", 
            textShadow: "0 0 3px black",
            fontSize: "24px",
          }}
        >
          {type === DinoType.Red ? "🦖" : 
           type === DinoType.Green ? "🦕" : 
           type === DinoType.Blue ? "🐊" : 
           type === DinoType.Yellow ? "🦎" : 
           type === DinoType.Purple ? "🐉" : "?"}
        </div>
      </Html>
    </group>
  );
};

export default DinoTile;
