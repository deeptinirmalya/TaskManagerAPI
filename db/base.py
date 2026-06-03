import enum
from datetime import date, datetime, time
from decimal import Decimal
from sqlalchemy import Date, DateTime, Enum, Numeric, String, Time, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExpenseType(enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    INITIALIZE = "initialize"


class Expense(Base):
    __tablename__ = "expences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[ExpenseType] = mapped_column(
        Enum(ExpenseType, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(5), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    cash: Mapped[float] = mapped_column(nullable=False)
    ippb: Mapped[float] = mapped_column(nullable=False)
    sbi: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, type={self.type.value}, amount={self.amount}, purpose='{self.purpose}')>"
    

class ExpenseLog(Base):
    __tablename__ = "expences_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    initialize: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_debit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_credit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    initialize_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ExpenseLog(id={self.id}, "
            f"period={self.from_date} to {self.to_date}, "
            f"initialize={self.initialize})>"
        )

class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    task_name: Mapped[str] = mapped_column(String(500), nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name='{self.task_name[:30]}', complete={self.is_complete})>"