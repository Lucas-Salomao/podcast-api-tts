# Podcast Generator API
# Entry point for running the application

"""
Main entry point for the Podcast Generator API.

Run with:
    uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Or simply:
    python main.py
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
