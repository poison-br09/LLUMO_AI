# app/routes/employee_routes.py
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from pymongo.errors import DuplicateKeyError

from app.services import employee_service
from app.core.deps import get_current_user

router = APIRouter()

from app.models.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut

# --- Section 3: Querying & Aggregation (static routes first) ---

# 5. List by department (with pagination)
@router.get("/", response_model=List[EmployeeOut])
async def list_employees(
    department: Optional[str] = Query(None, description="Filter by department"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    results = await employee_service.list_employees(department=department, skip=skip, limit=limit)
    return results

# 6. Avg salary by department
@router.get("/avg-salary", response_model=List[Dict[str, Any]])
async def avg_salary_by_department():
    results = await employee_service.avg_salary_by_department()
    return results

# 7. Search by skill
@router.get("/search", response_model=List[EmployeeOut])
async def search_by_skill(
    skill: str = Query(..., description="Skill to search (exact match in skills array)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    case_insensitive: bool = Query(False),
):
    results = await employee_service.search_employees_by_skill(
        skill, skip=skip, limit=limit, case_insensitive=case_insensitive
    )
    return results  # will be [] if no matches

# --- Core CRUD (dynamic route last) ---

# Create employee (protected; remove user param if you don't want auth)
@router.post("/", response_model=EmployeeOut, status_code=201)
async def create_employee(emp: EmployeeCreate, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    try:
        created = await employee_service.create_employee(emp.dict())
        return created
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="employee_id must be unique")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# Get by employee_id
@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(employee_id: str):
    emp = await employee_service.get_employee_by_id(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp

# Update (partial)
@router.put("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: str,
    updates: EmployeeUpdate,
    user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    res = await employee_service.update_employee(employee_id, updates.dict(exclude_unset=True))
    if res is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if isinstance(res, dict) and res.get("no_update_fields"):
        raise HTTPException(status_code=400, detail="No fields provided for update")
    return res

# Delete
@router.delete("/{employee_id}")
async def delete_employee(employee_id: str): # user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    deleted = await employee_service.delete_employee(employee_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}
