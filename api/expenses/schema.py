import datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class ExpenseCreate(BaseModel):
    type: Literal['credit', 'debit']
    date: datetime.date
    time: datetime.time
    mode: Literal['upi', 'bank_transaction', 'cash', 'card']
    bucket_name: Literal['sbi', 'cash', 'ippb'] = Field(..., max_length=5)
    amount: float = Field(..., gt=0)
    purpose: str = Field(..., max_length=200)

    @model_validator(mode='after')
    def validate_conditional_rules(self) -> 'ExpenseCreate':
        if self.mode == 'cash' and self.bucket_name != 'cash':
            raise ValueError("If mode is 'cash', bucket_name must be 'cash'")
            
        if self.mode == 'card':
            if self.bucket_name != 'sbi':
                raise ValueError("If mode is 'card', bucket_name must be 'sbi'")
            if self.type != 'debit':
                raise ValueError("If mode is 'card', type must be 'debit'")
                
        return self

    class Config:
        json_encoders = {
            datetime.date: lambda v: v.strftime('%Y-%m-%d'),
            datetime.time: lambda v: v.strftime('%H:%M')
        }



class InitializeBalance(BaseModel):
    ippb_balance: float = Field(
        default=0.0, 
        ge=0.0, 
        description="Current balance in the India Post Payments Bank account."
    )
    
    sbi_balance: float = Field(
        default=0.0, 
        ge=0.0, 
        description="Current balance in the State Bank of India account."
    )
    
    cash_balance: float = Field(
        default=0.0, 
        ge=0.0, 
        description="Physical cash-on-hand balance."
    )
    password: str = Field(
        ...,  
        max_length=128, 
        description="The account password or PIN to authorize this request."
    )