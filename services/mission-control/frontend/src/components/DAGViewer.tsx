import React, { memo, useMemo, Suspense, lazy } from 'react';
import ReactFlow, { Background, ConnectionLineType } from 'reactflow';
import { motion } from 'framer-motion';
import 'reactflow/dist/style.css';
import { CustomNode } from './dag/CustomNode';
import { NeuralEdge } from './dag/NeuralEdge';
import { useZenithStore } from '../store/zenithStore';

// 🌌 Lazy load 3D Module for performance optimization
const NeuralBody3D = lazy(() => import('./dag/NeuralBody3D').then(m => ({ default: m.NeuralBody3D })));

const nodeTypes = {
  custom: CustomNode,
};

const edgeTypes = {
  neural: NeuralEdge,
};

// 🧠 Anatomical Positioning Matrix (Normalized 1000x1000)
// These coordinates align with the 3D Neural Body silhouette
const ANATOMICAL_MAP: Record<string, { x: number, y: number }> = {
  'planner': { x: 420, y: 50 },       // Left Brain
  'brain': { x: 420, y: 50 },         // Brain (General)
  'bridge': { x: 580, y: 50 },        // Right Brain
  'receptionist': { x: 580, y: 50 },  // Right Brain
  'critic': { x: 500, y: 250 },       // Heart / Core
  'reviewer': { x: 500, y: 250 },     // Heart / Core
  'memory': { x: 500, y: 500 },       // Spine
  'vault': { x: 500, y: 500 },        // Spine
  'executor': { x: 200, y: 350 },     // Left Hand
  'executor_1': { x: 800, y: 350 },   // Right Hand
  'executor_2': { x: 350, y: 800 },   // Left Foot
  'executor_3': { x: 650, y: 800 },   // Right Foot
};

export const DAGViewer = memo(({ nodes, edges, onNodesChange, onEdgesChange }: any) => {
  const status = useZenithStore(s => s.status);
  const isRunning = status === 'running';

  // 🧬 Force Anatomical Positioning
  const mappedNodes = useMemo(() => {
    let executorCount = 0;
    return (nodes || []).map((node: any) => {
      const type = node.data?.type || node.id;
      let pos = ANATOMICAL_MAP[node.id] || ANATOMICAL_MAP[type];

      if (type === 'executor' && executorCount > 0) {
        pos = ANATOMICAL_MAP[`executor_${executorCount}`] || pos;
        executorCount++;
      } else if (type === 'executor') {
        executorCount++;
      }

      if (!pos) pos = { x: 500, y: 400 };

      return {
        ...node,
        position: pos,
        draggable: false,
      };
    });
  }, [nodes]);

  const neuralEdges = useMemo(() => {
    return (edges || []).map((edge: any) => ({
      ...edge,
      type: 'neural',
      data: { ...edge.data, status: isRunning ? 'RUNNING' : 'IDLE' },
      animated: isRunning
    }));
  }, [edges, isRunning]);

  return (
    <div className="w-full h-full relative bg-[#04060b] overflow-hidden">
      
      {/* 🌌 Phase 4: 3D Dimensional Background Layer */}
      <Suspense fallback={
        <div className="absolute inset-0 flex items-center justify-center opacity-10">
          <div className="w-24 h-24 rounded-full border-4 border-red-500 border-t-transparent animate-spin" />
        </div>
      }>
        <NeuralBody3D isRunning={isRunning} />
      </Suspense>

      {/* 🩸 Blood Circulation Atmosphere Overlay */}
      <div className={`absolute inset-0 pointer-events-none transition-opacity duration-2000 z-0 ${isRunning ? 'opacity-30' : 'opacity-5'}`}>
        <div className="absolute inset-0 bg-gradient-to-t from-red-950/60 via-transparent to-red-950/20" />
        {/* Scanning Light Effect */}
        <div className="absolute inset-0 bg-[linear-gradient(0deg,transparent_0%,rgba(255,0,0,0.05)_50%,transparent_100%)] bg-[length:100%_200%] animate-[scan_4s_linear_infinite]" />
      </div>

      <ReactFlow
        nodes={mappedNodes}
        edges={neuralEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        connectionLineType={ConnectionLineType.Bezier}
        fitView={true}
        className="z-10 bg-transparent"
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        minZoom={0.1}
        maxZoom={2}
        fitViewOptions={{ padding: 0.2, duration: 1200 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          color="rgba(255, 50, 50, 0.03)"
          gap={50}
          size={1}
          className="opacity-20"
        />
      </ReactFlow>

      {/* 🧬 Anatomical Labels (Overlay) */}
      <div className="absolute top-4 left-4 pointer-events-none opacity-40 z-20">
        <div className="flex flex-col gap-1 border-l-2 border-red-500/50 pl-3">
          <span className="text-[10px] font-black uppercase tracking-widest text-red-500">Neural Anatomy 3D Matrix</span>
          <span className="text-[8px] font-mono text-white/40 uppercase tracking-widest">Projection Active // R3F Core</span>
        </div>
      </div>
      
      {/* 🔮 3D Status HUD */}
      <div className="absolute bottom-4 right-4 pointer-events-none z-20 text-right">
        <div className="flex flex-col gap-1 pr-3 border-r-2 border-red-500/30">
          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-white/20">Spatial Sync</span>
          <span className={`text-[8px] font-black uppercase tracking-widest ${isRunning ? 'text-red-500 animate-pulse' : 'text-white/10'}`}>
            {isRunning ? 'Hyper-Drive Active' : 'Idle Orbit'}
          </span>
        </div>
      </div>
    </div>
  );
}, (prev, next) => {
  if (prev.nodes === next.nodes && prev.edges === next.edges) return true;
  if (prev.nodes?.length !== next.nodes?.length) return false;
  if (prev.edges?.length !== next.edges?.length) return false;
  
  for (let i = 0; i < prev.nodes.length; i++) {
    const a = prev.nodes[i];
    const b = next.nodes[i];
    if (a.id !== b.id || a.data?.status !== b.data?.status || a.data?.msg !== b.data?.msg) return false;
  }
  return true;
});



