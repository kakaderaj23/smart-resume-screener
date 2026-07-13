"""
ResumeRepository for managing ResumeRecord persistence operations.
"""

import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume_record import ResumeRecord

logger = logging.getLogger("smart-resume-screener.repositories.resume")


class ResumeRepository:
    """
    Repository encapsulating database query and storage interactions for ResumeRecord.
    Enforces architectural separation of concerns and avoids web framework dependencies.
    """

    def save(self, db: Session, record: ResumeRecord) -> ResumeRecord:
        """
        Persist a new ResumeRecord to the database.
        """
        try:
            db.add(record)
            db.commit()
            db.refresh(record)
            logger.info(f"Persisted ResumeRecord ID {record.id} with status {record.processing_status}")
            return record
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist ResumeRecord: {e}", exc_info=True)
            raise e

    def get(self, db: Session, record_id: int) -> Optional[ResumeRecord]:
        """
        Retrieve a ResumeRecord by its primary key ID.
        """
        return db.get(ResumeRecord, record_id)

    def list(self, db: Session, skip: int = 0, limit: int = 100) -> List[ResumeRecord]:
        """
        List ResumeRecords with support for pagination offset and limit.
        """
        statement = select(ResumeRecord).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def update(self, db: Session, record: ResumeRecord) -> ResumeRecord:
        """
        Update an existing ResumeRecord in the database.
        """
        try:
            db.commit()
            db.refresh(record)
            logger.info(f"Updated ResumeRecord ID {record.id} with status {record.processing_status}")
            return record
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update ResumeRecord ID {record.id}: {e}", exc_info=True)
            raise e

    def delete(self, db: Session, record_id: int) -> bool:
        """
        Delete a ResumeRecord by its primary key ID.
        Returns True if deletion was successful, False if the record was not found.
        """
        record = self.get(db, record_id)
        if not record:
            logger.warning(f"ResumeRecord ID {record_id} not found for deletion.")
            return False

        try:
            db.delete(record)
            db.commit()
            logger.info(f"Deleted ResumeRecord ID {record_id} from database.")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete ResumeRecord ID {record_id}: {e}", exc_info=True)
            raise e
