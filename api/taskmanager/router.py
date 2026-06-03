from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from db.session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, text
from security.auth import get_client_info, create_access_token, token_required
from db.base import Task
from core.config import settings
from datetime import time
import utils.util as util
from pushbullet import Pushbullet

taskmanager_router = APIRouter()


@taskmanager_router.get("/view-tasks")
def view_tasks(db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        stmt = select(Task.id, Task.task_name).where(Task.is_complete == False)
        result = db.execute(stmt).mappings().all()
        data = jsonable_encoder([dict(row) for row in result])

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Data retrived sucesully",
                "data": data,
                "error": None
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@taskmanager_router.get("/view-completed-tasks")
def view_completed_tasks(db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        stmt = select(Task.id, Task.task_name).where(Task.is_complete == True)
        result = db.execute(stmt).mappings().all()
        data = jsonable_encoder([dict(row) for row in result])

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Data retrived sucesully",
                "data": data,
                "error": None
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    


@taskmanager_router.get("/add-task")
def add_tasks(task: str, db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        new_task = Task(
            created_at = util.get_now_utc(),
            task_name = task
        )

        db.add(new_task)

        db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Task Added sucesuly",
                "data": None,
                "error": None
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@taskmanager_router.get("/mark-task-as-complete")
def mark_task_complete(task_id: int, db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
            stmt = select(Task.is_complete).where(Task.id == task_id)
            res = db.execute(stmt).mappings().first() 

            if res is None:
                raise HTTPException(status_code=404, detail="No task found")
                
            if res["is_complete"] is True:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Task is already completed",
                        "data": None,
                        "error": None
                    }
                )

            db.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(is_complete=True)
            )
            db.commit()

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Successfully marked as complete",
                    "data": None,
                    "error": None
                }
            )
    except HTTPException as http:
        raise http
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@taskmanager_router.get("/clear-completed-task")
def clear_completed_task(db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        stmt = delete(Task).where(Task.is_complete == True)
        db.execute(stmt)
        db.commit()

        db.execute(text("OPTIMIZE TABLE tasks"))

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Completed tasks cleared and space optimized successfully",
                "data": None,
                "error": None
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

    
@taskmanager_router.get("/task-reminder")
def task_reminder(key: str, db: Session = Depends(get_db)):
    try:
        if key != settings.API_ACCESS_KEY:
            raise HTTPException(status_code=409, detail="Invalid Key")
        
        now = util.get_now_utc().time()

        start = time(18, 45)  
        end   = time(1, 15)  

        if now >= start or now <= end:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Not the right time",
                    "data": None,
                    "error": None
                }
            )

        stmt = select(Task.task_name).where(Task.is_complete == False)
        result = db.execute(stmt).scalars().all()

        final_result = "\n\n".join(result) if result else None

        if final_result is None:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "no pending tasks",
                    "data": None,
                    "error": None
                }
            )
            
        try:
            pb = Pushbullet(settings.PUSHBULLET_AUTH_KEY)
            pb.push_note("🤖Pending Tasks:", final_result)
        except Exception as e:
            raise HTTPException(status_code=403, detail="Pushbullet error")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Task send successfully",
                "data": None,
                "error": None
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    



@taskmanager_router.get("/clear-notifications")
def clear_notifications(key: str):


    try:
        if key != settings.API_ACCESS_KEY:
            raise HTTPException(status_code=409, detail="Invalid Key")
        
        pb = Pushbullet(settings.PUSHBULLET_AUTH_KEY)
        pushes = pb.get_pushes()

        for push in pushes:
            push_id = push.get("iden")
            if not push_id:
                continue
            try:
                pb.delete_push(push_id)
            except Exception as e:
                return f"Delete failed: {e}"
            
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Complete",
                "data": None,
                "error": None
            }
        )
            
    except HTTPException as httpe:
        raise httpe

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")