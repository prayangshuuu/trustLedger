"""Data deletion service implementing the GDPR/Privacy 'Right to be Forgotten'.

Permanently purges all user data across all tables with cascading deletions.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.storage import delete_user_documents


def delete_user_data(session: Session, user_id: str) -> bool:
    """Delete all records associated with a user, cascading across all child tables.

    Args:
        session: Active SQLAlchemy database session.
        user_id: Unique identifier of the user to delete.

    Returns:
        bool: True if the user existed and was deleted, False otherwise.
    """
    stmt = select(User).where(User.id == user_id)
    user = session.scalars(stmt).first()
    if user is None:
        return False

    session.delete(user)
    session.commit()
    # Encrypted document images live in object storage, outside the DB cascade
    delete_user_documents(user_id)
    return True
