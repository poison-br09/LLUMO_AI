from bson import ObjectId
from typing import List, Optional, Dict, Any
from app.db import get_employees_collection
from datetime import datetime
from pymongo import ASCENDING, DESCENDING

async def create_indexes() -> None:
    coll = get_employees_collection()
    await coll.create_index("employee_id", unique=True)
    await coll.create_index("department")
    await coll.create_index("skills")
    await coll.create_index("joining_date")

def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "employee_id": doc.get("employee_id"),
        "name": doc.get("name"),
        "department": doc.get("department"),
        "salary": doc.get("salary"),
        "joining_date": doc.get("joining_date").date().isoformat() if isinstance(doc.get("joining_date"), datetime) else (doc.get("joining_date") or None),
        "skills": doc.get("skills", []),
    }

async def insert_employee(doc: Dict[str, Any]) -> Dict[str, Any]:
    coll = get_employees_collection()
    res = await coll.insert_one(doc)
    created = await coll.find_one({"_id": res.inserted_id})
    return _serialize(created)

async def find_by_employee_id(employee_id: str) -> Optional[Dict[str, Any]]:
    coll = get_employees_collection()
    doc = await coll.find_one({"employee_id": employee_id})
    return _serialize(doc) if doc else None

async def update_by_employee_id(employee_id: str, update_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    coll = get_employees_collection()
    res = await coll.update_one({"employee_id": employee_id}, {"$set": update_doc})
    if res.matched_count == 0:
        return None
    doc = await coll.find_one({"employee_id": employee_id})
    return _serialize(doc)

async def delete_by_employee_id(employee_id: str) -> bool:
    coll = get_employees_collection()
    res = await coll.delete_one({"employee_id": employee_id})
    return res.deleted_count == 1

async def list_by_department(department: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    coll = get_employees_collection()
    cursor = coll.find({"department": department}).sort("joining_date", DESCENDING).skip(skip).limit(limit)
    results = [ _serialize(doc) async for doc in cursor ]
    return results

async def list_all(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    coll = get_employees_collection()
    cursor = coll.find({}).sort("joining_date", DESCENDING).skip(skip).limit(limit)
    return [ _serialize(doc) async for doc in cursor ]

async def aggregate_avg_salary_by_dept() -> List[Dict[str, Any]]:
    coll = get_employees_collection()
    pipeline = [
        {"$group": {"_id": "$department", "avg_salary": {"$avg": "$salary"}}},
        {"$project": {"department": "$_id", "avg_salary": {"$round": ["$avg_salary", 0]}, "_id": 0}},
        {"$sort": {"department": 1}}
    ]
    cursor = coll.aggregate(pipeline)
    return [doc async for doc in cursor]

async def search_by_skill(skill: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    coll = get_employees_collection()
    cursor = coll.find({"skills": skill}).sort("joining_date", DESCENDING).skip(skip).limit(limit)
    return [ _serialize(doc) async for doc in cursor ]

async def list_employees_cursor(department: Optional[str] = None, limit: int = 50, last_seen: str = None):
    """
    last_seen is an ISO datetime string representing the cursor (joining_date).
    Returns documents with joining_date < last_seen (newest first).
    """
    coll = get_employees_collection()
    query = {}
    if department:
        query["department"] = department
    if last_seen:
        last_dt = datetime.fromisoformat(last_seen)
        query["joining_date"] = {"$lt": last_dt}
    cursor = coll.find(query).sort("joining_date", -1).limit(limit)
    return [employee_helper(doc) async for doc in cursor]