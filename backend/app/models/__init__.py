"""
__init__.py for models module
"""
from app.models.user import User
from app.models.typhoon import Typhoon
from app.models.image import TyphoonImage
from app.models.video import VideoAnalysisResult
from app.models.knowledge_graph import (
    NodeType,
    RelationshipType,
    GraphNode,
    GraphLink,
    GraphData,
    NODE_TYPE_CONFIG,
    RELATIONSHIP_TYPE_CONFIG,
    IntensityLevel,
    INTENSITY_LEVELS,
    get_node_id,
    detect_node_type,
    validate_relationship,
)

__all__ = [
    "User",
    "Typhoon",
    "TyphoonImage",
    "VideoAnalysisResult",
    "NodeType",
    "RelationshipType",
    "GraphNode",
    "GraphLink",
    "GraphData",
    "NODE_TYPE_CONFIG",
    "RELATIONSHIP_TYPE_CONFIG",
    "IntensityLevel",
    "INTENSITY_LEVELS",
    "get_node_id",
    "detect_node_type",
    "validate_relationship",
]
