import os
import shutil
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends
from core.auth import AuthHandler
from core.rag_service import process_and_store_file

authHandler = AuthHandler()
router = APIRouter(prefix="/knowledge", tags=["知识库"])

UPLOAD_DIR = "./uploads"


@router.post("/upload")
async def upload_file(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        user_id: int = Depends(authHandler.auth_access_dependency)
):
    file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    background_tasks.add_task(process_and_store_file, file_path, user_id)
    return {
        "result": "success",
        "message": f"文件{file.filename}上传成功！后台正在为您构建专属知识库，请稍候测试起名功能。"
    }
