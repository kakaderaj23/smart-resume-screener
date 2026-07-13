"""
Recommendation Engine containing deterministic business logic and enums.
"""

from enum import Enum
import logging

logger = logging.getLogger("smart-resume-screener.services.recommendation_engine")


class Recommendation(str, Enum):
    """
    Strongly typed recommendation levels for candidates based on match evaluation.
    """
    STRONG_HIRE = "STRONG_HIRE"
    SHORTLIST = "SHORTLIST"
    CONSIDER = "CONSIDER"
    REJECT = "REJECT"


class RecommendationEngine:
    """
    Service responsible for applying deterministic business rules to generate
    hiring recommendations from semantic scores. Contains zero AI logic.
    """

    def generate_recommendation(self, score: int) -> Recommendation:
        """
        Map a semantic score (1-10) to a recommendation level using strict business rules.

        Business Rules:
        - 9-10  -> STRONG_HIRE
        - 7-8   -> SHORTLIST
        - 5-6   -> CONSIDER
        - 1-4   -> REJECT

        Args:
            score (int): Semantic score from LLM assessment.

        Returns:
            Recommendation: The mapped hiring recommendation enum.

        Raises:
            ValueError: If the score is out of the valid 1-10 range.
        """
        if not (1 <= score <= 10):
            logger.error(f"Cannot generate recommendation: score {score} is out of bounds [1-10].")
            raise ValueError(f"Semantic score {score} must be between 1 and 10.")

        if score >= 9:
            recommendation = Recommendation.STRONG_HIRE
        elif score >= 7:
            recommendation = Recommendation.SHORTLIST
        elif score >= 5:
            recommendation = Recommendation.CONSIDER
        else:
            recommendation = Recommendation.REJECT

        logger.info(f"Generated recommendation '{recommendation}' for semantic score {score}.")
        return recommendation
