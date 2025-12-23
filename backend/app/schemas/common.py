"""
Common Schemas - Shared across all endpoints.

Pagination, sorting, and response wrappers.
"""

from pydantic import BaseModel, Field
from typing import List, TypeVar, Generic, Optional, Any
from datetime import datetime
from enum import Enum


# ==================== Pagination ====================

class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size


class PaginationMeta(BaseModel):
    """Pagination metadata in response."""
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    
    @classmethod
    def create(cls, page: int, page_size: int, total_items: int) -> "PaginationMeta":
        """Create pagination metadata from counts."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


# Generic type for paginated items
T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    data: List[Any]  # Will be typed T when used
    pagination: PaginationMeta
    
    class Config:
        arbitrary_types_allowed = True


# ==================== Sorting ====================

class SortOrder(str, Enum):
    """Sort order direction."""
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    """Common sorting parameters."""
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.ASC, description="Sort direction")


# ==================== Cache Control ====================

class CacheControl(BaseModel):
    """Cache control metadata in response."""
    cached: bool = Field(False, description="Whether response was from cache")
    cache_key: Optional[str] = Field(None, description="Cache key (for debugging)")
    expires_at: Optional[datetime] = Field(None, description="When cache expires")
    ttl_seconds: Optional[int] = Field(None, description="Time to live in seconds")


class CachedResponse(BaseModel, Generic[T]):
    """Response wrapper with cache metadata."""
    data: Any  # Will be typed T when used
    cache: CacheControl
    
    class Config:
        arbitrary_types_allowed = True


# ==================== Error Responses ====================

class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    details: Optional[dict] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    errors: List[ErrorDetail]
    request_id: Optional[str] = None


# ==================== Success Response ====================

class SuccessResponse(BaseModel):
    """Standard success response wrapper."""
    success: bool = True
    data: Any
    message: Optional[str] = None


# ==================== Search Specific ====================

class SearchMeta(BaseModel):
    """Metadata for search responses."""
    search_id: str = Field(..., description="Unique search identifier")
    query_time_ms: int = Field(..., description="Query execution time in milliseconds")
    filters_applied: dict = Field(default_factory=dict, description="Applied filters")
    price_range: Optional[dict] = Field(None, description="Min/max prices in results")


class PaginatedSearchResponse(BaseModel, Generic[T]):
    """Paginated search response with metadata."""
    data: List[Any]  # Search results
    pagination: PaginationMeta
    search: SearchMeta
    cache: Optional[CacheControl] = None
    
    class Config:
        arbitrary_types_allowed = True
