"""Request tracking and cancellation management for Chat-O-Llama."""

import uuid
import time
import logging
import threading
from typing import Dict, Optional, Set, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    """Status of a tracked request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class RequestInfo:
    """Information about a tracked request."""
    request_id: str
    conversation_id: str
    model: str
    message: str
    backend_type: str
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    user_session: Optional[str] = None
    cancellation_token: Optional[threading.Event] = field(default_factory=threading.Event)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the cancellation token if not provided."""
        if self.cancellation_token is None:
            self.cancellation_token = threading.Event()
    
    @property
    def is_active(self) -> bool:
        """Check if the request is still active (not completed, cancelled, or failed)."""
        return self.status in [RequestStatus.PENDING, RequestStatus.PROCESSING]
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get the duration of the request in seconds."""
        if self.started_at is None:
            return None
        
        end_time = self.completed_at or self.cancelled_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def cancel(self):
        """Cancel the request by setting the cancellation token."""
        if self.is_active:
            self.cancellation_token.set()
            self.cancelled_at = datetime.now()
            self.status = RequestStatus.CANCELLED
            logger.info(f"Request {self.request_id} cancelled")
    
    def is_cancelled(self) -> bool:
        """Check if the request has been cancelled."""
        return self.cancellation_token.is_set() or self.status == RequestStatus.CANCELLED


class RequestManager:
    """Manages active requests and their cancellation."""
    
    def __init__(self):
        self._requests: Dict[str, RequestInfo] = {}
        self._lock = threading.RLock()
        self._cleanup_interval = 300  # 5 minutes
        self._max_request_age = 3600  # 1 hour
        self._cleanup_thread = None
        self._running = False
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start the background cleanup thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
            logger.info("Request cleanup thread started")
    
    def _cleanup_loop(self):
        """Background cleanup loop to remove old requests."""
        while self._running:
            try:
                self._cleanup_old_requests()
                time.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _cleanup_old_requests(self):
        """Remove old completed/cancelled requests."""
        with self._lock:
            current_time = datetime.now()
            to_remove = []
            
            for request_id, request_info in self._requests.items():
                if not request_info.is_active:
                    # Remove completed/cancelled requests after max age
                    age = (current_time - request_info.created_at).total_seconds()
                    if age > self._max_request_age:
                        to_remove.append(request_id)
                else:
                    # Cancel very old active requests (potential stuck requests)
                    age = (current_time - request_info.created_at).total_seconds()
                    if age > self._max_request_age * 2:  # 2 hours for active requests
                        logger.warning(f"Force cancelling stuck request {request_id}")
                        request_info.cancel()
                        to_remove.append(request_id)
            
            for request_id in to_remove:
                del self._requests[request_id]
                logger.debug(f"Cleaned up request {request_id}")
    
    def generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return str(uuid.uuid4())
    
    def create_request(
        self,
        conversation_id: str,
        model: str,
        message: str,
        backend_type: str,
        user_session: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new request and return its ID.
        
        Args:
            conversation_id: ID of the conversation
            model: Model name to use
            message: User message
            backend_type: Backend type (ollama, llamacpp, etc.)
            user_session: Optional user session ID
            metadata: Optional additional metadata
            
        Returns:
            str: Generated request ID
        """
        request_id = self.generate_request_id()
        
        with self._lock:
            request_info = RequestInfo(
                request_id=request_id,
                conversation_id=conversation_id,
                model=model,
                message=message,
                backend_type=backend_type,
                user_session=user_session,
                metadata=metadata or {}
            )
            
            self._requests[request_id] = request_info
            logger.info(f"Created request {request_id} for conversation {conversation_id}")
            
        return request_id
    
    def get_request(self, request_id: str) -> Optional[RequestInfo]:
        """Get request information by ID."""
        with self._lock:
            return self._requests.get(request_id)
    
    def update_request_status(
        self,
        request_id: str,
        status: RequestStatus,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the status of a request.
        
        Args:
            request_id: Request ID to update
            status: New status
            metadata: Optional metadata to merge
            
        Returns:
            bool: True if update was successful
        """
        with self._lock:
            request_info = self._requests.get(request_id)
            if request_info is None:
                logger.warning(f"Request {request_id} not found for status update")
                return False
            
            old_status = request_info.status
            request_info.status = status
            
            # Update timestamps
            now = datetime.now()
            if status == RequestStatus.PROCESSING and request_info.started_at is None:
                request_info.started_at = now
            elif status in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
                request_info.completed_at = now
            elif status == RequestStatus.CANCELLED:
                request_info.cancelled_at = now
            
            # Merge metadata
            if metadata:
                request_info.metadata.update(metadata)
            
            logger.info(f"Request {request_id} status updated: {old_status} -> {status}")
            return True
    
    def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a request by ID.
        
        Args:
            request_id: Request ID to cancel
            
        Returns:
            bool: True if cancellation was successful
        """
        with self._lock:
            request_info = self._requests.get(request_id)
            if request_info is None:
                logger.warning(f"Request {request_id} not found for cancellation")
                return False
            
            if not request_info.is_active:
                logger.info(f"Request {request_id} is not active (status: {request_info.status})")
                return False
            
            request_info.cancel()
            return True
    
    def cancel_conversation_requests(self, conversation_id: str) -> int:
        """
        Cancel all active requests for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            int: Number of requests cancelled
        """
        cancelled_count = 0
        with self._lock:
            for request_info in self._requests.values():
                if (request_info.conversation_id == conversation_id and 
                    request_info.is_active):
                    request_info.cancel()
                    cancelled_count += 1
        
        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} requests for conversation {conversation_id}")
        
        return cancelled_count
    
    def get_active_requests(self) -> List[RequestInfo]:
        """Get all active requests."""
        with self._lock:
            return [req for req in self._requests.values() if req.is_active]
    
    def get_conversation_requests(self, conversation_id: str) -> List[RequestInfo]:
        """Get all requests for a conversation."""
        with self._lock:
            return [req for req in self._requests.values() 
                   if req.conversation_id == conversation_id]
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Get request statistics."""
        with self._lock:
            total_requests = len(self._requests)
            active_requests = sum(1 for req in self._requests.values() if req.is_active)
            
            status_counts = {}
            for status in RequestStatus:
                status_counts[status.value] = sum(
                    1 for req in self._requests.values() if req.status == status
                )
            
            backend_counts = {}
            for req in self._requests.values():
                backend_counts[req.backend_type] = backend_counts.get(req.backend_type, 0) + 1
            
            return {
                'total_requests': total_requests,
                'active_requests': active_requests,
                'status_counts': status_counts,
                'backend_counts': backend_counts,
                'cleanup_interval': self._cleanup_interval,
                'max_request_age': self._max_request_age
            }
    
    def cleanup_all(self):
        """Clean up all requests and stop the cleanup thread."""
        self._running = False
        with self._lock:
            # Cancel all active requests
            for request_info in self._requests.values():
                if request_info.is_active:
                    request_info.cancel()
            
            # Clear all requests
            self._requests.clear()
        
        logger.info("Request manager cleaned up")
    
    def __del__(self):
        """Cleanup when the manager is destroyed."""
        self.cleanup_all()


# Global request manager instance
_request_manager = None
_manager_lock = threading.Lock()


def get_request_manager() -> RequestManager:
    """Get the global request manager instance."""
    global _request_manager
    with _manager_lock:
        if _request_manager is None:
            _request_manager = RequestManager()
        return _request_manager


def reset_request_manager():
    """Reset the global request manager (mainly for testing)."""
    global _request_manager
    with _manager_lock:
        if _request_manager is not None:
            _request_manager.cleanup_all()
        _request_manager = None