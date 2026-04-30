from fastapi import APIRouter
from app.api import config, patients, merge, stats

router = APIRouter()
router.include_router(config.router)
router.include_router(patients.router)
router.include_router(merge.router)
router.include_router(stats.router)

__all__ = ['router']