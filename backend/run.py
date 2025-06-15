#!/usr/bin/env python
"""Entry point for running the application."""

import os
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable (Cloud Run sets this)
    port = int(os.environ.get("PORT", 8080))
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,  # Gunicorn handles workers
        log_level="info",
        access_log=True
    )