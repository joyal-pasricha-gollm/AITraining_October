# Concurrent Agents Demo

A small Python demo that analyzes fictional customer feedback with three agents running concurrently: sentiment analysis, recurring issues, and improvement suggestions.

## Setup

1. Install Python 3.10 or later.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set your Groq API key and chat model in `.env`.
4. Run the demo:

   ```powershell
   python concurrent_agents.py
   ```

The program reads feedback records from `feedback.json` and prints each agent's analysis.
