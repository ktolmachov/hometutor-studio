"""
Parse existing 22 scenarios from doc/user_scenarios.md

Task 2.1: Extract scenario numbers, titles, covered features, and personas
Build coverage map: scenario_number → covered_features/waves
Identify which MoT moments are covered by existing scenarios
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set
from pathlib import Path


@dataclass
class ScenarioInfo:
    """Information about a single scenario"""
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


def parse_scenarios(file_path: str) -> List[ScenarioInfo]:
    """Parse all scenarios from user_scenarios.md"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    scenarios = []
    
    # Split by scenario headers
    scenario_pattern = r'## Сценарий (\d+) — (.+?)(?=\n## Сценарий |\Z)'
    matches = re.finditer(scenario_pattern, content, re.DOTALL)
    
    for match in matches:
        number = int(match.group(1))
        title = match.group(2).strip()
        scenario_text = match.group(0)
        
        scenario = ScenarioInfo(number=number, title=title)
        
        # Extract persona
        persona_match = re.search(r'\*\*Для кого:\*\* ([^,\n]+)', scenario_text)
        if persona_match:
            scenario.persona = persona_match.group(1).strip()
        
        # Extract time estimate
        time_match = re.search(r'\*\*Время:\*\* (.+?)(?:\.|$)', scenario_text)
        if time_match:
            scenario.time_estimate = time_match.group(1).strip()
        
        # Extract main question
        question_match = re.search(r'\*\*Главный вопрос:\*\* [«"](.+?)[»"]', scenario_text)
        if question_match:
            scenario.main_question = question_match.group(1).strip()
        
        # Determine level based on scenario number and content
        scenario.level = determine_level(number, scenario_text)
        
        # Extract covered features from context and steps
        scenario.covered_features = extract_features(scenario_text)
        
        # Extract wave references
        scenario.covered_waves = extract_wave_references(scenario_text)
        
        # Extract MoT moments
        scenario.mot_moments = extract_mot_moments(scenario_text)
        
        # Extract YAML artifact reference
        yaml_match = re.search(r'doc/scenarios/(scenario_\d+_\w+\.yaml)', scenario_text)
        if yaml_match:
            scenario.yaml_artifact = yaml_match.group(1)
        
        # Extract e2e test reference
        e2e_match = re.search(r'tests/e2e/demos/(scenario_\d+[^)]+\.spec\.ts)', scenario_text)
        if e2e_match:
            scenario.e2e_test = e2e_match.group(1)
        
        scenarios.append(scenario)
    
    return scenarios


def determine_level(number: int, text: str) -> str:
    """Determine scenario level based on number and content"""
    # Based on "Карта уровней" table in the document
    if number in [1, 2, 3, 15, 16, 19]:
        return "Первые шаги"
    elif number in [4, 5, 6, 7]:
        return "Учебный ритм"
    elif number in [8, 9, 10, 11, 17, 18, 20, 21, 22]:
        return "Мастерство"
    elif number in [12, 13, 14]:
        return "Power user"
    else:
        return "Unknown"


def extract_features(text: str) -> List[str]:
    """Extract covered features from scenario text"""
    features = []
    
    # Common feature keywords to look for
    feature_keywords = {
        'Quick Answer': ['быстрый ответ', 'quick answer'],
        'Tutor': ['тьютор', 'tutor', 'учебная сессия'],
        'Flashcards': ['flashcard', 'флеш-карточ', 'карточк'],
        'SM-2': ['sm-2', 'повторение', 'spaced repetition'],
        'Course Workspace': ['course workspace', 'курс', 'course'],
        'Adaptive Plan': ['adaptive plan', 'адаптивный план', 'daily plan'],
        'Mastery': ['mastery', 'освоение', 'graduation'],
        'Trust Panel': ['trust', 'доверие', 'источник'],
        'Telegram': ['telegram', 'телеграм'],
        'Reindex': ['reindex', 'переиндексация', 'ingest'],
        'Backup': ['backup', 'бэкап', 'офлайн', 'offline'],
        'UX Breakthrough': ['ux breakthrough', 'skeleton', 'celebration'],
        'Interactive Tour': ['интерактивный тур', 'interactive tour'],
        'Plan Diff': ['plan diff', 'diff плана', 'что изменилось'],
        'Home Hub': ['главная', 'home', 'режим'],
        'Environment': ['окружение', 'environment', 'env'],
        'Pedagogical Router': ['педагогический роутер', 'pedagogical router', 'адаптивный маршрут'],
        'Smart Study Router': ['умный маршрутизатор', 'smart study router', 'ssr'],
        'AI Vision': ['ai vision', 'ии', 'ml layer']
    }
    
    text_lower = text.lower()
    for feature, keywords in feature_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            features.append(feature)
    
    return features


def extract_wave_references(text: str) -> List[str]:
    """Extract wave references from scenario text"""
    waves = []
    
    # Look for wave-* patterns
    wave_pattern = r'wave-[\w-]+'
    wave_matches = re.findall(wave_pattern, text, re.IGNORECASE)
    waves.extend(wave_matches)
    
    # Look for ssr-* patterns
    ssr_pattern = r'ssr-[\w-]+'
    ssr_matches = re.findall(ssr_pattern, text, re.IGNORECASE)
    waves.extend(ssr_matches)
    
    return list(set(waves))  # Remove duplicates


def extract_mot_moments(text: str) -> Set[str]:
    """Extract MoT (Moment of Truth) references from scenario text"""
    mot_moments = set()
    
    # Look for #N patterns (e.g., #1, #2, #13)
    mot_pattern = r'#(\d+)'
    mot_matches = re.findall(mot_pattern, text)
    mot_moments.update(f"#{num}" for num in mot_matches)
    
    # Look for explicit MoT descriptions
    mot_keywords = {
        '#1': ['discover', 'первый запуск', 'first launch'],
        '#2': ['first answer', 'первый ответ'],
        '#3': ['transition to tutor', 'мост', 'переход к тьютору'],
        '#4': ['learning session', 'учебная сессия'],
        '#5': ['flashcard generation', 'генерация карточек'],
        '#6': ['spaced repetition', 'sm-2', 'повторение'],
        '#7': ['return next day', 'возврат', 'следующий день'],
        '#8': ['course workspace', 'курс'],
        '#9': ['adaptive plan', 'адаптивный план'],
        '#10': ['mastery', 'graduation', 'освоение'],
        '#11': ['trust', 'доверие'],
        '#12': ['telegram', 'mobile'],
        '#13': ['home mode selection', 'главная', 'режим'],
        '#14': ['backup', 'offline', 'офлайн']
    }
    
    text_lower = text.lower()
    for mot, keywords in mot_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            mot_moments.add(mot)
    
    return mot_moments


def build_coverage_map(scenarios: List[ScenarioInfo]) -> dict:
    """Build coverage map: scenario_number → covered_features/waves"""
    coverage_map = {}
    
    for scenario in scenarios:
        coverage_map[scenario.number] = {
            'title': scenario.title,
            'level': scenario.level,
            'persona': scenario.persona,
            'features': scenario.covered_features,
            'waves': scenario.covered_waves,
            'mot_moments': sorted(list(scenario.mot_moments)),
            'yaml_artifact': scenario.yaml_artifact,
            'e2e_test': scenario.e2e_test
        }
    
    return coverage_map


def generate_report(scenarios: List[ScenarioInfo], coverage_map: dict) -> str:
    """Generate a detailed report of scenario coverage"""
    
    report = []
    report.append("=" * 80)
    report.append("SCENARIO COVERAGE ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Summary statistics
    report.append("SUMMARY STATISTICS")
    report.append("-" * 80)
    report.append(f"Total scenarios: {len(scenarios)}")
    
    # Count by level
    level_counts = {}
    for scenario in scenarios:
        level_counts[scenario.level] = level_counts.get(scenario.level, 0) + 1
    
    report.append("\nScenarios by level:")
    for level, count in sorted(level_counts.items()):
        report.append(f"  {level}: {count}")
    
    # Count scenarios with artifacts
    with_yaml = sum(1 for s in scenarios if s.yaml_artifact)
    with_e2e = sum(1 for s in scenarios if s.e2e_test)
    report.append(f"\nScenarios with YAML artifacts: {with_yaml}/{len(scenarios)}")
    report.append(f"Scenarios with e2e tests: {with_e2e}/{len(scenarios)}")
    
    # MoT coverage
    all_mot_moments = set()
    for scenario in scenarios:
        all_mot_moments.update(scenario.mot_moments)
    
    report.append(f"\nMoT moments covered: {len(all_mot_moments)}")
    report.append(f"MoT moments: {', '.join(sorted(all_mot_moments, key=lambda x: int(x[1:])))}")
    
    # Feature coverage
    all_features = set()
    for scenario in scenarios:
        all_features.update(scenario.covered_features)
    
    report.append(f"\nUnique features covered: {len(all_features)}")
    
    # Wave references
    all_waves = set()
    for scenario in scenarios:
        all_waves.update(scenario.covered_waves)
    
    report.append(f"\nWave references found: {len(all_waves)}")
    if all_waves:
        report.append("Waves mentioned:")
        for wave in sorted(all_waves):
            report.append(f"  - {wave}")
    
    report.append("")
    report.append("=" * 80)
    report.append("DETAILED SCENARIO BREAKDOWN")
    report.append("=" * 80)
    report.append("")
    
    # Detailed breakdown by scenario
    for scenario in sorted(scenarios, key=lambda s: s.number):
        report.append(f"Scenario {scenario.number}: {scenario.title}")
        report.append("-" * 80)
        report.append(f"Level: {scenario.level}")
        report.append(f"Persona: {scenario.persona or 'Not specified'}")
        report.append(f"Time: {scenario.time_estimate or 'Not specified'}")
        report.append(f"Main Question: {scenario.main_question or 'Not specified'}")
        
        if scenario.covered_features:
            report.append(f"Covered Features ({len(scenario.covered_features)}):")
            for feature in scenario.covered_features:
                report.append(f"  - {feature}")
        else:
            report.append("Covered Features: None identified")
        
        if scenario.covered_waves:
            report.append(f"Wave References ({len(scenario.covered_waves)}):")
            for wave in scenario.covered_waves:
                report.append(f"  - {wave}")
        else:
            report.append("Wave References: None")
        
        if scenario.mot_moments:
            report.append(f"MoT Moments: {', '.join(sorted(scenario.mot_moments, key=lambda x: int(x[1:])))}")
        else:
            report.append("MoT Moments: None identified")
        
        report.append(f"YAML Artifact: {scenario.yaml_artifact or 'Not found'}")
        report.append(f"E2E Test: {scenario.e2e_test or 'Not found'}")
        report.append("")
    
    report.append("=" * 80)
    report.append("MoT COVERAGE MATRIX")
    report.append("=" * 80)
    report.append("")
    
    # Build MoT coverage matrix
    mot_coverage = {}
    for scenario in scenarios:
        for mot in scenario.mot_moments:
            if mot not in mot_coverage:
                mot_coverage[mot] = []
            mot_coverage[mot].append(scenario.number)
    
    for mot in sorted(mot_coverage.keys(), key=lambda x: int(x[1:])):
        scenarios_list = ', '.join(str(s) for s in sorted(mot_coverage[mot]))
        report.append(f"{mot}: Scenarios {scenarios_list}")
    
    report.append("")
    report.append("=" * 80)
    report.append("FEATURE COVERAGE MATRIX")
    report.append("=" * 80)
    report.append("")
    
    # Build feature coverage matrix
    feature_coverage = {}
    for scenario in scenarios:
        for feature in scenario.covered_features:
            if feature not in feature_coverage:
                feature_coverage[feature] = []
            feature_coverage[feature].append(scenario.number)
    
    for feature in sorted(feature_coverage.keys()):
        scenarios_list = ', '.join(str(s) for s in sorted(feature_coverage[feature]))
        report.append(f"{feature}: Scenarios {scenarios_list}")
    
    report.append("")
    report.append("=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)
    
    return '\n'.join(report)


def main():
    """Main execution function"""
    
    # Path to user_scenarios.md
    scenarios_file = Path(__file__).parent.parent.parent.parent / 'doc' / 'user_scenarios.md'
    
    print(f"Parsing scenarios from: {scenarios_file}")
    print()
    
    # Parse scenarios
    scenarios = parse_scenarios(str(scenarios_file))
    
    print(f"Found {len(scenarios)} scenarios")
    print()
    
    # Build coverage map
    coverage_map = build_coverage_map(scenarios)
    
    # Generate report
    report = generate_report(scenarios, coverage_map)
    
    # Save report
    report_file = Path(__file__).parent / 'scenario_coverage_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report saved to: {report_file}")
    print()
    
    # Print summary to console
    print("SUMMARY:")
    print(f"  Total scenarios: {len(scenarios)}")
    print(f"  Scenarios with YAML: {sum(1 for s in scenarios if s.yaml_artifact)}")
    print(f"  Scenarios with e2e: {sum(1 for s in scenarios if s.e2e_test)}")
    
    all_mot = set()
    for s in scenarios:
        all_mot.update(s.mot_moments)
    print(f"  MoT moments covered: {len(all_mot)}")
    
    all_features = set()
    for s in scenarios:
        all_features.update(s.covered_features)
    print(f"  Unique features: {len(all_features)}")
    
    all_waves = set()
    for s in scenarios:
        all_waves.update(s.covered_waves)
    print(f"  Wave references: {len(all_waves)}")
    
    print()
    print("Full report available in scenario_coverage_report.txt")


if __name__ == '__main__':
    main()
