from abc import ABC, abstractmethod
from typing import Tuple
from app.config import CustomerPolicy

class RateLimiter(ABC):
    @abstractmethod
    def check(self, policy: CustomerPolicy) -> Tuple[bool, int, int, int]:
        """
        Check if the request should be allowed.
        
        Args:
            policy: The resolved policy object for the customer.
            
        Returns:
            Tuple of (allowed: bool, limit: int, remaining: int, retry_after: int)
        """
        pass
