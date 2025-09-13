# app/services/employee_service.py
from typing import List, Optional, Dict, Any, Union
from pymongo.errors import DuplicateKeyError
from datetime import datetime, time, date
from app.db import get_employees_collection

# ---- Helper to normalize/serialize Mongo documents for API responses ----
def employee_helper(emp: Dict[str, Any]) -> Dict[str, Any]:
    if not emp:
        return None
    jd = emp.get("joining_date")
    if jd:
        # jd may be datetime or date or string
        try:
            jd_str = jd.date().isoformat() if hasattr(jd, "date") else str(jd)
        except Exception:
            jd_str = str(jd)
    else:
        jd_str = None

    return {
        "id": str(emp.get("_id")),
        "employee_id": emp.get("employee_id"),
        "name": emp.get("name"),
        "department": emp.get("department"),
        "salary": emp.get("salary"),
        "joining_date": jd_str,
        "skills": emp.get("skills", []),
    }

# ---- Internal utils ----
def _ensure_datetime(value: Union[str, date, datetime]) -> datetime:
    """Convert date/ISO-string to datetime (at midnight) for Mongo ISODate storage."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    # assume ISO string
    return datetime.fromisoformat(value)

def _prepare_doc_for_insert(payload: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(payload)
    if "joining_date" in doc and doc["joining_date"] is not None:
        doc["joining_date"] = _ensure_datetime(doc["joining_date"])
    return doc

def _prepare_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    u = {k: v for k, v in updates.items() if v is not None}
    if "joining_date" in u:
        u["joining_date"] = _ensure_datetime(u["joining_date"])
    return u

# ---- CRUD + Querying service functions ----

async def create_employee(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a new employee. Raises DuplicateKeyError (from pymongo) when employee_id exists.
    Returns the created document serialized via employee_helper.
    """
    coll = get_employees_collection()
    doc = _prepare_doc_for_insert(payload)
    try:
        res = await coll.insert_one(doc)
    except DuplicateKeyError:
        # bubble up for router to convert to HTTP 400
        raise DuplicateKeyError("employee_id must be unique")
    created = await coll.find_one({"_id": res.inserted_id})
    return employee_helper(created)

async def get_employee_by_id(employee_id: str) -> Optional[Dict[str, Any]]:
    coll = get_employees_collection()
    doc = await coll.find_one({"employee_id": employee_id})
    return employee_helper(doc) if doc else None

async def update_employee(employee_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Partial update: only provided fields are set.
    Returns:
      - None if employee not found
      - {"no_update_fields": True} if client sent no fields to update
      - serialized doc on success
    """
    coll = get_employees_collection()
    update_doc = _prepare_updates(updates)
    if not update_doc:
        return {"no_update_fields": True}
    res = await coll.update_one({"employee_id": employee_id}, {"$set": update_doc})
    if res.matched_count == 0:
        return None
    doc = await coll.find_one({"employee_id": employee_id})
    return employee_helper(doc)

async def delete_employee(employee_id: str) -> bool:
    coll = get_employees_collection()
    res = await coll.delete_one({"employee_id": employee_id})
    return res.deleted_count == 1

async def list_employees(department: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    If department provided, filter by it and sort by joining_date (newest first).
    Otherwise list all employees sorted by joining_date.
    Supports skip/limit pagination.
    """
    coll = get_employees_collection()
    query = {}
    if department:
        query["department"] = department
    cursor = coll.find(query).sort("joining_date", -1).skip(skip).limit(limit)
    return [employee_helper(doc) async for doc in cursor]

async def average_salary_by_department() -> List[Dict[str, Any]]:
    """
    Aggregation: average salary grouped by department.
    Returns list of {"department": <dept>, "avg_salary": <rounded>}
    """
    coll = get_employees_collection()
    pipeline = [
        {"$group": {"_id": "$department", "avg_salary": {"$avg": "$salary"}}},
        {"$project": {"department": "$_id", "avg_salary": {"$round": ["$avg_salary", 0]}, "_id": 0}},
        {"$sort": {"department": 1}}
    ]
    cursor = coll.aggregate(pipeline)
    return [doc async for doc in cursor]

async def search_employees_by_skill(skill: str, skip: int = 0, limit: int = 100, case_insensitive: bool = False) -> List[Dict[str, Any]]:
    """
    Search employees having `skill` in their skills array.
    Default is exact match. Set case_insensitive=True for case-insensitive match.
    """
    coll = get_employees_collection()
    if case_insensitive:
        cursor = coll.find({"skills": {"$elemMatch": {"$regex": f"^{skill}$", "$options": "i"}}}).sort("joining_date", -1).skip(skip).limit(limit)
    else:
        cursor = coll.find({"skills": skill}).sort("joining_date", -1).skip(skip).limit(limit)
    return [employee_helper(doc) async for doc in cursor]
