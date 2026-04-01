"""Pydantic models for the Requirements Management System."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    REQUIREMENT = "requirement"
    SPECIFICATION = "specification"
    TEST_CASE = "test_case"
    DESIGN = "design"
    RISK = "risk"


class LinkType(str, Enum):
    DERIVES_FROM = "derives_from"
    SATISFIES = "satisfies"
    VERIFIED_BY = "verified_by"
    TRACES_TO = "traces_to"
    MITIGATED_BY = "mitigated_by"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NodeStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    SUSPECT = "suspect"
    DELETED = "deleted"


DEFAULT_SUBSYSTEMS = ["SS", "GCS", "DLS", "AVS"]


class RequirementNode(BaseModel):
    id: str
    title: str
    content: str
    node_type: NodeType = NodeType.REQUIREMENT
    priority: Priority = Priority.MEDIUM
    status: NodeStatus = NodeStatus.DRAFT
    author: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    subsystem: str = "SS"


class RequirementLink(BaseModel):
    source_id: str
    target_id: str
    link_type: LinkType = LinkType.TRACES_TO
    is_suspect: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    description: str = ""


class CreateNodeRequest(BaseModel):
    id: Optional[str] = None
    title: str
    content: str
    node_type: NodeType = NodeType.REQUIREMENT
    priority: Priority = Priority.MEDIUM
    author: str = ""
    tags: list[str] = Field(default_factory=list)
    subsystem: str = "SS"


class UpdateNodeRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    node_type: Optional[NodeType] = None
    priority: Optional[Priority] = None
    status: Optional[NodeStatus] = None
    tags: Optional[list[str]] = None
    subsystem: Optional[str] = None


class CreateLinkRequest(BaseModel):
    source_id: str
    target_id: str
    link_type: LinkType = LinkType.TRACES_TO
    description: str = ""


class SubsystemRequest(BaseModel):
    name: str


class BaselineRequest(BaseModel):
    name: str
    description: str = ""


class BaselineInfo(BaseModel):
    name: str
    description: str
    created_at: datetime
    node_count: int
    link_count: int
