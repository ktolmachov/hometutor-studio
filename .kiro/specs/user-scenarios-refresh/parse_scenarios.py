"""
Parse existing 22 scenarios from doc/user_scenarios.md

Task 2.1: Extract scenario numbers, titles, covered features, and personas
Build coverage map: scenario_number → covered_features/waves
Identify which MoT moments are covered by existing scenarios
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set
import json


@dataclass
class Scenario:
    """Represents a parsed user scenario"""
    number: int
    title: str
    persona: Optional[str] = None
    time_estimate: Optional[str] = None
    main_question: Optional[str] = None
    level: Optional[str] = None  # "Первые шаги", "Учебный ритм", "Мастерство", "Power user"
    covered_features: List[str] = field(default_factory=list)
    covered_waves: List[str] = field(default_factory=list)
    mot_moments: Set[str] = field(default_factory=set)  # MoT moments mentioned
    yaml_artifact: Optional[str] = None
    e2e_test: Optional[str] = None


def parse_scenarios(file_path: str) -> List[Scenario]:
    """Parse all scenarios from user_scenarios.md"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    scenarios = []
    
    # Find all scenario sections using regex
    # Pattern: ## Сценарий N — Title
    scenario_pattern = r'## Сценарий (\d+) — (.+?)(?=\n)'
    matches = re.finditer(scenario_pattern, content)
    
    for match in matches:
        scenario_num = int(match.group(1))
        scenario_title = match.group(2).strip()
        
        # Extract the full scenario section (from this heading to next ## or end)
        start_pos = match.start()
        # Find next scenario or end of file
        next_match = re.search(r'\n## Сценарий \d+', content[start_pos + 1:])
        if next_match:
            end_pos = start_pos + 1 + next_match.start()
        else:
            # Check for other ## headings (like "Связанные документы")
            next_section = re.search(r'\n## [^С]', content[start_pos + 1:])
            if next_section:
                end_pos = start_pos + 1 + next_section.start()
            else:
                end_pos = len(content)
        
        scenario_text = content[start_pos:end_pos]
        
        # Parse scenario details
        scenario = Scenario(number=scenario_num, title=scenario_title)
        
        # Extract persona (look for "Для кого:")
        persona_match = re.search(r'\*\*Для кого:\*\* (.+?)(?:\n|\.|,)', scenario_text)
        if persona_match:
            scenario.persona = persona_match.group(1).strip()
        
        # Extract time estimate
        time_match = re.search(r'\*\*Время:\*\* (.+?)(?:\n|\.)', scenario_text)
        if time_match:
            scenario.time_estimate = time_match.group(1).strip()
        
        # Extract main question
        question_match = re.search(r'\*\*Главный вопрос:\*\* [«"](.+?)[»"]', scenario_text)
        if question_match:
            scenario.main_question = question_match.group(1).strip()
        
        # Determine level based on scenario number (from "Карта уровней" table)
        if scenario_num in [1, 2, 3, 15, 16, 19]:
            scenario.level = "Первые шаги"
        elif scenario_num in [4, 5, 6, 7]:
            scenario.level = "Учебный ритм"
        elif scenario_num in [8, 9, 10, 11, 17, 18, 20, 21, 22]:
            scenario.level = "Мастерство"
        elif scenario_num in [12, 13, 14]:
            scenario.level = "Power user"
        
        # Extract covered features (look for key terms)
        features = []
        if 'Quick Answer' in scenario_text or 'Быстрый ответ' in scenario_text:
            features.append('Quick Answer')
        if 'тьютор' in scenario_text.lower() or 'tutor' in scenario_text.lower():
            features.append('Tutor')
        if 'flashcard' in scenario_text.lower() or 'карточк' in scenario_text.lower():
            features.append('Flashcards')
        if 'SM-2' in scenario_text or 'повторение' in scenario_text:
            features.append('Spaced Repetition')
        if 'Course' in scenario_text or 'курс' in scenario_text.lower():
            features.append('Course Workspace')
        if 'Adaptive' in scenario_text or 'адаптивн' in scenario_text.lower():
            features.append('Adaptive Plan')
        if 'mastery' in scenario_text.lower() or 'освоен' in scenario_text.lower():
            features.append('Mastery Tracking')
        if 'Trust' in scenario_text or 'доверие' in scenario_text.lower() or 'источник' in scenario_text.lower():
            features.append('Trust Panel')
        if 'Telegram' in scenario_text:
            features.append('Telegram Bot')
        if 'reindex' in scenario_text.lower() or 'переиндекс' in scenario_text.lower():
            features.append('Reindexing')
        if 'backup' in scenario_text.lower() or 'офлайн' in scenario_text.lower():
            features.append('Backup & Offline')
        if 'UX Breakthrough' in scenario_text or 'skeleton' in scenario_text.lower():
            features.append('UX Breakthrough')
        if 'интерактивный тур' in scenario_text.lower() or 'interactive tour' in scenario_text.lower():
            features.append('Interactive Tour')
        if 'diff' in scenario_text.lower() or 'изменилось в плане' in scenario_text.lower():
            features.append('Plan Diff')
        if 'главная' in scenario_text.lower() or 'home' in scenario_text.lower() and scenario_num == 18:
            features.append('Home Hub')
        if 'окружение' in scenario_text.lower() or 'env' in scenario_text.lower():
            features.append('Environment Validation')
        if 'педагогический роутер' in scenario_text.lower() or 'pedagogical router' in scenario_text.lower():
            features.append('Pedagogical Router')
        if 'Умный Маршрутизатор' in scenario_text or 'Smart Study Router' in scenario_text or 'SSR' in scenario_text:
            features.append('Smart Study Router')
        if 'AI Vision' in scenario_text or 'ИИ' in scenario_text and scenario_num == 22:
            features.append('AI Vision')
        
        scenario.covered_features = features
        
        # Extract MoT moments (look for #N patterns)
        mot_pattern = r'#(\d+)[:\s]'
        mot_matches = re.finditer(mot_pattern, scenario_text)
        for mot_match in mot_matches:
            scenario.mot_moments.add(f"#{mot_match.group(1)}")
        
        # Also check for specific MoT names
        mot_names = {
            'Discover': '#1',
            'First Answer': '#2',
            'Transition to tutor': '#3',
            'Home mode selection': '#13'
        }
        for name, mot_id in mot_names.items():
            if name.lower() in scenario_text.lower():
                scenario.mot_moments.add(mot_id)
        
        # Extract wave references (look for wave-* patterns)
        wave_pattern = r'wave-[\w-]+'
        wave_matches = re.finditer(wave_pattern, scenario_text)
        for wave_match in wave_matches:
            scenario.covered_waves.append(wave_match.group(0))
        
        # Extract YAML artifact reference
        yaml_match = re.search(r'scenario_(\d+)_[\w_]+\.yaml', scenario_text)
        if yaml_match:
            scenario.yaml_artifact = yaml_match.group(0)
        
        # Extract e2e test reference
        e2e_match = re.search(r'scenario_(\d+)[\w_]*\.spec\.ts', scenario_text)
        if e2e_match:
            scenario.e2e_test = e2e_match.group(0)
        
        scenarios.append(scenario)
    
    return scenarios


def build_coverage_map(scenarios: List[Scenario]) -> dict:
    """Build coverage map: scenario_number → covered_features/waves"""
    
    coverage_map = {}
    
    for scenario in scenarios:
        coverage_map[scenario.number] = {
            'title': scenario.title,
            'level': scenario.level,
            'persona': scenario.persona,
            'covered_features': scenario.covered_features,
            'covered_waves': list(set(scenario.covered_waves)),  # deduplicate
            'mot_moments': sorted(list(scenario.mot_moments)),
            'yaml_artifact': scenario.yaml_artifact,
            'e2e_test': scenario.e2e_test
        }
    
    return coverage_map


def analyze_mot_coverage(scenarios: List[Scenario]) -> dict:
    """Identify which MoT moments are covered by existing scenarios"""
    
    mot_coverage = {}
    
    for scenario in scenarios:
        for mot in scenario.mot_moments:
            if mot not in mot_coverage:
                mot_coverage[mot] = []
            mot_coverage[mot].append({
                'scenario_number': scenario.number,
                'scenario_title': scenario.title
            })
    
    return mot_coverage


def generate_report(scenarios: List[Scenario], coverage_map: dict, mot_coverage: dict):
    """Generate analysis report"""
    
    print("=" * 80)
    print("TASK 2.1: PARSE EXISTING 22 SCENARIOS")
    print("=" * 80)
    print()
    
    print(f"Total scenarios found: {len(scenarios)}")
    print()
    
    # Scenarios by level
    print("SCENARIOS BY LEVEL:")
    print("-" * 80)
    levels = {}
    for scenario in scenarios:
        level = scenario.level or "Unknown"
        if level not in levels:
            levels[level] = []
        levels[level].append(scenario.number)
    
    for level, nums in sorted(levels.items()):
        print(f"  {level}: {len(nums)} scenarios - {nums}")
    print()
    
    # Feature coverage
    print("FEATURE COVERAGE:")
    print("-" * 80)
    feature_count = {}
    for scenario in scenarios:
        for feature in scenario.covered_features:
            feature_count[feature] = feature_count.get(feature, 0) + 1
    
    for feature, count in sorted(feature_count.items(), key=lambda x: -x[1]):
        scenarios_with_feature = [s.number for s in scenarios if feature in s.covered_features]
        print(f"  {feature}: {count} scenarios - {scenarios_with_feature}")
    print()
    
    # MoT coverage
    print("MOT MOMENT COVERAGE:")
    print("-" * 80)
    for mot in sorted(mot_coverage.keys(), key=lambda x: int(x[1:])):
        scenarios_list = [f"#{s['scenario_number']}" for s in mot_coverage[mot]]
        print(f"  {mot}: {len(mot_coverage[mot])} scenarios - {', '.join(scenarios_list)}")
    print()
    
    # Wave coverage
    print("WAVE COVERAGE:")
    print("-" * 80)
    wave_count = {}
    for scenario in scenarios:
        for wave in scenario.covered_waves:
            if wave not in wave_count:
                wave_count[wave] = []
            wave_count[wave].append(scenario.number)
    
    if wave_count:
        for wave, scenario_nums in sorted(wave_count.items()):
            print(f"  {wave}: scenarios {scenario_nums}")
    else:
        print("  No explicit wave references found in scenarios")
    print()
    
    # Artifact coverage
    print("ARTIFACT COVERAGE:")
    print("-" * 80)
    with_yaml = [s.number for s in scenarios if s.yaml_artifact]
    with_e2e = [s.number for s in scenarios if s.e2e_test]
    print(f"  Scenarios with YAML artifacts: {len(with_yaml)} - {with_yaml}")
    print(f"  Scenarios with e2e tests: {len(with_e2e)} - {with_e2e}")
    print()
    
    # Detailed scenario list
    print("DETAILED SCENARIO LIST:")
    print("-" * 80)
    for scenario in sorted(scenarios, key=lambda s: s.number):
        print(f"\nScenario {scenario.number}: {scenario.title}")
        print(f"  Level: {scenario.level}")
        print(f"  Persona: {scenario.persona}")
        print(f"  Time: {scenario.time_estimate}")
        print(f"  Main Question: {scenario.main_question}")
        print(f"  Features: {', '.join(scenario.covered_features) if scenario.covered_features else 'None identified'}")
        print(f"  MoT Moments: {', '.join(sorted(scenario.mot_moments)) if scenario.mot_moments else 'None identified'}")
        print(f"  Waves: {', '.join(scenario.covered_waves) if scenario.covered_waves else 'None identified'}")
        print(f"  YAML: {scenario.yaml_artifact or 'Not found'}")
        print(f"  E2E Test: {scenario.e2e_test or 'Not found'}")
    
    print()
    print("=" * 80)


def main():
    """Main execution"""
    
    # Parse scenarios
    file_path = r'd:\Projects\home-rag_v2\doc\user_scenarios.md'
    scenarios = parse_scenarios(file_path)
    
    # Build coverage map
    coverage_map = build_coverage_map(scenarios)
    
    # Analyze MoT coverage
    mot_coverage = analyze_mot_coverage(scenarios)
    
    # Generate report
    generate_report(scenarios, coverage_map, mot_coverage)
    
    # Save results to JSON for next tasks
    output = {
        'scenarios': [
            {
                'number': s.number,
                'title': s.title,
                'level': s.level,
                'persona': s.persona,
                'time_estimate': s.time_estimate,
                'main_question': s.main_question,
                'covered_features': s.covered_features,
                'covered_waves': s.covered_waves,
                'mot_moments': sorted(list(s.mot_moments)),
                'yaml_artifact': s.yaml_artifact,
                'e2e_test': s.e2e_test
            }
            for s in sorted(scenarios, key=lambda s: s.number)
        ],
        'coverage_map': coverage_map,
        'mot_coverage': mot_coverage,
        'summary': {
            'total_scenarios': len(scenarios),
            'scenarios_by_level': {
                level: len([s for s in scenarios if s.level == level])
                for level in ["Первые шаги", "Учебный ритм", "Мастерство", "Power user"]
            },
            'scenarios_with_yaml': len([s for s in scenarios if s.yaml_artifact]),
            'scenarios_with_e2e': len([s for s in scenarios if s.e2e_test]),
            'unique_features': len(set(f for s in scenarios for f in s.covered_features)),
            'mot_moments_covered': len(mot_coverage)
        }
    }
    
    output_path = r'd:\Projects\home-rag_v2\.kiro\specs\user-scenarios-refresh\scenario_analysis.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Results saved to: {output_path}")


if __name__ == '__main__':
    main()
