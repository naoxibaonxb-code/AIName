from pydantic import BaseModel, Field, model_validator
from typing import List, Annotated, Literal
from .agent import NameSchema

CategoryLiteral = Literal["人名", "企业名", "宠物名"]


class NameIn(BaseModel):
    category: Annotated[CategoryLiteral, Field("人名", description="命名分类")]
    surname: Annotated[str, Field("", description="姓氏")]
    gender: Annotated[Literal["不限", "男", "女"], Field("不限", description="性别")]
    length: Annotated[Literal["不限", "单字", "两字","五字"], Field("不限", description="字数")]
    other: Annotated[str | None, Field("", description="其他要求")]
    exclude: Annotated[List[str], Field([], description="排除的名字")]

    @model_validator(mode="after")
    def validate_surname(self, ):
        if self.category == "人名" and not self.surname:
            raise ValueError("生成姓名时，姓氏不能为空")
        return self


class NameOut(BaseModel):
    names: List[NameSchema]


class FeedBackIn(BaseModel):
    thread_id: str = Field(..., description="前端回传的会话ID")
    category: Literal["人名", "企业名", "宠物名"] = Field(...,description="路由依赖")
    feedback: str = Field(...,description="用户的修改意见，如：换成带水字旁的字")

class NameWithThreadOut(BaseModel):
    thread_id: str
    names: List[NameSchema]
