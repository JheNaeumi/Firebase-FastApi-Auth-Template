
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
# Route Imports
from app import login, registration
from app.home import home
from app.profile import profile


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

api_prefix = '/api/2025'

app.include_router(login.router, prefix='{}'.format(api_prefix))
app.include_router(registration.router, prefix='{}'.format(api_prefix))
app.include_router(home.router, prefix='{}'.format(api_prefix))
app.include_router(profile.router, prefix='{}'.format(api_prefix))


if __name__ == "__main__":
    uvicorn.run('main:app', reload=True, port=5000)
