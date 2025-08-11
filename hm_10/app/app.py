"""
ML Model Inference API

This module provides a REST API for machine learning model inference,
specifically for text analysis that calculates the relative frequency
of vowels in the input text.
"""

from typing import Optional
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration constants
SECRET_KEY = "your-secret-key-change-in-production"  # Should be in env vars
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fake database (in production, use a real database)
users_db = {
    "john_smith": {
        "username": "john_smith",
        "hashed_password": pwd_context.hash("password123"),
        "email": "john@example.com",
        "age": 25,
        "role": "user",
    },
    "admin1": {
        "username": "admin1",
        "hashed_password": pwd_context.hash("admin123"),
        "email": "admin@example.com",
        "age": 30,
        "role": "admin",
    },
}

# Initialize FastAPI app
app = FastAPI(
    title="ML Model Inference API",
    description="API for text analysis using machine learning models",
    version="1.0.0"
)


class User(BaseModel):
    """User model for the API"""
    username: str
    email: str
    age: int
    role: str


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None


class ModelInferenceOutput(BaseModel):
    """Model inference output"""
    result: float
    analysis_type: str = "vowel_frequency"
    input_length: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    if username in users_db:
        user_dict = users_db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return User(
        username=user.username,
        email=user.email,
        age=user.age,
        role=user.role
    )


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is an admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


@app.get("/")
def index():
    """Root endpoint"""
    return {
        "message": "ML Model Inference API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to get access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@app.get("/analysis/{data}", response_model=ModelInferenceOutput)
async def run_model_analysis(
        data: str,
        current_user: User = Depends(get_current_admin_user)
):
    """
    Run text analysis on input data.

    This endpoint calculates the relative frequency of English vowels
    in the input text. Only accessible by admin users.

    Args:
        data: Input text to analyze
        current_user: Current authenticated admin user

    Returns:
        ModelInferenceOutput with analysis results
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input data cannot be empty"
        )

    # Count vowels in the text
    vowels = "aeiouAEIOU"
    vowel_count = sum(1 for char in data if char in vowels)

    # Calculate relative frequency
    result = vowel_count / len(data) if len(data) > 0 else 0.0

    return ModelInferenceOutput(
        result=result,
        input_length=len(data)
    )


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}