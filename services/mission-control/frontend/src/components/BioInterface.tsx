import React, { memo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, Float, Stars, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';

// ─── 🎭 ULTRA-STABLE AGENT NODES ──────────────────────────────────────────────
const AgentAvatar = ({ type, isRunning }: { type: string, isRunning: boolean }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const elapsed = useRef(0);
  useFrame((state, delta) => {
    if (meshRef.current) {
      elapsed.current += delta;
      const t = elapsed.current;
      meshRef.current.rotation.y = t * 1.5;
      if (isRunning) {
        meshRef.current.scale.setScalar(1.3 + Math.sin(t * 8) * 0.1);
      }
    }
  });

  return (
    <mesh ref={meshRef}>
      {type === 'planner' && <octahedronGeometry args={[1, 0]} />}
      {type === 'executor' && <boxGeometry args={[1.2, 1.2, 1.2]} />}
      {type === 'critic' && <dodecahedronGeometry args={[1, 0]} />}
      {type === 'receptionist' && <sphereGeometry args={[0.8, 16, 16]} />}
      <meshStandardMaterial 
        color={isRunning ? "#ff0000" : (type === 'planner' ? "#00f2ff" : "#555")} 
        wireframe={!isRunning}
        emissive={isRunning ? "#ff0000" : "#222"}
        emissiveIntensity={isRunning ? 5 : 0.5}
      />
    </mesh>
  );
};

export const BioInterface = memo(({ nodes = [] }: any) => {
  const safeNodes = nodes || [];
  
  // 🛡️ Fix Case-Sensitivity: Chấp nhận cả PLANNER và planner
  const planner = safeNodes.find((n: any) => 
    n.id?.toLowerCase() === 'planner' || n.data?.type?.toLowerCase() === 'planner'
  );
  const executor = safeNodes.find((n: any) => 
    n.id?.toLowerCase() === 'executor' || n.data?.type?.toLowerCase() === 'executor'
  );
  const critic = safeNodes.find((n: any) => 
    n.id?.toLowerCase() === 'critic' || n.data?.type?.toLowerCase() === 'critic'
  );

  const agents = [
    { id: 'p', label: 'PLANNER', type: 'planner', active: planner?.data?.status === 'RUNNING', pos: [10, 0, 0] },
    { id: 'e', label: 'EXECUTOR', type: 'executor', active: executor?.data?.status === 'RUNNING', pos: [-10, 0, 0] },
    { id: 'c', label: 'CRITIC', type: 'critic', active: critic?.data?.status === 'RUNNING', pos: [0, 0, 10] },
    { id: 'r', label: 'RECEPTION', type: 'receptionist', active: false, pos: [0, 0, -10] },
  ];

  const isAnyActive = agents.some(a => a.active);

  return (
    <div className="w-full h-full relative bg-[#020305] flex items-center justify-center overflow-hidden">
      
      {/* 🌌 3D SPACE */}
      <div className="absolute inset-0 z-0">
        <Canvas dpr={[1, 2]}>
          <PerspectiveCamera makeDefault position={[0, 25, 40]} fov={45} />
          <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
          <ambientLight intensity={0.6} />
          <pointLight position={[0, 15, 0]} intensity={3} color="#ff3333" />
          
          {/* 🔱 Master Core */}
          <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
            <mesh>
              <octahedronGeometry args={[2.5, 0]} />
              <meshStandardMaterial color="#fff" emissive="#ff0000" emissiveIntensity={isAnyActive ? 10 : 2} wireframe />
            </mesh>
          </Float>

          {/* 👥 Neural Agents */}
          {agents.map((agent: any) => (
            <group key={agent.id} position={agent.pos}>
              <Float speed={3} rotationIntensity={1} floatIntensity={1.5}>
                <AgentAvatar type={agent.type} isRunning={agent.active} />
              </Float>
              {/* 🔗 Neural Bridge (Stable Line) */}
              <mesh position={[agent.pos[0] / 2, 0, agent.pos[2] / 2]} rotation={[0, -Math.atan2(agent.pos[2], agent.pos[0]), 0]}>
                <boxGeometry args={[Math.sqrt(agent.pos[0]**2 + agent.pos[2]**2), 0.05, 0.05]} />
                <meshBasicMaterial color={agent.active ? "#ff0000" : "#222"} transparent opacity={0.4} />
              </mesh>
            </group>
          ))}
        </Canvas>
      </div>

      {/* 📟 HUD OVERLAYS (HTML for stability) */}
      <div className="absolute top-8 left-8 flex flex-col gap-1 pointer-events-none z-10 border-l-4 border-red-600 pl-4 py-2 bg-black/60 backdrop-blur-xl">
        <span className="text-[16px] font-black text-white tracking-[0.4em] uppercase">Zenith War Room</span>
        <span className="text-[10px] font-mono text-red-500 uppercase tracking-widest">Neural Alliance v20.3 Final</span>
      </div>

      {/* 🏷️ Agent Labels (HTML Overlay) */}
      {agents.map((agent: any) => (
        <div 
          key={agent.id + '_label'}
          className="absolute pointer-events-none transition-all duration-1000"
          style={{
            transform: `translate(${agent.pos[0] * 35}px, ${agent.pos[2] * -15}px)`,
            opacity: 0.6
          }}
        >
          <div className={`px-3 py-1 border ${agent.active ? 'border-red-600 bg-red-600/10 text-white' : 'border-white/10 bg-black/40 text-white/40'} text-[9px] font-black uppercase tracking-widest rounded-sm backdrop-blur-md`}>
            {agent.label}
          </div>
        </div>
      ))}

      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 z-10 flex flex-col items-center pointer-events-none">
        <div className="text-[10px] font-black text-white/20 uppercase tracking-[1em] mb-4">Supreme Command Hub</div>
        <div className="w-96 h-[1px] bg-gradient-to-r from-transparent via-red-600/40 to-transparent" />
      </div>

    </div>
  );
});
