import traceback

from fastapi import APIRouter, Depends, HTTPException

from schemas.name import NameOut, NameIn, NameWithThreadOut, FeedBackIn
from core.auth import AuthHandler
from core.workflow import get_name_v2, feedback_names

auth_handler = AuthHandler()
router = APIRouter(prefix="/name", tags=["name"])


@router.post("/get_name", response_model=NameOut)
async def get_name(name_info: NameIn,
                   user_id: int = Depends(auth_handler.auth_access_dependency)):
    name_result = await get_name_v2(name_info, user_id)
    print(name_result)
    try:
        data = NameOut(names=name_result["names"]["names"])
    except Exception as e:
        print(e)
    return data


@router.post("/generate", response_model=NameWithThreadOut)
async def take_names_first_time(name_info: NameIn,
                                user_id: int = Depends(auth_handler.auth_access_dependency)):
    name_result = await get_name_v2(name_info, user_id)
    print(name_result)
    try:
        data = NameWithThreadOut(thread_id=name_result["thread_id"], names=name_result["names"]["names"])
    except Exception as e:
        print(e)
    return data


@router.post("/feedback", response_model=NameWithThreadOut)
async def take_names_feedback(
        data: FeedBackIn,
        user_id: int = Depends(auth_handler.auth_access_dependency)):
    """带有 Thread_ID 的多轮微调"""
    try:
        result = await feedback_names(data, user_id)
        return NameWithThreadOut(
            thread_id=result["thread_id"],
            names=result["names"]["names"])
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="微调失败")
