# ZENITH INFRASTRUCTURE SPECIFICATION v1.0
> [!NOTE]
> This document maintains the precise mapping of the physical infrastructure layer, synchronizing Docker containers, images, and network ports for the JKAI Zenith ecosystem.

## 1. CORE NEURAL SERVICES
| Service Name | Container Name | Image/Tag | Ports | Role |
| :--- | :--- | :--- | :--- | :--- |
| **ai-brain** | `jkai-ai-brain` | `jkai-ai-brain` | `8001:8000` | Central Cognitive Engine |
| **ai-control-plane** | `jkai-ai-control-plane` | `jkai-ai-control-plane` | `7000:8000` | Strategy & Orchestration |
| **ai-executor-1** | `jkai-ai-executor-1` | `jkai-ai-executor-1` | `8002:8000` | Primary Execution Unit |
| **ai-executor-2** | `jkai-ai-executor-2` | `jkai-ai-executor-2` | `8007:8000` | Secondary Execution Unit |
| **rag-service** | `jkai-rag-service` | `jkai-rag-service` | `8000:8000` | Knowledge Retrieval (RAG) |
| **ai-browser** | `jkai-ai-browser` | `jkai-ai-browser` | `8003:8000` | Autonomous Web Navigation |

## 2. INTERFACE & GATEWAYS
| Service Name | Container Name | Image/Tag | Ports | Role |
| :--- | :--- | :--- | :--- | :--- |
| **mission-control** | `jkai-mission-control` | `jkai-mission-control` | `5173:5173` | Zenith 3D HUD / Frontend |
| **ai-telegram** | `jkai-ai-telegram` | `jkai-ai-telegram` | - | Telegram Bot Interface |
| **n8n-main** | `n8n-main` | `n8nio/n8n:2.7.4` | `5678:5678` | Automation Workflow Engine |
| **n8n-worker** | `n8n-worker` | `n8nio/n8n:2.7.4` | - | Distributed Workflow Worker |

## 3. DATA & MEMORY LAYER
| Service Name | Container Name | Image/Tag | Ports | Role |
| :--- | :--- | :--- | :--- | :--- |
| **postgres** | `postgres` | `postgres:15-alpine` | - | Structured Event Archive |
| **redis-queue** | `redis-queue` | `redis:7-alpine` | - | Task Queue (n8n) |
| **redis-ai** | `redis-ai` | `redis:7-alpine` | - | Real-time Neural Sync |
| **qdrant** | `qdrant` | `qdrant/qdrant:latest` | `6333:6333` | Vector Memory Vault |

## 4. MONITORING & SECURITY
| Service Name | Container Name | Image/Tag | Ports | Role |
| :--- | :--- | :--- | :--- | :--- |
| **jaeger** | `jaeger` | `jaegertracing/all-in-one:latest` | `16686:16686` | X-Ray Trace Monitoring |
| **zenith-file-warden** | `zenith-file-warden` | `jkai-zenith-file-warden` | `8005:8005` | Filesystem Security Guard |

---
*Updated: 2026-05-12 07:15:00 (Post-v41.0 Synchronization)*
