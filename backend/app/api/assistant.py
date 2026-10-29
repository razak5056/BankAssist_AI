from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.agents.banking_agent import process_customer_query
from backend.app.core.auth import require_role
from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.assistant import AgentAnswer, AgentQuestion

router = APIRouter(prefix="/assistant", tags=["AI Banking Agent"])


@router.post("/ask", response_model=AgentAnswer)
def ask_banking_agent(
    payload: AgentQuestion,
    current_user: User = Depends(require_role("Customer")),
    db: Session = Depends(get_db),
):
    """
    Customer AI Banking Agent:
    - Understands query and categorizes it
    - Consults banking knowledge base
    - Answers directly OR automatically creates a dispute ticket and routes to L1 support
    """
    return process_customer_query(
        db=db,
        customer=current_user,
        question=payload.question.strip(),
    )
