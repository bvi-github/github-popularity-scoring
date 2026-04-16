from github_popularity_scoring.domain.enums_ import ScoringStrategyName
from github_popularity_scoring.presenter.dependencies import SCORING_STRATEGIES

def test_all_scoring_strategy_names_are_registered()->None:
    assert set(SCORING_STRATEGIES) == set(ScoringStrategyName)
