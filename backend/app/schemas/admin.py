from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


SupportTier = Literal["L1 Support", "L2 Senior Support", "L3 Support Manager"]
Category = Literal["UPI", "ATM", "Cards", "Account", "KYC"]


class RoutingRule(BaseModel):
    category: Category
    support_tier: SupportTier
    priority: Literal["Low", "Normal", "High", "Urgent"]


class AdminConfigUpdate(BaseModel):
    routing_rules: list[RoutingRule] = Field(min_length=5, max_length=5)
    sla_targets: dict[SupportTier, int]

    @model_validator(mode="after")
    def validate_settings(self):
        expected_categories = {"UPI", "ATM", "Cards", "Account", "KYC"}
        actual_categories = {rule.category for rule in self.routing_rules}
        if actual_categories != expected_categories:
            raise ValueError("Routing rules must define each banking category exactly once")

        if len(self.sla_targets) != 3 or any(
            not 1 <= hours <= 720 for hours in self.sla_targets.values()
        ):
            raise ValueError("Provide SLA targets from 1 to 720 hours for each support tier")
        return self


class AdminOverview(BaseModel):
    account_count: int
    role_counts: dict[str, int]
    ticket_metrics: Optional[dict[str, Any]] = None
    message: str
