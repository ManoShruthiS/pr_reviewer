# ==============================================================================
# FILE: database.py
# PURPOSE: Stores and retrieves past code review results using a lightweight database.
#
# HOW TO THINK OF THIS FILE (SIMPLE ANALOGY):
# Think of this like a digital notebook or filing cabinet.
# Whenever the user analyzes a GitHub Pull Request, this file writes down:
# 1. Which PR was checked
# 2. What the risk score was
# 3. What problems were found
# 4. The exact date and time it was reviewed
#
# NOTICE: We use an "In-Memory" database (sqlite:///:memory:).
# That means it keeps data only in computer RAM while the server is running.
# When you stop the server, it cleanly wipes the slate clean without leaving cluttered files on your hard drive!
# ==============================================================================

# SQLAlchemy is a popular Python library that makes talking to databases easy
# instead of having to write complicated raw SQL queries manually.
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# datetime is Python's built-in tool for handling dates, clocks, and timestamps
from datetime import datetime, timezone

# ------------------------------------------------------------------------------
# STEP 1: CREATE THE DATABASE ENGINE (THE CONNECTION)
# ------------------------------------------------------------------------------
# "sqlite:///:memory:" tells Python:
# "Do not save a big file on the hard drive; just keep this database in computer RAM memory."
# check_same_thread=False allows multiple web requests to use the database safely at the same time.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# SessionLocal is like a factory that opens a new conversation (session) with the database whenever we need to save or read data.
SessionLocal = sessionmaker(bind=engine)

# Base is a helper blueprint from SQLAlchemy that our database tables inherit from.
Base = declarative_base()


# ------------------------------------------------------------------------------
# STEP 2: DEFINE THE DATA TABLE STRUCTURE ("THE SPREADSHEET")
# ------------------------------------------------------------------------------
# This class defines what a "Review" record looks like in our database.
# Think of it like defining the columns of an Excel spreadsheet.
class Review(Base):
    __tablename__ = "reviews"  # Name of the table inside SQLite

    # Column 1: A unique ID number for each review (e.g. 1, 2, 3...)
    id = Column(Integer, primary_key=True, index=True)

    # Column 2: The web link to the GitHub Pull Request (e.g. "https://github.com/facebook/react/pull/123")
    pr_url = Column(String, nullable=False)

    # Column 3: The human-readable title of the Pull Request (e.g. "Fix login button bug")
    pr_title = Column(String)

    # Column 4: The calculated risk score from 0 to 100 (e.g. 85 = dangerous, 10 = safe)
    risk_score = Column(Integer)

    # Column 5: The complete list of detected bugs and security issues, saved as JSON text
    issues_json = Column(Text)

    # Column 6: The exact date and time when this review was performed (automatically sets to right now)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ------------------------------------------------------------------------------
# STEP 3: DATABASE HELPER FUNCTIONS (ACTIONS)
# ------------------------------------------------------------------------------

# Function: Reset and initialize the database
# When the app starts, this wipes out old test tables and creates fresh new empty ones.
def init_db():
    Base.metadata.drop_all(engine)    # Erase any old tables
    Base.metadata.create_all(engine)  # Create brand new tables


# Function: Save a new review into the database
# Takes in the PR link, title, score, and problems, and writes them down.
def save_review(pr_url: str, pr_title: str, risk_score: int, issues_json: str):
    # 1. Open a new conversation (session) with the database
    session = SessionLocal()

    # 2. Package up the information into a single Review object
    review = Review(
        pr_url=pr_url,
        pr_title=pr_title,
        risk_score=risk_score,
        issues_json=issues_json
    )

    # 3. Put the new review into the database notebook
    session.add(review)

    # 4. Save (commit) the changes permanently into the database
    session.commit()

    # 5. Grab the newly created unique ID number (e.g. 1) so we can return it
    review_id = review.id

    # 6. Always close the conversation to free up computer memory
    session.close()

    # 7. Return the ID number back to whoever asked to save it
    return review_id


# Function: Get the list of all past reviews
# Used to display the "Recent Reviews History" section on the frontend web page.
def get_all_reviews():
    # 1. Open a database conversation
    session = SessionLocal()

    # 2. Fetch the latest 25 reviews, sorted with newest on top (descending order)
    reviews = session.query(Review).order_by(Review.created_at.desc()).limit(25).all()

    # 3. Close the conversation
    session.close()

    # 4. Return the list of past reviews
    return reviews


# Function: Get a single review by its specific ID number
# If the user clicks on review #3 in their history list, this finds and returns review #3.
def get_review_by_id(review_id: int):
    # 1. Open a database conversation
    session = SessionLocal()

    # 2. Search for the review where the ID matches review_id
    review = session.query(Review).filter(Review.id == review_id).first()

    # 3. Close the conversation
    session.close()

    # 4. Return the found review (or None if not found)
    return review
