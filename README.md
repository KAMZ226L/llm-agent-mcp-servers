# LLM Agent with MCP Servers

An LLM-powered agent that uses the **Model Context Protocol (MCP)** to interact with external APIs and a local PostgreSQL database through independent, specialized servers. The agent follows a **cache-first pattern**: it checks the local database before querying external sources, and can persist new data on user request.

## Architecture

```
                    ┌──────────────────┐
                    │   User (CLI)     │
                    └────────┬─────────┘
                             │ natural language
                             ▼
                    ┌──────────────────┐
                    │   LLM Agent      │
                    │   (Ollama)       │
                    │                  │
                    │  Tool Calling    │
                    │  Cache-first     │
                    └───┬──────────┬───┘
                        │          │
            ┌───────────▼──┐  ┌───▼───────────┐
            │  MCP Server  │  │  MCP Server   │
            │  Database    │  │  External API  │
            │  :8001       │  │  :8002         │
            └───────┬──────┘  └───┬───────────┘
                    │              │
            ┌───────▼──────┐  ┌───▼───────────┐
            │ PostgreSQL   │  │ Dragon Ball   │
            │ (local)      │  │ API           │
            └──────────────┘  └───────────────┘
```

## How It Works

1. **User asks a question** (e.g., "Tell me about Goku")
2. **LLM decides which tools to call** using Ollama's function calling
3. **Cache-first lookup**: the agent queries the local DB via MCP-DB
4. **If not found**: the agent queries the external API via MCP-API
5. **Results are presented** to the user in natural language
6. **Optional persistence**: the user can choose to save the data locally
7. **Relationships are maintained**: saving a character automatically creates their origin planet if it doesn't exist

The LLM never uses its own training knowledge — all data comes exclusively through MCP tool calls.

## MCP Servers

### MCP-DB (Port 8001)
Handles all database operations through three tools:

| Tool | Description |
|------|-------------|
| `get_character_by_name` | Looks up a character in the local DB |
| `insert_location_if_not_exists` | Creates a planet if it doesn't exist |
| `insert_character` | Inserts a character with a foreign key to their origin planet |

### MCP-API (Port 8002)
Handles external API queries:

| Tool | Description |
|------|-------------|
| `get_character_from_api` | Fetches character data from the Dragon Ball API |

## Data Model

```
┌─────────────────┐       ┌─────────────────┐
│    Location      │       │    Character      │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │◄──┐   │ id (PK)         │
│ name            │   │   │ name            │
│ description     │   │   │ race            │
│ is_destroyed    │   │   │ gender          │
│                 │   │   │ ki / max_ki     │
│                 │   └───│ origin_loc_id(FK)│
└─────────────────┘       └─────────────────┘
     One                        Many
```

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL running locally
- [Ollama](https://ollama.ai) installed

### Installation

```bash
# Clone the repo
git clone https://github.com/KAMZ226L/llm-agent-mcp-servers.git
cd llm-agent-mcp-servers

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Pull the LLM model
ollama pull llama3.1

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### Create the database

```bash
# In PostgreSQL
createdb dragonball

# Initialize tables
cd mcp_db
python -c "from db import init_db; init_db()"
```

### Run

You need three terminals:

```bash
# Terminal 1: Start MCP Database Server
cd mcp_db
python server.py

# Terminal 2: Start MCP API Server
cd mcp_api
python server.py

# Terminal 3: Start the Agent
cd client_agent
python main.py
```

### Example Session

```
You: Tell me about Goku
Agent: [calls get_character_by_name("Goku")]
       Not found in local DB.
       [calls get_character_from_api("Goku")]
       Goku is a Saiyan from planet Vegeta. Ki: 60,000,000...
       Would you like me to save this to the database?

You: Yes, save it
Agent: [calls insert_location_if_not_exists("Vegeta")]
       [calls insert_character({...}, {name: "Vegeta"})]
       Done! Goku has been saved with his origin planet.

You: Tell me about Goku again
Agent: [calls get_character_by_name("Goku")]
       Found in local DB! (no API call needed)
```

## Project Structure

```
llm-agent-mcp-servers/
├── client_agent/
│   └── main.py              # LLM agent with tool calling and CLI
├── mcp_api/
│   └── server.py            # MCP server for Dragon Ball API
├── mcp_db/
│   ├── server.py            # MCP server for database operations
│   ├── models.py            # SQLModel schemas (Character, Location)
│   └── db.py                # Database connection and session management
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── LICENSE
```

## Tech Stack

- **Python 3.10+**
- **FastMCP** — Model Context Protocol server framework
- **Ollama** — local LLM inference (Llama 3.1)
- **SQLModel** — database ORM (SQLAlchemy + Pydantic)
- **PostgreSQL** — relational database
- **Dragon Ball API** — external data source

## License

MIT
