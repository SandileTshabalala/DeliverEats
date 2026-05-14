from fastapi import Depends
from app.core.dependencies import get_current_user

def role_required(*roles):
    def wrapper(user=Depends(get_current_user)):
        if user.role not in roles:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user
    return wrapper
