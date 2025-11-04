from pydantic import BaseModel, ConfigDict, validator
from typing import Literal, Dict


class Database:
    def __init__(self, instance_name, username, password, db_name):
        self.instance_name = instance_name
        self.username = username
        self.password = password
        self.db_name = db_name

FASTLY_POPS = Literal[
  "ADL",
  "AMS",
  "RTM",
  "DCA",
  "IAD",
  "PDK",
  "AKL",
  "QAH",
  "BKK",
  "QAJ",
  "QAF",
  "QAB",
  "BOG",
  "BOS",
  "BNE",
  "BRU",
  "EZE",
  "YYC",
  "CPT",
  "QAL",
  "MAA",
  "CHI",
  "CHC",
  "CMH",
  "LCK",
  "CPH",
  "ADS",
  "DFW",
  "DEL",
  "QAG",
  "DEN",
  "DTW",
  "QAM",
  "DXB",
  "DUB",
  "FOR",
  "FRA",
  "WIE",
  "FJR",
  "GNV",
  "ACC",
  "HEL",
  "HKG",
  "HNL",
  "IAH",
  "QAC",
  "HYD",
  "QAE",
  "JGA",
  "JNB",
  "KNU",
  "MCI",
  "QAA",
  "CCU",
  "KTU",
  "KUL",
  "LIM",
  "LIS",
  "LCY",
  "LHR",
  "LON",
  "BUR",
  "HHR",
  "LAX",
  "MAD",
  "TOJ",
  "IXM",
  "MAN",
  "MNL",
  "MRS",
  "QAD",
  "MEL",
  "MIA",
  "LIN",
  "MXP",
  "MSP",
  "STP",
  "YUL",
  "BOM",
  "QAI",
  "MUC",
  "LGA",
  "NYC",
  "TSS",
  "EWR",
  "ITM",
  "OSL",
  "PAO",
  "PAR",
  "PER",
  "PHX",
  "PDX",
  "IXD",
  "PNQ",
  "QRO",
  "IXR",
  "GIG",
  "FCO",
  "SXV",
  "QAK",
  "SJC",
  "WVI",
  "SCL",
  "GRU",
  "BFI",
  "ICN",
  "QPG",
  "SIN",
  "SOF",
  "SSE",
  "STL",
  "BMA",
  "STV",
  "SYD",
  "WSI",
  "TYO",
  "NRT",
  "YYZ",
  "YVR",
  "VNS",
  "VIE",
  "WLG"
]

class Pop(BaseModel):
    edge_requests = int


class FastlyStatsResponse(BaseModel):
    stats: Dict[str, Pop]

    model_config = ConfigDict(extra="ignore")

    @validator('stats')
    def in_list_of_pops(cls, v):
        for k in v:
            if not (k in FASTLY_POPS):
                raise ValueError("Pop must be in list of valid Fastly points of presence.")
        return v
    