from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title='GridCheck API', version='3.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173','http://localhost:3000'],
    allow_credentials=True, allow_methods=['*'], allow_headers=['*'],
)
app.include_router(router)

@app.get('/health')
def health():
    return {'status': 'ok', 'version': '3.0.0'}
