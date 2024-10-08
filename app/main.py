from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
import requests
import uvicorn
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
KEYCLOAK_BASE_URL = "https://login.marc-os.com"
KEYCLOAK_REALM = "gradify"
KEYCLOAK_CLIENT_ID = "gradibackend"
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "mHZa6XNqnTOlv2REYLWgCmysbEcpHTBE")  # Replace with your actual secret

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# FastAPI app setup
app = FastAPI()

# Pydantic Models
class User(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    role: str

# Utility Functions
def get_public_key():
    """ Retrieve the realm public key to verify JWT tokens."""
    response = requests.get(f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}")
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not fetch public key from Keycloak")
    return response.json()["public_key"]

# Dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo", headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return response.json()

# Endpoints
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    data = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
        "grant_type": "password",
        "username": form_data.username,
        "password": form_data.password
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token", data=data, headers=headers)
    
    # Logging for debugging purposes
    logger.info(f"Requesting token with data: {data}")
    logger.info(f"Keycloak response status code: {response.status_code}")
    logger.info(f"Keycloak response body: {response.text}")
    
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user credentials")
    return response.json()

@app.post("/register-school")
async def register_school(user: User, current_user: dict = Depends(get_current_user)):
    # Only allow users who just registered to register a school
    if current_user.get("preferred_username") != user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to register a school")

    # Simulate registration of the school (in practice, you'd save this to a database)
    school_data = {
        "school_name": f"{user.username}'s School",
        "admin": current_user.get("preferred_username")
    }

    # Here we would normally create the Keycloak group for this school, for now we simulate the response
    return {"message": "School registered successfully", "data": school_data}

@app.get("/users/me", response_model=User)
async def get_user(current_user: dict = Depends(get_current_user)):
    user = User(
        username=current_user.get("preferred_username"),
        email=current_user.get("email"),
        first_name=current_user.get("given_name"),
        last_name=current_user.get("family_name"),
        role=""  # To be updated once role handling is implemented
    )
    return user

@app.get("/admin/users", response_model=List[User])
async def get_all_users(current_user: dict = Depends(get_current_user)):
    # Only admin users can view all users
    if current_user.get("role") != "schooladmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view all users")
    
    # Fetching users would involve database calls or Keycloak API calls, for now we return a simulated list
    users = [
        User(username="teacher1", email="teacher1@example.com", first_name="Alice", last_name="Smith", role="teacher"),
        User(username="student1", email="student1@example.com", first_name="Bob", last_name="Brown", role="student")
    ]
    return users

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
