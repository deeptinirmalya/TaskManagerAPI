from fastapi import APIRouter, HTTPException, Request, Depends, Header
from fastapi.encoders import jsonable_encoder
from db.session import get_db, test_db_connection
from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc
from security.auth import get_client_info, create_access_token, token_required
import requests
from core.config import settings
import utils.util as util
from db.base import Expense, ExpenseLog, ExpenseType
from fastapi.responses import JSONResponse
import uuid
from typing import Any
from worker.task import extract_transaction_from_telegram

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
        stmt = select(Expense).where(Expense.type == ExpenseType.INITIALIZE)
        res = db.execute(stmt).scalar_one_or_none()

        if not res:
            raise HTTPException(status_code=409, detail="you dont initialize the money initialize first")
        
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
    


temp_data = {}
@expenses_router.post("/telegram/webhook/{secret}")
async def telegram_webhook(
    request: Request,
    secret: str
):

    if secret != settings.TELEGRAM_WEBHOOK_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid Secret"
        )

    data = await request.json()

    # print(data)
    message = data.get("message", {})

    user_id = message.get("from", {}).get("id")

    caption = message.get("caption")

    photos = message.get("photo", [])
    file_id = photos[-1]["file_id"] if photos else None

    # print(f"user_id {user_id}")
    # print(f"caption {caption}")
    # print(f"file_id {file_id}")

    try:

        if "callback_query" in data:

            callback = data["callback_query"]

            action = callback["data"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]

            user_data = temp_data.pop(chat_id, None)

            print(f"from call back: ", user_data)

            if not user_data:

                requests.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                    json={
                        "callback_query_id": callback["id"],
                        "text": "Already processed."
                    }
                )

                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Ok",
                        "data": None,
                        "error": None
                    }
                )

            requests.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {
                        "inline_keyboard": []
                    }
                }
            )

            requests.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ Selected platform: {action}"
                }
            )

            if action == "phonepe":
                text = (
                    "✅ Image received successfully.\n"
                    "Platform: PhonePe\n"
                    "Processing started..."
                )
                extract_transaction_from_telegram(chat_id, user_data["caption"], user_data["file_id"], settings.TELEGRAM_BOT_TOKEN, settings.GEMINI_KEY, "phonepe")


            elif action == "navi":
                text = (
                    "✅ Image received successfully.\n"
                    "Platform: Navi\n"
                    "Processing started...")
                extract_transaction_from_telegram(chat_id, user_data["caption"], user_data["file_id"], settings.TELEGRAM_BOT_TOKEN, settings.GEMINI_KEY, "navi")

            elif action == "google_pay":
                text = (
                    "✅ Image received successfully.\n"
                    "Platform: Google Pay\n"
                    "Processing started..."
                )
                extract_transaction_from_telegram(chat_id, user_data["caption"], user_data["file_id"], settings.TELEGRAM_BOT_TOKEN, settings.GEMINI_KEY, "google_pay")

            else:
                text = "❌ Invalid option"

            # requests.post(
            #     f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            #     json={
            #         "chat_id": chat_id,
            #         "text": text
            #     }
            # )

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Ok",
                    "data": None,
                    "error": None
                }
            )


        if "message" in data:

            message = data["message"]

            if "photo" not in message:

                requests.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": message["chat"]["id"],
                        "text": "⚠️ Please send an image with caption."
                    }
                )

                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Ok",
                        "data": None,
                        "error": None
                    }
                )


            user_id = message["from"]["id"]
            
            chat_id = message["chat"]["id"]

            if user_id != settings.TELEGRAM_USER_ID:
                print("user_id not match")
                requests.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "❌ You Are Not Allow To Action ❌"
                    }
                )
                raise HTTPException(status_code=403, detail="You Are Not Allowed To Action.")

            caption = message.get("caption", "")

            photo = message["photo"][-1]

            file_id = photo["file_id"]

            temp_data[chat_id] = {
                "user_id": user_id,
                "caption": caption,
                "file_id": file_id
            }
            # print(f"from initial :", temp_data[chat_id])
            requests.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text":
                        "Choose The UPI platform:",
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "PhonePe",
                                    "callback_data": "phonepe"
                                }
                            ],
                            [
                                {
                                    "text": "Navi",
                                    "callback_data": "navi"
                                }
                            ],
                            [
                                {
                                    "text": "Google Pay",
                                    "callback_data": "google_pay"
                                }
                            ]
                        ]
                    }
                }
            )

            return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Ok",
                        "data": None,
                        "error": None
                    }
                )


        return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Ok",
                    "data": None,
                    "error": None
                }
            )


    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "error": str(e)
            }
        )
    

@expenses_router.post("/telegram/add-expenses")
async def add_expense_throuh_telegram(
    request: Request,
    db: Session = Depends(get_db),
    x_api_key: str = Header(..., alias="X-API-Key")
):
    payload = await request.json()

    if x_api_key != settings.MASTER_API_KEY:
        raise HTTPException(status_code=403, detail="Unuthorised")
    try:
        outer_success = payload.get('sucess')
        outer_error = payload.get('error')

        data_block = payload.get('data', {})
        chat_id = data_block.get('chat_id')
        caption = data_block.get('caption')

        result_block = data_block.get('result', {})
        inner_data = result_block.get('data', {})

        inner_success = result_block.get('success')
        inner_error = result_block.get('error')

        date = inner_data.get('date')
        time = inner_data.get('time')
        transaction_type = inner_data.get('transaction_type')
        amount_numeric = inner_data.get('amount_numeric')
        bank_name = inner_data.get('bank_name')

        if not outer_success:
            requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"❌ transaction failed with outer error = {outer_error}"
                }
            )
            raise HTTPException(status_code=500, detail=f"❌ transaction failed with outer error = {outer_error}")
            
        if not inner_success:
            requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"❌ transaction failed with inner error = {inner_error}"
                }
            )
            raise HTTPException(status_code=500, detail=f"❌ transaction failed with inner error = {inner_error}")


        bank_name = "ippb" if bank_name.lower() == "navi" else bank_name
        print(f"Chat ID: {chat_id}")
        print(f"Caption: {caption}")
        print(f"Date: {date}")
        print(f"Time: {time}")
        print(f"Transaction Type: {transaction_type}")
        print(f"Amount (Numeric): {amount_numeric}")
        print(f"Bank Name: {bank_name}")

        latest_account_balance_stmt = select(Expense.ippb, Expense.cash, Expense.sbi).order_by(desc(Expense.id)).limit(1)
        previous_balance = db.execute(latest_account_balance_stmt).mappings().first()

        balance = {
            "cash": previous_balance["cash"],
            "ippb": previous_balance["ippb"],
            "sbi": previous_balance["sbi"]
        }

        if transaction_type.lower() == "credit":
            balance[bank_name] = balance[bank_name] + amount_numeric

            new_txn = Expense(
                type = ExpenseType(transaction_type.lower()),
                date = date,
                time = time,
                mode = "upi",
                bucket_name = bank_name.lower(),
                amount = amount_numeric,
                purpose = caption,
                cash = balance["cash"],
                ippb = balance["ippb"],
                sbi = balance["sbi"],
                created_at = util.get_now_utc()
            )

            
        if transaction_type.lower() == "debit":
            balance[bank_name.lower()] = balance[bank_name.lower()] - amount_numeric

            if balance[bank_name.lower()] < 0:
                requests.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": f"With this transaction the {bank_name.lower()} balance will be in -ve"
                    }
                )
                raise HTTPException(status_code=409, detail=f"With this transaction the {bank_name.lower()} balance will be in -ve")
            

            new_txn = Expense(
                type = ExpenseType(transaction_type.lower()),
                date = date,
                time = time,
                mode = "upi",
                bucket_name = bank_name.lower(),
                amount = amount_numeric,
                purpose = caption,
                cash = balance["cash"],
                ippb = balance["ippb"],
                sbi = balance["sbi"],
                created_at = util.get_now_utc()
            )
        
        db.add(new_txn)
        db.commit()



        requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "✅ transaction added sucess fully ✅"
            }
        )

        return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "message": "Ok",
            "data": None,
            "error": None
        }
    )


    except HTTPException as httpe:
        raise httpe
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"❌ transactin add failed at end point = {e}"
                }
            )
        # raise HTTPException(status_code=500, detail="Internal Server Error")
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "message": "Ok",
                "data": None,
                "error": None
            }
        )
    




