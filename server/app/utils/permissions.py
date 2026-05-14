from fastapi import HTTPException, status

def check_role(user, allowed_roles):
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for your role"
        )
