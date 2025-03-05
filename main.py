import os
import logging
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the application
    logger.info(f"Starting REanna Router on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
