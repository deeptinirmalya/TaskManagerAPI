from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.encoders import jsonable_encoder
from db.session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc
from security.auth import get_client_info, create_access_token, token_required
# from .schema import LoginSchema
from core.config import settings
import utils.util as util
from db.base import Expense, ExpenseLog, ExpenseType
from fastapi.responses import JSONResponse
import uuid

from .schema import ExpenseCreate, InitializeBalance

expenses_router = APIRouter()


@expenses_router.get("/view-expenses")
def view_expenses(db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
            expenses_stmt = select(
                Expense.id, Expense.amount, Expense.date, Expense.purpose, 
                Expense.time, Expense.mode, Expense.bucket_name, Expense.type
            ).where(Expense.type != ExpenseType.INITIALIZE).order_by(desc(Expense.id))
            
            expenses_result = db.execute(expenses_stmt).mappings().all()
            
            expenses = []
            for row in expenses_result:
                row_dict = dict(row)
                if row_dict.get('date') and hasattr(row_dict['date'], 'strftime'):
                    row_dict['date'] = row_dict['date'].strftime('%d-%m-%Y') 
                if row_dict.get('time') and hasattr(row_dict['time'], 'strftime'):
                    row_dict['time'] = row_dict['time'].strftime('%H:%M')
                expenses.append(row_dict)

            latest_account_balance_stmt = select(Expense.ippb, Expense.cash, Expense.sbi).order_by(desc(Expense.id)).limit(1)
            balance_res = db.execute(latest_account_balance_stmt).mappings().first()
            account_balance = dict(balance_res) if balance_res else {}

            total_debit_stmt = select(func.sum(Expense.amount).label("total_spend")).where(Expense.type == ExpenseType.DEBIT)
            debit_res = db.execute(total_debit_stmt).mappings().first()
            total_debit = float(debit_res["total_spend"]) if debit_res and debit_res["total_spend"] is not None else 0.0

            total_credit_stmt = select(func.sum(Expense.amount).label("total_spend")).where(Expense.type == ExpenseType.CREDIT)
            credit_res = db.execute(total_credit_stmt).mappings().first()
            total_credit = float(credit_res["total_spend"]) if credit_res and credit_res["total_spend"] is not None else 0.0

            return JSONResponse(
                status_code=200,
                content=jsonable_encoder({
                    "success": True,
                    "message": "Data retrieved successfully",
                    "data": {
                        "expenses": expenses,
                        "account_balance": account_balance,
                        "total_credit": total_credit,
                        "total_debit": total_debit
                    },
                    "error": None
                })
            )
    except HTTPException as http:
        raise http
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@expenses_router.post("/add-expense")
def add_expense(data: ExpenseCreate, db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        latest_account_balance_stmt = select(Expense.ippb, Expense.cash, Expense.sbi).order_by(desc(Expense.id)).limit(1)
        previous_balance = db.execute(latest_account_balance_stmt).mappings().first()

        balance = {
            "cash": previous_balance["cash"],
            "ippb": previous_balance["ippb"],
            "sbi": previous_balance["sbi"]
        }

        if data.type == "credit":
            balance[data.bucket_name] = balance[data.bucket_name] + data.amount

            new_txn = Expense(
                type = ExpenseType(data.type),
                date = data.date,
                time = data.time,
                mode = data.mode,
                bucket_name = data.bucket_name,
                amount = data.amount,
                purpose = data.purpose,
                cash = balance["cash"],
                ippb = balance["ippb"],
                sbi = balance["sbi"],
                created_at = util.get_now_utc()
            )

            
        if data.type == "debit":
            balance[data.bucket_name] = balance[data.bucket_name] - data.amount

            if balance[data.bucket_name] < 0:
                raise HTTPException(status_code=409, detail=f"With this transaction the {data.bucket_name} balance will be in -ve")
            

            new_txn = Expense(
                type = ExpenseType(data.type),
                date = data.date,
                time = data.time,
                mode = data.mode,
                bucket_name = data.bucket_name,
                amount = data.amount,
                purpose = data.purpose,
                cash = balance["cash"],
                ippb = balance["ippb"],
                sbi = balance["sbi"],
                created_at = util.get_now_utc()
            )
        
        db.add(new_txn)
        db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Transaction added sucessfuly",
                "data": None,
                "error": None
            }
        )


    except HTTPException as httpe:
        raise httpe
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    



@expenses_router.post("/initialize-account-balance")
def initialize_account_balance(data: InitializeBalance, db: Session = Depends(get_db), _user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:

        if data.password != settings.PASSWORD:
            raise HTTPException(status_code=409, detail="Invalid Password")
        
        stmt = select(Expense).where(Expense.type == ExpenseType.INITIALIZE)
        res = db.execute(stmt).scalar_one_or_none()

        if res:
            raise HTTPException(status_code=409, detail="You already have an active initialization.")
        
        current_time_utc = util.get_now_utc()
        
        new_txn = Expense(
            type=ExpenseType.INITIALIZE,
            date=current_time_utc.date(),
            time=current_time_utc.time(),
            mode="Initialize",
            bucket_name="InIt",
            amount=0.0,
            purpose="Initialize",
            cash=data.cash_balance,
            ippb=data.ippb_balance,
            sbi=data.sbi_balance,
            created_at=current_time_utc
        )
        db.add(new_txn)
        db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Transaction added sucessfuly",
                "data": None,
                "error": None
            }
        )


    except HTTPException as httpe:
        raise httpe
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")