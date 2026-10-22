from fastapi import FastAPI
from app.api.routes import router as dataset_router

app = FastAPI(
    title="AI Business Intelligence Analyst",
    description="An AI-powered business analysis and predictive analytics platform",
    version="0.1.0",
)

# Register API routes
app.include_router(dataset_router)


@app.get("/", tags=["System"])
def home():
    """Root endpoint to check service identity and status."""
    return {
        "message": "AI Business Intelligence Analyst is running!",
        "status": "success",
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for container and uptime monitoring."""
    return {
        "status": "healthy",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
