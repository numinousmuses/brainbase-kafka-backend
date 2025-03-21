# /schemas/basedagent.py
from pydantic import BaseModel
from typing import Optional, List

class BasedAgentOutput(BaseModel):
    output: str
    type: str  # Expected values: "based", "diff", or "response"
    based_filename: Optional[str] = None
    message: Optional[str] = None

class TriageContextOutput(BaseModel):
    summary: str
    extraction_indices: List[List[int]]  # 2D array of line number indices
    genNewFile: bool
    files_list: List[str]
    plain_response: Optional[bool] = False
    extracted_context: Optional[str] = None
