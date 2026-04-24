from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, RootModel
from .mineru_content import MinerUElement


class AnnotatedMinerUElement(BaseModel):
    """A MinerU element with an assigned semantic tag from a template."""
    semantic_tag: str
    element: MinerUElement
    model_config = {"extra": "allow"}


class AnnotatedMinerUContentList(RootModel):
    """The interface data format for downstream template engines."""
    root: List[AnnotatedMinerUElement]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)
