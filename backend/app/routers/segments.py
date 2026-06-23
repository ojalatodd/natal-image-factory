from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Asset, Project, Segment, User
from app.schemas import SegmentOut, SegmentSwap

router = APIRouter(tags=["segments"])


@router.get("/projects/{project_id}/segments", response_model=list[SegmentOut])
def list_segments(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project.segments


@router.post("/segments/{segment_id}/swap", response_model=SegmentOut)
def swap_segment(
    segment_id: int,
    body: SegmentSwap,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    seg = db.get(Segment, segment_id)
    if not seg or seg.project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    if body.asset_id is not None:
        asset = db.get(Asset, body.asset_id)
        if not asset or asset.segment_id != seg.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid asset")
        for a in seg.assets:
            a.is_chosen = a.id == asset.id
        seg.chosen_asset_id = asset.id
        seg.chosen_media_type = asset.media_type

    if body.media_type is not None:
        seg.chosen_media_type = body.media_type
        # Phase 3: re-run search/rank for this segment with the new media type.

    db.commit()
    db.refresh(seg)
    return seg
