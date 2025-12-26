# RAFA AI Studio 🤖📈

**An AI-Powered Decentralized Hedge Fund on Base.**

The RAFA AI Studio is a hybrid full-stack application that combines an AI Agent (powered by LangChain), a Quantitative Analysis Engine, and a Web3 trading execution layer. It allows users to onboard, receive an automated funding "airdrop," and interact with an AI that manages a portfolio on the Base Sepolia testnet. Tune your AI in the Studio with prompts and RAGs to improve your portfolio performance.

## 🏗 Architecture

This project utilizes a **Unified Monolith Architecture** to simplify deployment while maintaining high performance.

* **Production (Railway/Heroku):** The application is containerized using **Docker**. The Python FastAPI backend serves both the API endpoints *and* the compiled React frontend static files.
* **Development (Local):** We use a **Hybrid Workflow**. The Backend (Python) and Frontend (React) run in separate terminals for hot-reloading, connected via a proxy.

### Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React, Tailwind CSS | Responsive UI for portfolio tracking and agent chat. |
| **Backend** | Python 3.11, FastAPI | High-performance API handling AI logic and trade execution. |
| **Database** | MongoDB | Stores user profiles, trade history, and portfolio snapshots. |
| **AI Engine** | LangChain, OpenAI | Interprets user intent and generates trading strategies. |
| **Quant Engine** | Taapi.io / Pandas-TA | Calculates real-time RSI, MACD, and EMA indicators. |
| **Blockchain** | Web3.py, Base Sepolia | Handles wallet management and on-chain swaps. |

---

## 🚀 Key Features

1.  **AI Trading Agent:** A conversational agent that understands commands like *"Buy 1 ETH if RSI is below 30"* and executes them autonomously.
2.  **Hybrid Quant Engine:** Fetches live market data (Birdeye/Coingecko) and computes technical indicators to signal trade entry/exit.
3.  **Automated Onboarding Faucet:** New users automatically receive **0.001 ETH** (Base Sepolia) from the protocol treasury to cover initial gas fees.
4.  **Shadow Ledger:** Tracks both "Real" on-chain assets and "Virtual" performance metrics for strategy testing.

---

## 🛠 Local Development Setup

Follow these steps to run the project on your machine.

### 1. Prerequisites
* Node.js (v18+)
* Python (v3.11)
* Git

### 2. Environment Variables
Create a `.env` file in the `backend/` directory:

```ini
# Blockchain
PRIVATE_KEY=your_agent_wallet_private_key
TREASURY_PRIVATE_KEY=your_faucet_wallet_private_key
WEB3_PROVIDER_URL=[https://sepolia.base.org](https://sepolia.base.org)

# Data Providers
BIRDEYE_API_KEY=your_key
TAAPI_API_KEY=your_key

# Database
MONGO_URI=your_mongodb_connection_string