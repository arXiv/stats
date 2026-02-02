from pydantic import BaseModel, ConfigDict
from typing import Dict


class Pop(BaseModel):
    edge_requests: int

    model_config = ConfigDict(extra="ignore")


class FastlyStatsApiResponse(BaseModel):
    stats: Dict[str, Pop]
