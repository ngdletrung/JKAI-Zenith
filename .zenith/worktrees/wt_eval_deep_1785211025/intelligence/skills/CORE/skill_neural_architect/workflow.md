# SKILL WORKFLOW: NEURAL ARCHITECT (#109)

## Operational Steps

### 1. Initialization
- The skill is invoked by the Dispatcher when architectural mapping or project understanding is required.
- It identifies the target workspace or specific project path.

### 2. Reconnaissance (Scanning)
- Performs a deep scan of the file system, ignoring non-essential directories (.git, node_modules, etc.).
- Collects file names and structures to build a mental model of the project.

### 3. Synthesis (Neural Analysis)
- Sends the file list to the AI Planner with an Architect profile.
- Identifies "Nodes" (Services, Entry Points, Data Flows) and "Edges" (Relationships).

### 4. Visualization (Mermaid)
- Transforms the AI analysis into Mermaid.js diagram code.
- Generates a human-readable topology report.

### 5. Integration (Neural Sync)
- Embeds the description of each node.
- Upserts the vectors into the 'universal_graph' collection.
- Marks the project as "Mapped" for future AI reasoning tasks.

## Maintenance
- Run /sync_Q_Rank_brain to ensure the mapping logic is always up to date.
