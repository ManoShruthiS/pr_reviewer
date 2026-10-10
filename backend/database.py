from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone

# In-memory SQLite database ensures zero persistent history on disk.
# Every execution starts completely fresh without storing previous runs.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    pr_url = Column(String, nullable=False)
    pr_title = Column(String)
    risk_score = Column(Integer)
    issues_json = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.drop_all(engine)
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
    review_id = review.id
    session.close()
    return review_id


def get_all_reviews():
    session = SessionLocal()
    reviews = session.query(Review).order_by(Review.created_at.desc()).limit(25).all()
    session.close()
    return reviews


def get_review_by_id(review_id: int):
    session = SessionLocal()
    review = session.query(Review).filter(Review.id == review_id).first()
    session.close()
    return review
