from pydantic import BaseModel, ConfigDict
from typing import Dict

class Database:
    def __init__(self, instance_name, username, password, db_name):
        self.instance_name = instance_name
        self.username = username
        self.password = password
        self.db_name = db_name

class Pop(BaseModel):
    edge_requests: int

    model_config = ConfigDict(extra="ignore")

class FastlyStatsApiResponse(BaseModel):
    stats: Dict[str, Pop]
