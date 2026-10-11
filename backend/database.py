from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

engine = create_engine("sqlite:///reviews.db")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    pr_url = Column(String, nullable=False)
    pr_title = Column(String)
    risk_score = Column(Integer)
    issues_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def save_review(pr_url: str, pr_title: str, risk_score: int, issues_json: str):
    session = SessionLocal()
    review = Review(
        pr_url=pr_url,
        pr_title=pr_title,
        risk_score=risk_score,
        issues_json=issues_json
    )
    session.add(review)
    session.commit()
    session.close()


def get_all_reviews():
    session = SessionLocal()
    reviews = session.query(Review).order_by(Review.created_at.desc()).all()
    session.close()
    return reviews
