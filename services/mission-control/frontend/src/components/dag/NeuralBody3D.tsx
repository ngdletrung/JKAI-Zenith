import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial, Float, Stars, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';

const ParticleBody = ({ isRunning }: { isRunning: boolean }) => {
  const pointsRef = useRef<THREE.Points>(null);
  
  // Create a high-tech anatomical silhouette using particles
  const particles = useMemo(() => {
    const count = 4000;
    const positions = new Float32Array(count * 3);
    
    for (let i = 0; i < count; i++) {
      // Create a vertical "Golem" shape
      const y = (Math.random() - 0.5) * 6; // Height
      
      // Tapering logic for human-like silhouette
      let radius = 0;
      if (y > 2.2) radius = 0.3 * Math.exp(-((y - 2.5) ** 2)); // Head (Fixed TS17006)
      else if (y > 1.8) radius = 0.1; // Neck
      else if (y > 0) radius = 0.8 * Math.exp(-y * 0.2); // Chest/Shoulders
      else if (y > -2) radius = 0.6 * Math.exp(y * 0.1); // Torso/Hips
      else radius = 0.3 * Math.exp((y + 3) * 0.5); // Legs
      
      const angle = Math.random() * Math.PI * 2;
      const r = Math.sqrt(Math.random()) * radius;
      
      positions[i * 3] = Math.cos(angle) * r;
      positions[i * 3 + 1] = y - 0.5; // Offset to center
      positions[i * 3 + 2] = Math.sin(angle) * r * 0.6; // Slightly flat depth
    }
    return positions;
  }, []);

  const elapsed = useRef(0);
  useFrame((state, delta) => {
    if (pointsRef.current) {
      // Constant slow drift
      pointsRef.current.rotation.y += 0.002;
      
      // Sync heartbeat with time
      elapsed.current += delta;
      const t = elapsed.current;
      const pulse = Math.sin(t * (isRunning ? 4 : 1)) * 0.05 + 1;
      pointsRef.current.scale.set(pulse, pulse, pulse);
      
      if (isRunning) {
        pointsRef.current.rotation.y += 0.01;
      }
    }
  });

  return (
    <Points ref={pointsRef} positions={particles} stride={3}>
      <PointMaterial
        transparent
        color={isRunning ? "#ff0000" : "#440000"}
        size={0.06}
        sizeAttenuation={true}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </Points>
  );
};

export const NeuralBody3D = ({ isRunning }: { isRunning: boolean }) => {
  return (
    <div className="absolute inset-0 w-full h-full pointer-events-none z-0" style={{ perspective: '1000px' }}>
      <Canvas dpr={[1, 2]}>
        <PerspectiveCamera makeDefault position={[0, 0, 8]} fov={45} />
        <ambientLight intensity={0.2} />
        <pointLight position={[5, 5, 5]} intensity={1} color="#ff0000" />
        <pointLight position={[-5, -5, -5]} intensity={0.5} color="#880000" />
        
        <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
          <ParticleBody isRunning={isRunning} />
        </Float>
        
        <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />
      </Canvas>
    </div>
  );
};
