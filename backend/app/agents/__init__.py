"""AtlasLens multi-agent layer.

Each agent is a thin Semantic Kernel wrapper around a domain-specific prompt
plus a small set of native function tools backed by `DataLoader`.

Agents:
    - Watcher   : ingests text artifacts into the Knowledge Store
    - Analyzer  : surfaces patterns / trends from accumulated data
    - Coach     : delivers EM-facing recommendations
    - Simulator : runs structural change impact predictions
    - Reporter  : daily/weekly summaries
"""
