"""
Database setup and ORM models.

Uses SQLite by default (file: backtest.db) so the project runs out of the
box with zero external setup. Swapping to Postgres or MySQL is a one-line
change: just replace DATABASE_URL below with your connection string, e.g.

    postgresql://user:password@localhost:5432/qode_backtest
    mysql+pymysql://user:password@localhost:3306/qode_backtest

Everything else (models, queries, engine) stays the same because we use
SQLAlchemy as the abstraction layer.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = "sqlite:///backtest.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sector = Column(String(100))

    prices = relationship("Price", back_populates="company", cascade="all, delete-orphan")
    fundamentals = relationship("Fundamental", back_populates="company", cascade="all, delete-orphan")


class Price(Base):
    """Daily OHLCV data, one row per company per trading day."""
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    volume = Column(Integer)

    company = relationship("Company", back_populates="prices")

    __table_args__ = (
        Index("ix_prices_company_date", "company_id", "date"),
    )


class Fundamental(Base):
    """
    Quarterly fundamental snapshot per company.
    'report_date' is when the figure was actually published/known — this is
    what the backtest engine uses to avoid future data leakage (it never
    looks at a fundamental row whose report_date is after the rebalance date).
    """
    __tablename__ = "fundamentals"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_date = Column(Date, nullable=False)

    market_cap_cr = Column(Float)      # market cap in INR Crores
    pat_cr = Column(Float)             # profit after tax, INR Crores
    revenue_cr = Column(Float)
    roce = Column(Float)               # %
    roe = Column(Float)                # %
    pe_ratio = Column(Float)
    debt_to_equity = Column(Float)

    company = relationship("Company", back_populates="fundamentals")

    __table_args__ = (
        Index("ix_fund_company_date", "company_id", "report_date"),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
