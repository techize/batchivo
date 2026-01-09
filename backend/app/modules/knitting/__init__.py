"""Knitting/Crochet feature modules."""

from typing import List

from app.modules.base import BaseModule
from app.modules.knitting.needle import NeedleModule
from app.modules.knitting.pattern import PatternModule
from app.modules.knitting.project import ProjectModule
from app.modules.knitting.yarn import YarnModule


def get_modules() -> List[BaseModule]:
    """
    Get all knitting modules.

    Returns:
        List of module instances
    """
    return [
        YarnModule(),
        NeedleModule(),
        PatternModule(),
        ProjectModule(),
    ]


__all__ = [
    "YarnModule",
    "NeedleModule",
    "PatternModule",
    "ProjectModule",
    "get_modules",
]
