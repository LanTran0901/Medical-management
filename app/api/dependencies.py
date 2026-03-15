from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.security import decode_token
from app.domain.entities.user import User
from app.infrastructure.config.database.postgres.connection import get_session
from app.infrastructure.repositories.user_repository_pg import UserRepositoryPG

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user_repo = UserRepositoryPG(session)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user
