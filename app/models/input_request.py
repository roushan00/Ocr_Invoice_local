
from pydantic import BaseModel


class ProcessRequest(BaseModel):
    unique_id: str
    distributor_id: str | None = None

class CancelRequest(BaseModel):
    unique_id: str
