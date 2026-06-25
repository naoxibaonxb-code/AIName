from pydantic import BaseModel, Field, model_validator
from typing import List, Annotated, Literal
from .agent import NameSchema

CategoryLiteral = Literal["人名", "企业名", "宠物名", "虚拟IP"]
NameLengthLiteral = Literal[
    "不限",
    "单字",
    "两字",
    "五字",
    "单字名",
    "双字名",
    "1-2字",
    "2-3字",
    "2-4字（推荐）",
    "3-5字",
]


class NameIn(BaseModel):
    category: Annotated[CategoryLiteral, Field("人名", description="命名分类")]
    surname: Annotated[str, Field("", description="姓氏")]
    gender: Annotated[Literal["不限", "男", "女"], Field("不限", description="性别")]
    length: Annotated[NameLengthLiteral, Field("不限", description="名字长度")]
    other: Annotated[str | None, Field("", description="其他要求")]
    exclude: Annotated[List[str], Field([], description="排除的名字")]
    use_bazi: Annotated[bool, Field(False, description="是否启用八字五行参考")]
    birth_info: Annotated[str | None, Field("", description="出生时间、地点等命理参考信息")]
    brand_tone: Annotated[str | None, Field("", description="品牌调性")]
    target_audience: Annotated[str | None, Field("", description="目标客群")]
    competitors: Annotated[str | None, Field("", description="竞品或相似品牌")]
    ip_setting: Annotated[str | None, Field("", description="虚拟 IP 的世界观或角色设定")]
    ip_personality: Annotated[str | None, Field("", description="虚拟 IP 的性格、人设或口头禅")]

    @model_validator(mode="after")
    def validate_surname(self, ):
        if self.category == "人名" and not self.surname:
            raise ValueError("生成姓名时，姓氏不能为空")
        return self


class FeedBackIn(BaseModel):
    thread_id: str = Field(..., description="前端回传的会话ID")
    category: CategoryLiteral = Field(..., description="路由依赖")
    feedback: str = Field(..., description="用户的修改意见，如：换成带水字旁的字")

class NameWithThreadOut(BaseModel):
    thread_id: str
    names: List[NameSchema]
