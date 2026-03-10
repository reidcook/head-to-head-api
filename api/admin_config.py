from pydantic import BaseModel, Field


# Class used for configuring ag-grid + admin config stuff
class FieldConfig(BaseModel):
    field: str
    headerName: str
    form_type: str = Field(default="input")
    map_to: str = Field(default="")
    options: list[str] = Field(default=[])
    
