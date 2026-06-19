# schemas/agent.py

from pydantic import BaseModel, Field
from typing import Annotated, List


class NameSchema(BaseModel):
    name: Annotated[str, Field(..., description="姓名")]
    reference: Annotated[str, Field(..., description="出处")]
    moral: Annotated[str, Field(..., description="寓意")]
    domain: str = Field(default="", description="为企业品牌设计的纯小写 .com 域名，例如: astar.com")
    domain_status: str = Field(default="正在查询...", description="域名的注册状态")

class NameResultSchema(BaseModel):
    names: List[NameSchema]
