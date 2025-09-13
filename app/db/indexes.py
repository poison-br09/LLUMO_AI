# scripts/setup_db.py (one-time)
from app.db import get_db
from pymongo import ASCENDING

def ensure_collection_schema():
    db = get_db()
    coll_name = "employees"
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["employee_id", "name", "department", "salary", "joining_date", "skills"],
            "properties": {
                "employee_id": {"bsonType": "string"},
                "name": {"bsonType": "string"},
                "department": {"bsonType": "string"},
                "salary": {"bsonType": "double"},
                "joining_date": {"bsonType": "date"},
                "skills": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"}
                }
            }
        }
    }
    try:
        # If collection exists, use collMod to add validator
        db.command({
            "collMod": coll_name,
            "validator": validator,
            "validationLevel": "moderate"
        })
    except Exception:
        # If collMod fails (collection might not exist), create the collection with validator
        db.create_collection(coll_name, validator=validator)
    # create index
    db[coll_name].create_index("employee_id", unique=True)
