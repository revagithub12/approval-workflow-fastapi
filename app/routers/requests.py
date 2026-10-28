from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ApprovalLog, ApprovalRequest, Role, Stage, Status, User
from ..schemas import Decision, RequestCreate, RequestOut

router = APIRouter(prefix="/requests", tags=["requests"])


def _can_view(user: User, req: ApprovalRequest) -> bool:
    if user.role == Role.ADMIN or req.requester_id == user.id:
        return True
    return user.role == Role.MANAGER and req.stage == Stage.MANAGER


def _get_request_or_404(db: Session, request_id: int) -> ApprovalRequest:
    req = db.get(ApprovalRequest, request_id)
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return req


@router.post("", response_model=RequestOut, status_code=201)
def create_request(data: RequestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    req = ApprovalRequest(**data.model_dump(), requester_id=user.id)
    req.logs.append(ApprovalLog(actor_id=user.id, action="created"))
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=list[RequestOut])
def list_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(ApprovalRequest).order_by(ApprovalRequest.id.desc())
    if user.role == Role.MANAGER:
        query = query.where(
            or_(
                ApprovalRequest.requester_id == user.id,
                (ApprovalRequest.stage == Stage.MANAGER) & (ApprovalRequest.status == Status.PENDING),
            )
        )
    elif user.role == Role.EMPLOYEE:
        query = query.where(ApprovalRequest.requester_id == user.id)
    return db.scalars(query).all()


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    req = _get_request_or_404(db, request_id)
    if not _can_view(user, req):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot view this request")
    return req


def _check_can_decide(req: ApprovalRequest, user: User) -> None:
    if req.status != Status.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request already {req.status.value}")
    if req.requester_id == user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot approve your own request")
    required = Role.MANAGER if req.stage == Stage.MANAGER else Role.ADMIN
    if user.role != required:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"This stage needs a {required.value}")


@router.post("/{request_id}/approve", response_model=RequestOut)
def approve(
    request_id: int,
    data: Decision = Decision(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = _get_request_or_404(db, request_id)
    _check_can_decide(req, user)
    if req.stage == Stage.MANAGER:
        req.stage = Stage.ADMIN  # moves to the next approval stage
    else:
        req.stage = Stage.DONE
        req.status = Status.APPROVED
    req.logs.append(ApprovalLog(actor_id=user.id, action="approved", comment=data.comment))
    db.commit()
    db.refresh(req)
    return req


@router.post("/{request_id}/reject", response_model=RequestOut)
def reject(
    request_id: int,
    data: Decision = Decision(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = _get_request_or_404(db, request_id)
    _check_can_decide(req, user)
    req.stage = Stage.DONE
    req.status = Status.REJECTED
    req.logs.append(ApprovalLog(actor_id=user.id, action="rejected", comment=data.comment))
    db.commit()
    db.refresh(req)
    return req
