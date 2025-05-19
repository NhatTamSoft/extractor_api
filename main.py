import uvicorn
from app import app
from app.core.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=45456, reload=True) 