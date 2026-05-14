from fastapi.responses import JSONResponse

def success(data=None, message="Success", status_code=200):
    return JSONResponse(status_code=status_code, content={
        "status": "success",
        "message": message,
        "data": data
    })

def error(message="Error", status_code=400):
    return JSONResponse(status_code=status_code, content={
        "status": "error",
        "message": message
    })
