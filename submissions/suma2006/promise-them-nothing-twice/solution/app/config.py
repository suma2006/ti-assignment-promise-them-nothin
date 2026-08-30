import os
import sys
import yaml
from pydantic import BaseModel, model_validator
from typing import Optional, Dict, List

class OverrideConfig(BaseModel):
    override_id: str
    customer_id: str
    override_rpm: int
    window_start_utc: str
    window_end_utc: str
    expires_at_timestamp: int
    approved_by: str
    reason: str
    ticket_ref: str

class CustomerRecord(BaseModel):
    tier: str
    rpm: Optional[int] = None

class PolicyConfig(BaseModel):
    tiers: Dict[str, int]
    customers: Dict[str, CustomerRecord]
    overrides: List[OverrideConfig]

    @model_validator(mode='after')
    def validate_customer_rpms(self):
        for cid, record in self.customers.items():
            if record.rpm is None and record.tier not in self.tiers:
                raise ValueError(f"Customer '{cid}' has tier '{record.tier}' with no default RPM, and no explicit rpm is set.")
        return self

def load_policies(path: str = None) -> PolicyConfig:
    if path is None:
        path = os.getenv("CONFIG_PATH", "config/policies.yaml")
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return PolicyConfig(**data)
    except Exception as e:
        print(f"Failed to load or validate policy config: {e}", file=sys.stderr)
        sys.exit(1)

policy_config = load_policies()

class CustomerPolicy(BaseModel):
    customer_id: str
    base_rpm: int
    override_id: Optional[str] = None
    override_rpm: Optional[int] = None
    window_start_utc: Optional[str] = None
    window_end_utc: Optional[str] = None
    expires_at_timestamp: Optional[int] = None

def get_customer_policy(customer_id: str) -> Optional[CustomerPolicy]:
    customer_record = policy_config.customers.get(customer_id)
    if not customer_record:
        return None
    
    if customer_record.rpm is not None:
        base_rpm = customer_record.rpm
    else:
        base_rpm = policy_config.tiers.get(customer_record.tier, 0)
        
    policy = CustomerPolicy(customer_id=customer_id, base_rpm=base_rpm)
    
    for override in policy_config.overrides:
        if override.customer_id == customer_id:
            policy.override_id = override.override_id
            policy.override_rpm = override.override_rpm
            policy.window_start_utc = override.window_start_utc
            policy.window_end_utc = override.window_end_utc
            policy.expires_at_timestamp = override.expires_at_timestamp
            break
            
    return policy
