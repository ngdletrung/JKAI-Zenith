<!--
[ZENITH FILE DIRECTIVE]
- File: claw_compactor/ABOUT.md
- Role: Third-Party Library Attribution
- Ownership: OpenClaw Contributors / Bot777 (MIT License)
- Status: Assimilated | Version: 7.1.0

[WORKING PRINCIPLES]:
1. [ATTRIBUTION]: Claw Compactor is (c) OpenClaw Contributors, MIT License.
2. [INTEGRITY]: Do NOT modify source files in this directory.
3. [LICENSE]: Full license text at LICENSES/claw-compactor-MIT.txt.
-->

# Claw Compactor v7.1.0 (Assimilated)

**Source**: https://github.com/open-compress/claw-compactor  
**License**: MIT License — see `LICENSES/claw-compactor-MIT.txt`  
**Authors**: Bot777, OpenClaw Contributors  
**Integration Date**: 2026-07-04  

## What is Claw Compactor?

14-stage Fusion Pipeline for LLM token compression:
- Reversible compression with RewindStore
- AST-aware code analysis (Neurosyntax)
- SimHash semantic deduplication
- JSON statistical sampling (Ionizer)
- Log/diff/search result folding
- Content-type-aware routing (Cortex)
- Zero LLM inference cost, zero external dependencies

## Assimilated Components

The full `claw_compactor/` directory is copied verbatim from the upstream project.
- JKAI does NOT modify source files within `fusion/`, `rewind/`, or root modules.
- The wrapper `context.py` in the parent directory provides JKAI-specific integration.

## License Notice

This library is free software; you can redistribute it and/or modify it under
the terms of the MIT License. A copy of the license is included in the
JKAI `LICENSES/` directory as `claw-compactor-MIT.txt`.
