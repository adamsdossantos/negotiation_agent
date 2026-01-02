# Multi-Agent Marketplace Simulation

## Overview
Autonomous AI agents that simulate a functioning marketplace with emergent economic behaviors.

## Features
- 10 agents with distinct personalities
- Multi-round negotiations (up to 5 rounds)
- Agent memory and learning
- Complete transaction ledger
- Comprehensive analytics


## Quick Start
```bash
pip install uv
uv sync
python main.py
```

## Architecture
- LangGraph for negotiation state machines
- Gemini for agent decision-making
- Pydantic for data validation

## LangGraph Workflow

![Workflow](langgraph_workflow.png)

## Results

### Profitability
- Chaotic personality is the most profitable.
- Data Driven personality didn't do any negotiation
- Risky Taker is the second most profitable.

![Profitability](profitability.png)

### Assets
- Risk Taker and Emotional have more assets (capital + items)
- Conservative has less assets

![Assets](assets.png)

### Capital

- Risk Taker and Emotional have more capital

![Capital](capital.png)


### Transactions

- 85% of success in transactions

![Transactions](transactions.png)


- The avarage transaction price increases over time

![Average price](avg_transanction.png)

## Findings

As the simulation data is stored in csvs in a simulation_data folder, several data analysis could be done based on them, like which personality that trades most, items most negotiated, how each personality interact with other based on memory, etc.

Other implementation could be done in order to have most realistic simulation like persistence memory. 
This would allow the agents to recover memory about each other and have a potencial leverage in negotiation.

