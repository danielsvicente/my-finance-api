from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers.accounts import router

app = FastAPI()

# CORS middleware to allow requests from different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You should specify the actual origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)