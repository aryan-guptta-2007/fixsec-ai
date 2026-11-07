from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    github_id = Column(String, unique=True)
    github_token = Column(String)  # Fernet-encrypted, see core/security.py
    created_at = Column(DateTime, default=datetime.utcnow)

    repos = relationship("Repository", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    scheduled_scans = relationship("ScheduledScan", back_populates="user")


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        Index("ix_repositories_user_repo", "user_id", "repo_name", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    repo_name = Column(String)  # owner/repo
    repo_url = Column(String)
    default_branch = Column(String, default="main")
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="repos")
    scans = relationship("Scan", back_populates="repository")


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (Index("ix_scans_repo_started", "repo_id", "started_at"),)

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"))
    status = Column(String, default="pending")  # pending, running, completed, failed
    trigger = Column(String, default="manual")  # manual, scheduled
    branch = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    total_files = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    security_score = Column(Float, nullable=True)
    grade = Column(String, nullable=True)
    result_json = Column(Text, nullable=True)  # full API payload, secrets masked
    error_message = Column(Text, nullable=True)

    repository = relationship("Repository", back_populates="scans")
    vulnerabilities = relationship("Vulnerability", back_populates="scan")
    pull_requests = relationship("PullRequest", back_populates="scan")


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    type = Column(String)
    severity = Column(String)  # LOW, MEDIUM, HIGH, CRITICAL
    file_path = Column(String)
    line_number = Column(Integer, nullable=True)
    message = Column(Text)
    fixable = Column(Boolean, default=False)
    confidence_score = Column(Integer, default=0)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="vulnerabilities")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    pr_url = Column(String)
    branch_name = Column(String)
    status = Column(String, default="created")  # created, merged, closed
    fixes_applied = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="pull_requests")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(String, nullable=False)  # starter, pro, team
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_customer_id = Column(String, nullable=True)
    status = Column(String, default="active")  # active, trialing, past_due, canceled
    cancel_at_period_end = Column(Boolean, default=False)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")


class ScheduledScan(Base):
    __tablename__ = "scheduled_scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    repo_name = Column(String, nullable=False)
    frequency = Column(String, nullable=False)  # daily, weekly, monthly
    notification_channels = Column(Text, nullable=False, default="[]")  # JSON
    enabled = Column(Boolean, default=True)
    next_run = Column(DateTime, nullable=False, index=True)
    last_run = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    last_result = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="scheduled_scans")
