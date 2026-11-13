"""ORM 模型聚合导出（Base 用于 create_all）。"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from src.models.user import User  # noqa: E402
from src.models.audit import AuditLog  # noqa: E402
from src.models.policy import Policy  # noqa: E402
from src.models.rule import Rule  # noqa: E402
from src.models.company import Company  # noqa: E402
from src.models.match_run import MatchRun  # noqa: E402
from src.models.match import Match  # noqa: E402

__all__ = ["Base", "User", "AuditLog", "Policy", "Rule", "Company", "MatchRun", "Match"]
