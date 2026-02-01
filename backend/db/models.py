from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    github_id = Column(String, unique=True)
    github_token = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    repos = relationship("Repository", back_populates="user")

class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    repo_name = Column(String)
    repo_url = Column(String)
    default_branch = Column(String, default="main")
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="repos")
    scans = relationship("Scan", back_populates="repository")

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"))
    status = Column(String, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    total_files = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    
    repository = relationship("Repository", back_populates="scans")
    vulnerabilities = relationship("Vulnerability", back_populates="scan")
    pull_requests = relationship("PullRequest", back_populates="scan")

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    type = Column(String)  # secrets, sql_injection, dependency
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
    plan_id = Column(String, nullable=False)  # free, pro, team
    stripe_subscription_id = Column(String, nullable=True)
    status = Column(String, default="active")  # active, canceled, past_due
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")

# Update User model to include subscription relationship
User.subscriptions = relationship("Subscription", back_populates="user")