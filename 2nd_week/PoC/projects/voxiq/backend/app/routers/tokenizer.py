from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import models
from ..ml import tokenizer_explorer
from ..security import get_current_user

router = APIRouter(prefix="/api/tokenizer", tags=["tokenizer"])


class ExploreRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    layer: int | None = Field(None, ge=0, le=11)


@router.post("/explore")
def explore(payload: ExploreRequest, user: models.User = Depends(get_current_user)):
    tokenization = tokenizer_explorer.tokenize(payload.text)
    attention = tokenizer_explorer.attention_weights(payload.text, layer=payload.layer)
    return {
        "tokens": tokenization["tokens"],
        "token_ids": tokenization["ids"],
        "token_count": tokenization["count"],
        "attention": attention["attention"],
        "attention_tokens": attention["tokens"],
        "layer": attention["layer"],
        "num_layers": attention["num_layers"],
        "truncated": attention["truncated"],
    }
