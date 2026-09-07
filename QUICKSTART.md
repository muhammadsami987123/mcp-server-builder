# Quick Start – Get MCP Server Builder Running in 5 Minutes

Let's get you up and running with MCP Server Builder.

## Prerequisites

- Python 3.8+
- Git
- OpenAI API key (free tier OK)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/marsaempower/mcp-server-builder.git
cd mcp-server-builder
```

### 2. Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate it
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment

```bash
# Copy template
cp .env.example .env

# Edit with your API key
# On macOS/Linux:
open .env
# On Windows:
notepad .env

# Add your OpenAI API key:
# OPENAI_API_KEY=sk-your-key-here
```

**Get your API key**:
1. Go to https://platform.openai.com/api/keys
2. Click "Create new secret key"
3. Copy the key
4. Paste into .env

### 5. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
```

### 6. Open in Browser

```
http://localhost:8000
```

You should see the MCP Server Builder landing page with a URL input box.

## Build Your First MCP Server

### Step 1: Enter API URL

In the browser, paste an API documentation URL:

```
https://api.github.com
```

Or try these public APIs:
- `https://api.stripe.com` (Stripe API)
- `https://www.thunderbird.com/api` (API docs)
- `https://api.twilio.com` (Twilio)

### Step 2: Click "Build MCP"

The system will:
1. Fetch and analyze the API documentation
2. Extract endpoints and parameters
3. Design MCP tools using AI (GPT-4)
4. Generate complete Python MCP server code
5. Validate the generated code

This typically takes 3-8 seconds depending on API size.

### Step 3: Review Generated Server

Once complete, you'll see:
- Server name and description
- List of generated tools
- Code files (main.py, tools.py, config.py, etc.)
- Download button

### Step 4: Download & Run

1. Click "Download Project"
2. Extract the ZIP file
3. Open a terminal in the extracted directory
4. Run:

```bash
# Install dependencies
pip install -r requirements.txt

# Install the MCP server
mcp install

# Or run directly
python main.py
```

Your MCP server is now running! Use it with Claude Desktop or other MCP clients.

## Troubleshooting

### "OPENAI_API_KEY not found"

Make sure:
1. You have `.env` file in project root
2. `.env` contains: `OPENAI_API_KEY=sk-...`
3. The key is valid (test at https://platform.openai.com/api/keys)

Fix:
```bash
cp .env.example .env
# Edit .env with real key
```

### "Port 8000 already in use"

Another process is using port 8000. Either:
- Kill the other process, or
- Use different port:

```bash
uvicorn app.main:app --reload --port 8001
```

### "Discovery failed"

The API URL might not be accessible. Try:
1. Test the URL in your browser
2. Ensure it has OpenAPI/Swagger documentation
3. Check if URL requires authentication
4. Try a different API

Good URLs to test with:
- `https://api.github.com` (no auth needed)
- `https://httpbin.org/` (simple test API)

### "Generated server won't run"

Check:
1. All dependencies installed: `pip install -r requirements.txt`
2. Python version 3.8+: `python --version`
3. Syntax is valid: `python -m py_compile main.py`

## Common Tasks

### Test the Generated Server

```bash
# In the extracted project directory
python main.py

# In another terminal, test a tool
curl -X GET http://localhost:8001/tool/my_tool_name
```

### Customize Generated Server

Edit `main.py` and `tools.py`:
- Add authentication (API key, OAuth)
- Modify tool descriptions
- Add error handling
- Change tool parameters

### Use with Claude Desktop

1. Generate an MCP server
2. Download and extract
3. Add to Claude Desktop config:

```json
{
  "mcp": {
    "my-api-server": {
      "command": "python",
      "args": ["/path/to/generated/main.py"]
    }
  }
}
```

Restart Claude Desktop and the server's tools will be available.

## Next Steps

### Read Documentation

- **Full Setup**: See `README.md`
- **Architecture**: See `ARCHITECTURE.md`
- **API Reference**: See `API_REFERENCE.md`
- **Security**: See `SECURITY.md`
- **Testing**: See `TESTING.md`

### Contribute

Want to improve MCP Server Builder?

See `CONTRIBUTING.md` for:
- How to set up for development
- Code style guidelines
- Testing requirements
- PR process

### Get Help

- Questions? Open GitHub Discussion
- Found a bug? Open GitHub Issue
- Security issue? Email security@example.com

## Useful Commands

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Test
pytest

# Format code
black app/

# Type checking
mypy app/

# Production
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

## File Structure (Generated Server)

```
my-api-mcp/
├── main.py              # MCP server entry point
├── tools.py             # Tool implementations
├── config.py            # Configuration and auth
├── requirements.txt     # Dependencies
├── README.md            # Generated documentation
└── .env.example         # Environment template
```

## Tips & Tricks

### Speed Up Development

Use `--reload` flag to auto-restart on code changes:
```bash
uvicorn app.main:app --reload
```

### Debug Generated Code

Enable debug logging:
```bash
DEBUG=true uvicorn app.main:app --reload
```

### Test Different APIs

Try these public APIs without authentication:
- `https://jsonplaceholder.typicode.com/` (fake JSON API)
- `https://httpbin.org/` (HTTP testing)
- `https://api.github.com` (GitHub)
- `https://api.coindesk.com/` (Bitcoin data)

### Generate Multiple Servers

Each API gets its own generated server. You can:
1. Build multiple servers
2. Export each one
3. Combine them (advanced)
4. Use different APIs with different tools

## Frequently Asked Questions

**Q: Can I use generated servers in production?**  
A: Yes! They're production-ready. Test thoroughly and follow MCP best practices.

**Q: What APIs are supported?**  
A: OpenAPI 3.0, Swagger 2.0, and REST APIs with documentation. GraphQL support coming soon.

**Q: Can I customize the generated server?**  
A: Yes! Generated code is yours to modify. Edit main.py, tools.py, and config.py as needed.

**Q: Does it work with private APIs?**  
A: Yes! Provide the API documentation URL and auth credentials in the generated config.py.

**Q: How long does generation take?**  
A: Typically 3-8 seconds depending on API complexity. Larger APIs take longer.

**Q: Is there a cost?**  
A: Only your OpenAI API usage. Typically $0.01-0.50 per generated server depending on API size.

**Q: Can I generate multiple MCPs at once?**  
A: Yes! Use the web interface or API to generate as many as you need.

## Next: Run Your First MCP

```bash
# 1. Browser: http://localhost:8000
# 2. Paste URL: https://api.github.com
# 3. Click "Build MCP"
# 4. Wait 3-8 seconds
# 5. Download generated server
# 6. Extract and run!

# You now have a working MCP server! 🎉
```

---

**Happy building!** Questions? See the full docs in this repository.
