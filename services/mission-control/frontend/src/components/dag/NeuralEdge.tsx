import React, { useMemo } from 'react';
import { EdgeProps, getBezierPath } from 'reactflow';

export const NeuralEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isRunning = data?.status === 'RUNNING';
  
  // 🩸 Anatomical Color Palette (Blood & Crimson)
  const colors = {
    artery: '#ff0000', // Bright Red (Oxygenated)
    vein: '#8b0000',   // Deep Crimson (Deoxygenated)
    glow: 'rgba(255, 0, 0, 0.4)'
  };

  const intensity = data?.intensity || 'calm';
  const particleCount = intensity === 'fierce' ? 6 : 4;
  const speedBase = intensity === 'fierce' ? 1.5 : intensity === 'fast' ? 2.5 : 4;

  const particles = useMemo(() => {
    return Array.from({ length: particleCount }).map((_, i) => ({
      delay: i * (speedBase / particleCount),
      size: 2.2 + Math.random() * 1.8,
      duration: speedBase + (Math.random() * 0.5),
    }));
  }, [particleCount, speedBase]);

  return (
    <>
      <defs>
        {/* 🩸 Blood Glow Filter */}
        <filter id={`blood-glow-${id}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>

        {/* 🩸 Artery Gradient */}
        <linearGradient id={`blood-grad-${id}`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={colors.vein} stopOpacity="0.2" />
          <stop offset="50%" stopColor={colors.artery} stopOpacity="0.8" />
          <stop offset="100%" stopColor={colors.vein} stopOpacity="0.2" />
        </linearGradient>
      </defs>

      {/* Main Vessel Path (Thành mạch) */}
      <path
        id={id}
        className={`neural-edge-path ${isRunning ? 'animate-pulse-vessel' : ''}`}
        d={edgePath}
        fill="none"
        stroke={isRunning ? `url(#blood-grad-${id})` : 'rgba(255,255,255,0.08)'}
        strokeWidth={isRunning ? 4 : 2}
        strokeLinecap="round"
        style={{
          filter: isRunning ? `url(#blood-glow-${id})` : 'none',
          transition: 'all 0.5s ease-in-out',
        }}
      />

      {/* 🧬 Blood Cell Particles (Hồng cầu) */}
      {isRunning && particles.map((p, i) => (
        <circle key={i} r={p.size} fill={colors.artery} style={{ filter: `url(#blood-glow-${id})` }}>
          <animateMotion
            dur={`${p.duration}s`}
            repeatCount="indefinite"
            path={edgePath}
            begin={`${p.delay}s`}
          />
          {/* Subtle Jitter (Rung lắc sinh học) */}
          <animate
            attributeName="r"
            values={`${p.size};${p.size * 1.3};${p.size}`}
            dur="0.6s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            values="0.4;1;0.4"
            dur="1.2s"
            repeatCount="indefinite"
          />
        </circle>
      ))}

      {/* Invisible interaction path */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        style={{ cursor: 'pointer' }}
      />
    </>
  );
};
