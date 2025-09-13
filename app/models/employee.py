# app/models/employee.py
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

class EmployeeBase(BaseModel):
    employee_id: str = Field(..., example="E123")
    name: str = Field(..., example="John Doe")
    department: str = Field(..., example="Engineering")
    salary: float = Field(..., example=75000)
    joining_date: date = Field(..., example="2023-01-15")
    skills: List[str] = Field(..., example=["Python", "MongoDB", "APIs"])

class EmployeeCreate(EmployeeBase):
    pass  

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    joining_date: Optional[date] = None
    skills: Optional[List[str]] = None

class EmployeeOut(EmployeeBase):
    id: str  

    class Config:
        from_attributes = True
