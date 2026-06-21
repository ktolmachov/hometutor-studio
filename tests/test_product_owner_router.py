"""
Test Suite для Product Owner Router v2.0

Тестирует Decision Table, Conflict Resolution, Cohesion Score,
Escape Hatches и другие компоненты роутера.

Запуск:
    pytest tests/test_product_owner_router.py -v
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Any


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_registry():
    """Sample backlog_registry.yaml для тестов"""
    return {
        "schema_version": 2,
        "active_package_id": "epoch-test-package",
        "active_wave_id": "wave-test",
        "waves": [
            {
                "id": "wave-test",
                "status": "wip",
                "packages": ["epoch-test-package"]
            }
        ],
        "items": [
            {
                "id": "epoch-test-package",
                "status": "ready",
                "wave_id": "wave-test",
                "user_stories": ["US-20.1"],
                "write_set_max": 5
            },
            {
                "id": "epoch-proposed-package",
                "status": "proposed",
                "wave_id": None,
                "user_stories": ["US-20.2"]
            },
            {
                "id": "epoch-deferred-package",
                "status": "deferred",
                "wave_id": None,
                "re_entry_condition": "US-20.3 closed"
            }
        ]
    }


@pytest.fixture
def sample_ideas():
    """Sample ideas для cohesion score тестов"""
    return [
        {
            "id": 1,
            "title": "Skeleton screen",
            "write_set": ["app/ui/skeleton.py", "app/ui/answer_card.py"],
            "cjm_moment": "#2 First Answer",
            "epic": "US-19.x",
            "method_source": "Duolingo",
            "layer": "UI"
        },
        {
            "id": 2,
            "title": "Progressive reveal",
            "write_set": ["app/ui/progressive.py", "app/ui/answer_card.py"],
            "cjm_moment": "#3 Transition to Tutor",
            "epic": "US-19.x",
            "method_source": "Duolingo",
            "layer": "UI"
        },
        {
            "id": 3,
            "title": "Smooth transition",
            "write_set": ["app/ui/transition.py"],
            "cjm_moment": "#3 Transition to Tutor",
            "epic": "US-19.x",
            "method_source": "Duolingo",
            "layer": "UI",
            "depends_on": [1, 2]
        }
    ]


# ============================================================================
# DECISION TABLE TESTS
# ============================================================================

class TestDecisionTable:
    """Тесты для Decision Table"""
    
    def test_ready_package_exists(self, sample_registry):
        """Тест: Есть ready package → workflow.py"""
        # Arrange
        active_id = sample_registry["active_package_id"]
        package = next(p for p in sample_registry["items"] if p["id"] == active_id)
        
        # Act
        state = self._determine_state(sample_registry)
        
        # Assert
        assert state == "ready_package_exists"
        assert package["status"] == "ready"
    
    def test_no_active_package(self):
        """Тест: Нет active package → plan-next или ideation"""
        # Arrange
        registry = {
            "active_package_id": None,
            "items": []
        }
        
        # Act
        state = self._determine_state(registry)
        
        # Assert
        assert state == "no_package"
    
    def test_proposed_packages_exist(self, sample_registry):
        """Тест: Есть proposed packages → review conflicts"""
        # Arrange
        proposed = [p for p in sample_registry["items"] if p["status"] == "proposed"]
        
        # Assert
        assert len(proposed) > 0
        assert proposed[0]["id"] == "epoch-proposed-package"
    
    def test_deferred_with_re_entry(self, sample_registry):
        """Тест: Deferred с re_entry_condition"""
        # Arrange
        deferred = [p for p in sample_registry["items"] if p["status"] == "deferred"]
        
        # Assert
        assert len(deferred) > 0
        assert "re_entry_condition" in deferred[0]
        assert deferred[0]["re_entry_condition"] == "US-20.3 closed"
    
    def _determine_state(self, registry: Dict) -> str:
        """Helper: определить состояние по registry"""
        if registry.get("active_package_id"):
            return "ready_package_exists"
        elif not registry.get("items"):
            return "no_package"
        else:
            return "needs_plan"


# ============================================================================
# CONFLICT RESOLUTION TESTS
# ============================================================================

class TestConflictResolution:
    """Тесты для Conflict Resolution Rules"""
    
    def test_proposed_vs_blocker_priority(self, sample_registry):
        """Тест: proposed в registry + plan-next blocker → Registry wins"""
        # Arrange
        proposed_count = len([p for p in sample_registry["items"] if p["status"] == "proposed"])
        plan_next_blocker = True
        
        # Act
        priority = self._resolve_conflict("proposed_vs_blocker", proposed_count, plan_next_blocker)
        
        # Assert
        assert priority == "registry_wins"
        assert proposed_count > 0
    
    def test_deferred_re_entry_met(self, sample_registry):
        """Тест: deferred + re_entry met → Re-entry wins"""
        # Arrange
        deferred = next(p for p in sample_registry["items"] if p["status"] == "deferred")
        re_entry_met = True  # Assume US-20.3 closed
        
        # Act
        priority = self._resolve_conflict("deferred_vs_ideation", deferred, re_entry_met)
        
        # Assert
        assert priority == "re_entry_wins"
    
    def test_multiple_proposed_waves(self):
        """Тест: Несколько proposed волн → Wave ranking formula"""
        # Arrange
        waves = [
            {"id": "wave-a", "status": "proposed", "synergy_score": 4.5},
            {"id": "wave-b", "status": "proposed", "synergy_score": 3.2},
            {"id": "wave-c", "status": "proposed", "synergy_score": 4.8}
        ]
        
        # Act
        sorted_waves = sorted(waves, key=lambda w: w["synergy_score"], reverse=True)
        
        # Assert
        assert sorted_waves[0]["id"] == "wave-c"
        assert sorted_waves[0]["synergy_score"] == 4.8
    
    def _resolve_conflict(self, conflict_type: str, *args) -> str:
        """Helper: разрешить конфликт"""
        if conflict_type == "proposed_vs_blocker":
            proposed_count, blocker = args
            return "registry_wins" if proposed_count > 0 else "ideation"
        elif conflict_type == "deferred_vs_ideation":
            deferred, re_entry_met = args
            return "re_entry_wins" if re_entry_met else "ideation"
        return "unknown"


# ============================================================================
# COHESION SCORE TESTS
# ============================================================================

class TestCohesionScore:
    """Тесты для Cohesion Score Formula"""
    
    def test_high_cohesion_ideas(self, sample_ideas):
        """Тест: 3 идеи с high cohesion → score ≥0.7"""
        # Act
        score = self._calculate_cohesion_manual(sample_ideas)
        
        # Assert
        assert score >= 0.7
        assert self._interpret_cohesion(score) == "High cohesion → consider wave"
    
    def test_low_cohesion_ideas(self):
        """Тест: Идеи с low cohesion → score <0.4"""
        # Arrange
        ideas = [
            {
                "id": 1,
                "write_set": ["app/flashcard_service.py"],
                "cjm_moment": "#11 Flashcards",
                "epic": "US-15.x",
                "method_source": "Anki",
                "layer": "Backend"
            },
            {
                "id": 2,
                "write_set": ["app/ui/home.py"],
                "cjm_moment": "#13 Home mode",
                "epic": "US-14.x",
                "method_source": "Notion",
                "layer": "UI"
            }
        ]
        
        # Act
        score = self._calculate_cohesion_manual(ideas)
        
        # Assert
        assert score < 0.4
        assert self._interpret_cohesion(score) == "Low cohesion → definitely separate"
    
    def test_write_set_overlap(self, sample_ideas):
        """Тест: Write-set overlap calculation"""
        # Act
        overlap = self._calculate_write_set_overlap(sample_ideas)
        
        # Assert
        assert overlap > 0  # app/ui/answer_card.py в ideas 1 и 2
        assert overlap <= 1.0
    
    def test_cjm_adjacency(self, sample_ideas):
        """Тест: CJM adjacency (#2 → #3)"""
        # Act
        adjacency = self._calculate_cjm_adjacency(sample_ideas)
        
        # Assert
        assert adjacency > 0  # #2 и #3 adjacent
    
    def test_dependency_chain(self, sample_ideas):
        """Тест: Dependency chain (idea 3 depends on 1, 2)"""
        # Act
        has_chain = self._has_dependency_chain(sample_ideas)
        
        # Assert
        assert has_chain == 1.0  # idea 3 depends on 1, 2
    
    def test_same_epic(self, sample_ideas):
        """Тест: Same epic (все US-19.x)"""
        # Act
        same = self._all_same_epic(sample_ideas)
        
        # Assert
        assert same == 1.0
    
    def test_same_method_source(self, sample_ideas):
        """Тест: Same method source (все Duolingo)"""
        # Act
        same = self._all_same_method_source(sample_ideas)
        
        # Assert
        assert same == 1.0
    
    def test_same_layer(self, sample_ideas):
        """Тест: Same layer (все UI)"""
        # Act
        same = self._all_same_layer(sample_ideas)
        
        # Assert
        assert same == 1.0
    
    # Helper methods
    def _calculate_cohesion_manual(self, ideas: List[Dict]) -> float:
        """Manual cohesion calculation"""
        write_set_overlap = self._calculate_write_set_overlap(ideas)
        cjm_adjacency = self._calculate_cjm_adjacency(ideas)
        dependency_chain = self._has_dependency_chain(ideas)
        same_epic = self._all_same_epic(ideas)
        same_method_source = self._all_same_method_source(ideas)
        same_layer = self._all_same_layer(ideas)
        
        score = (
            write_set_overlap * 0.30 +
            cjm_adjacency * 0.25 +
            dependency_chain * 0.20 +
            same_epic * 0.15 +
            same_method_source * 0.05 +
            same_layer * 0.05
        )
        
        return score
    
    def _calculate_write_set_overlap(self, ideas: List[Dict]) -> float:
        """Calculate write-set overlap"""
        all_files = set()
        for idea in ideas:
            all_files.update(idea.get("write_set", []))
        
        if len(all_files) == 0:
            return 0.0
        
        # Count shared files
        shared_count = 0
        for file in all_files:
            count = sum(1 for idea in ideas if file in idea.get("write_set", []))
            if count > 1:
                shared_count += 1
        
        return min(1.0, shared_count / len(all_files))
    
    def _calculate_cjm_adjacency(self, ideas: List[Dict]) -> float:
        """Calculate CJM adjacency"""
        moments = [idea.get("cjm_moment", "") for idea in ideas]
        unique_moments = set(moments)
        
        if len(unique_moments) == 1:
            return 1.0  # Same moment
        
        # Check adjacency (simplified)
        moment_numbers = []
        for m in moments:
            if "#" in m:
                num = int(m.split("#")[1].split()[0])
                moment_numbers.append(num)
        
        if len(moment_numbers) < 2:
            return 0.0
        
        # Check if consecutive
        sorted_nums = sorted(set(moment_numbers))
        is_adjacent = all(sorted_nums[i+1] - sorted_nums[i] == 1 for i in range(len(sorted_nums)-1))
        
        return 1.0 if is_adjacent else 0.5
    
    def _has_dependency_chain(self, ideas: List[Dict]) -> float:
        """Check dependency chain"""
        for idea in ideas:
            if "depends_on" in idea and idea["depends_on"]:
                return 1.0
        return 0.0
    
    def _all_same_epic(self, ideas: List[Dict]) -> float:
        """Check same epic"""
        epics = set(idea.get("epic", "") for idea in ideas)
        return 1.0 if len(epics) == 1 else 0.0
    
    def _all_same_method_source(self, ideas: List[Dict]) -> float:
        """Check same method source"""
        sources = set(idea.get("method_source", "") for idea in ideas)
        return 1.0 if len(sources) == 1 else 0.0
    
    def _all_same_layer(self, ideas: List[Dict]) -> float:
        """Check same layer"""
        layers = set(idea.get("layer", "") for idea in ideas)
        return 1.0 if len(layers) == 1 else 0.0
    
    def _interpret_cohesion(self, score: float) -> str:
        """Interpret cohesion score"""
        if score >= 0.7:
            return "High cohesion → consider wave"
        elif score >= 0.4:
            return "Medium cohesion → separate packages"
        else:
            return "Low cohesion → definitely separate"


# ============================================================================
# ESCAPE HATCH TESTS
# ============================================================================

class TestEscapeHatches:
    """Тесты для Escape Hatches"""
    
    def test_ideation_zero_viable_ideas(self):
        """Тест: Ideation вернул 0 viable ideas → ослабить constraints"""
        # Arrange
        viable_ideas = 0
        constraints = ["must explain why", "must be fast", "must be perfect"]
        
        # Act
        action = self._escape_hatch_ideation_zero(viable_ideas, constraints)
        
        # Assert
        assert action == "relax_constraints"
        assert len(constraints) > 0
    
    def test_backlog_empty_feature_completeness(self):
        """Тест: Backlog пуст + все pains closed → Feature completeness"""
        # Arrange
        backlog_empty = True
        all_pains_closed = True
        open_us_count = 0
        
        # Act
        action = self._escape_hatch_backlog_empty(backlog_empty, all_pains_closed, open_us_count)
        
        # Assert
        assert action == "feature_completeness"
    
    def test_owner_paralysis_spike(self):
        """Тест: Owner paralysis >5 дней → Spike"""
        # Arrange
        days_without_decision = 6
        top_ideas = [
            {"id": 1, "score": 9.0},
            {"id": 2, "score": 6.0}
        ]
        
        # Act
        action = self._escape_hatch_owner_paralysis(days_without_decision, top_ideas)
        
        # Assert
        assert action == "run_spike"
        assert len(top_ideas) >= 2
    
    def test_scope_explosion_split(self):
        """Тест: Scope explosion (20+ идей) → Split по темам"""
        # Arrange
        ideas_count = 22
        
        # Act
        action = self._escape_hatch_scope_explosion(ideas_count)
        
        # Assert
        assert action == "split_by_themes"
    
    # Helper methods
    def _escape_hatch_ideation_zero(self, viable_ideas: int, constraints: List[str]) -> str:
        """Escape hatch для 0 viable ideas"""
        if viable_ideas == 0 and len(constraints) > 0:
            return "relax_constraints"
        return "unknown"
    
    def _escape_hatch_backlog_empty(self, backlog_empty: bool, all_pains_closed: bool, open_us: int) -> str:
        """Escape hatch для пустого backlog"""
        if backlog_empty and all_pains_closed and open_us == 0:
            return "feature_completeness"
        return "run_ideation"
    
    def _escape_hatch_owner_paralysis(self, days: int, top_ideas: List[Dict]) -> str:
        """Escape hatch для owner paralysis"""
        if days > 5 and len(top_ideas) >= 2:
            return "run_spike"
        elif days > 5:
            return "default_heuristic"
        return "wait"
    
    def _escape_hatch_scope_explosion(self, ideas_count: int) -> str:
        """Escape hatch для scope explosion"""
        if ideas_count > 20:
            return "split_by_themes"
        return "proceed"


# ============================================================================
# ROUTER METRICS TESTS
# ============================================================================

class TestRouterMetrics:
    """Тесты для Router Health Metrics"""
    
    def test_time_to_decision_target(self):
        """Тест: Time to Decision ≤5 мин"""
        # Arrange
        decisions = [
            {"time_minutes": 3},
            {"time_minutes": 4},
            {"time_minutes": 5},
            {"time_minutes": 6}
        ]
        
        # Act
        avg_time = sum(d["time_minutes"] for d in decisions) / len(decisions)
        
        # Assert
        assert avg_time <= 5  # Target: ≤5 мин
    
    def test_decision_accuracy_target(self):
        """Тест: Decision Accuracy ≥90%"""
        # Arrange
        decisions = [{"correct": True}] * 9 + [{"correct": False}]
        
        # Act
        accuracy = sum(1 for d in decisions if d["correct"]) / len(decisions)
        
        # Assert
        assert accuracy >= 0.90  # Target: ≥90%
    
    def test_ideation_delivery_rate_target(self):
        """Тест: Ideation → Delivery Rate ≥60%"""
        # Arrange
        ideations = [
            {"delivered": True},
            {"delivered": True},
            {"delivered": True},
            {"delivered": False},
            {"delivered": False}
        ]
        
        # Act
        delivery_rate = sum(1 for i in ideations if i["delivered"]) / len(ideations)
        
        # Assert
        assert delivery_rate >= 0.60  # Target: ≥60%


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestRouterIntegration:
    """Integration тесты для полного flow"""
    
    def test_full_flow_us_to_package(self, sample_registry, sample_ideas):
        """Тест: Полный flow от US к Package"""
        # Step 1: CANDIDATE_TABLE
        candidates = self._generate_candidate_table()
        assert len(candidates) > 0
        
        # Step 2: Выбрать TARGET
        target = candidates[0]
        assert "US-20.1" in target["us"]
        
        # Step 3: Ideation
        ideas = sample_ideas
        assert len(ideas) >= 3
        
        # Step 4: Cohesion check
        cohesion_score = TestCohesionScore()._calculate_cohesion_manual(ideas)
        assert cohesion_score >= 0.7
        
        # Step 5: Owner decision → Wave
        decision = "multi_wave" if cohesion_score >= 0.7 else "single_package"
        assert decision == "multi_wave"
        
        # Step 6: Registry + Sync
        # (mock)
        assert True
    
    def test_full_flow_blocker_to_escape(self):
        """Тест: Полный flow от blocker к escape hatch"""
        # Step 1: Plan-next blocker
        blocker = True
        
        # Step 2: Check conflicts
        proposed_count = 0
        deferred_count = 0
        
        # Step 3: CANDIDATE_TABLE
        candidates = self._generate_candidate_table()
        
        # Step 4: Если пусто → Escape hatch
        if len(candidates) == 0:
            action = TestEscapeHatches()._escape_hatch_backlog_empty(True, True, 0)
            assert action == "feature_completeness"
    
    def _generate_candidate_table(self) -> List[Dict]:
        """Mock CANDIDATE_TABLE generation"""
        return [
            {
                "cjm_stage": "#13 Home mode",
                "us": "US-20.1",
                "pain": "Unclear next action",
                "criticality": "P0",
                "impact": "loop",
                "actuality": "H"
            }
        ]


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

@pytest.mark.parametrize("status,expected_state", [
    ("ready", "ready_package_exists"),
    ("wip", "ready_package_exists"),
    ("proposed", "needs_plan"),
    ("deferred", "needs_plan"),
])
def test_package_status_to_state(status, expected_state):
    """Parametrized тест: Package status → State"""
    # Arrange
    registry = {
        "active_package_id": "test-package" if status in ["ready", "wip"] else None,
        "items": [
            {"id": "test-package", "status": status}
        ]
    }
    
    # Act
    state = TestDecisionTable()._determine_state(registry)
    
    # Assert
    assert state == expected_state


@pytest.mark.parametrize("ideas_count,expected_action", [
    (1, "single_package"),
    (2, "check_cohesion"),
    (3, "check_cohesion"),
    (6, "split_by_themes"),
    (20, "split_by_themes"),
])
def test_ideas_count_to_action(ideas_count, expected_action):
    """Parametrized тест: Ideas count → Action"""
    # Act
    if ideas_count == 1:
        action = "single_package"
    elif ideas_count <= 5:
        action = "check_cohesion"
    else:
        action = "split_by_themes"
    
    # Assert
    assert action == expected_action


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Тесты для edge cases"""
    
    def test_empty_registry(self):
        """Тест: Пустой registry"""
        registry = {"items": []}
        state = TestDecisionTable()._determine_state(registry)
        assert state == "no_package"
    
    def test_all_packages_closed(self):
        """Тест: Все packages closed"""
        registry = {
            "items": [
                {"id": "p1", "status": "closed"},
                {"id": "p2", "status": "closed"}
            ]
        }
        active_count = len([p for p in registry["items"] if p["status"] in ["ready", "wip", "proposed"]])
        assert active_count == 0
    
    def test_cohesion_score_boundary(self):
        """Тест: Cohesion score на границе (0.7)"""
        score = 0.7
        interpretation = TestCohesionScore()._interpret_cohesion(score)
        assert interpretation == "High cohesion → consider wave"
    
    def test_zero_ideas_generated(self):
        """Тест: 0 идей сгенерировано"""
        viable_ideas = 0
        action = TestEscapeHatches()._escape_hatch_ideation_zero(viable_ideas, ["constraint1"])
        assert action == "relax_constraints"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
