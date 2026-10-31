import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

def generate_uuid():
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc)

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    users = relationship("Membership", back_populates="organization")
    documents = relationship("Document", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    organizations = relationship("Membership", back_populates="user")
    queries = relationship("Query", back_populates="user")

class Membership(Base):
    __tablename__ = "memberships"
    
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(String, nullable=False, default="member") # admin, member
    
    organization = relationship("Organization", back_populates="users")
    user = relationship("User", back_populates="organizations")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="processing") # processing, ready, failed
    error_message = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)
    metadata_json = Column(JSONB, nullable=True) # avoiding keyword conflict
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    organization = relationship("Organization", back_populates="documents")
    uploader = relationship("User")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    content_hash = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    source_type = Column(String, nullable=True)
    
    document = relationship("Document", back_populates="chunks")

class Query(Base):
    __tablename__ = "queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    user = relationship("User", back_populates="queries")
    citations = relationship("Citation", back_populates="query", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="query", cascade="all, delete-orphan")

class Citation(Base):
    __tablename__ = "citations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id"), nullable=False)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    chunk_id = Column(String, nullable=False)
    relevance_score = Column(Float, nullable=True)
    
    query = relationship("Query", back_populates="citations")

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id"), nullable=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_query = Column(Text, nullable=False)
    classification = Column(String, nullable=True)
    status = Column(String, nullable=False, default="processing")
    iterations = Column(Integer, nullable=False, default=0)
    total_latency_ms = Column(Float, nullable=True)
    workflow_trace = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    
    query = relationship("Query", back_populates="agent_runs")
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan")

class AgentStep(Base):
    __tablename__ = "agent_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=False)
    step_type = Column(String, nullable=False)
    latency_ms = Column(Float, nullable=True)
    payload = Column(JSONB, nullable=True)
    
    run = relationship("AgentRun", back_populates="steps")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
