galacticSolver — Challenge Solver (Python)

Overview
- Simple, high-quality implementation to solve the timed challenge.
- Stack Option A: Python 3.11+, httpx and dotenv.
- Orchestrates the flow: statement parsing (via GPT proxy), data fetching (SWAPI and PokéAPI), safe evaluation, and answer submission.

Requirements
- Python 3.11 or higher installed.
- Challenge token (Bearer) received by email.

Quick setup
1) Create and activate a virtual environment (optional but recommended):
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) Install dependencies:
   python -m pip install -r requirements.txt

3) Provide the token via environment:
   - Option A (recommended): create a .env file in the repo root with:
       CHALLENGE_TOKEN=your_token_here
   - Option B: export an environment variable:
       export CHALLENGE_TOKEN=your_token_here
   - Optional: override the base URL with CHALLENGE_BASE_URL (defaults to https://recruiting.adere.so)

Usage
- Practice (uses the /challenge/test endpoint):
   python app.py practice

- Official run (3-minute loop):
   python app.py official

Notes
- The parser uses the chat proxy endpoint at the challenge base URL: POST {CHALLENGE_BASE_URL}/chat_completion (defaults to https://recruiting.adere.so). You can override with the CHALLENGE_BASE_URL env var.
- Data sources:
  - SWAPI: https://swapi.dev/api/
  - PokéAPI: https://pokeapi.co/api/v2/
- Results are rounded to 10 decimal places (ROUND_HALF_UP).

Project structure
- app.py                main CLI
- galactic_solver/
  - challenge_client.py challenge HTTP client (start/solution/test and chat proxy)
  - nlu_parser.py       statement parser using the GPT proxy (deterministic JSON)
  - evaluator.py        safe expression evaluator + rounding
  - data_sources/
    - swapi.py          Star Wars people and planets
    - pokeapi.py        Pokémon
  - utils.py            utilities (normalization, simple cache)

Warnings
- Do not commit the token to the repository. Use an environment variable or a local .env.
- For unknown values ("unknown") or division by zero, the program skips the problem and continues.

License
- Personal use for the challenge.
