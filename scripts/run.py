"""Development server runner for MCP Server Builder."""
import sys
from pathlib import Path

# Add parent directory to path so app module can be found
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
