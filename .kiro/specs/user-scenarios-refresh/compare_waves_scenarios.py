#!/usr/bin/env python3
"""
Task 2.2: Compare closed waves against existing scenario coverage

This script:
1. Loads closed waves from closed_waves.json
2. Loads scenario coverage from scenario_coverage_report.txt
3. Compares each wave against scenarios to identify gaps
4. Classifies gaps as: new_feature, ui_update, flow_change
5. Identifies partial vs complete coverage
6. Generates a gap analysis report
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set
from pathlib import Path


@dataclass
class Scenario:
    """Represents a user scenario from the coverage report"""
    number: int
    title: str
    level: str
    persona: str
    time: str
    main_question: str
    covered_features: List[str]
    mot_moments: List[str]
    yaml_artifact: Optional[str]
    e2e_test: Optional[str]


@dataclass
class Wave:
    """Represents a closed wave from backlog_registry.yaml"""
    id: str
    theme: str
    north_star: str
    entry_mot: str
    exit_mot: str
    packages: List[str]
    status: str
    created: str
    last_touched_mot: Optional[str]


@dataclass
class Gap:
    """Represents a gap between a closed wave and scenario coverage"""
    wave_id: str
    theme: str
    north_star: str
    entry_mot: str
    exit_mot: str
    gap_type: str  # "new_feature", "ui_update", "flow_change"
    coverage_status: str  # "not_covered", "partial", "complete"
    affected_scenarios: List[int]
    recommended_action: str  # "create_new", "update_existing", "verify_coverage"
    notes: str = ""


def load_closed_waves(json_path: Path) -> List[Wave]:
    """Load closed waves from JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    waves = []
    for item in data:
        waves.append(Wave(
            id=item['id'],
            theme=item['theme'],
            north_star=item['north_star'],
            entry_mot=item['entry_mot'],
            exit_mot=item['exit_mot'],
            packages=item['packages'],
            status=item['status'],
            created=item['created'],
            last_touched_mot=item.get('last_touched_mot')
        ))
    
    return waves


def parse_scenario_coverage(report_path: Path) -> List[Scenario]:
    """Parse scenario coverage report to extract scenario details"""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    scenarios = []
    
    # Split by scenario sections
    scenario_blocks = re.split(r'-{80,}\n', content)
    
    for block in scenario_blocks:
        # Look for scenario metadata
        number_match = re.search(r'Scenario (\d+):', block)
        if not number_match:
            continue
        
        number = int(number_match.group(1))
        
        # Extract fields
        title_match = re.search(r'Scenario \d+: (.+)', block)
        level_match = re.search(r'Level: (.+)', block)
        persona_match = re.search(r'Persona: (.+)', block)
        time_match = re.search(r'Time: (.+)', block)
        question_match = re.search(r'Main Question: (.+)', block)
        
        # Extract covered features
        features = []
        features_section = re.search(r'Covered Features \(\d+\):\n((?:  - .+\n)+)', block)
        if features_section:
            features = [line.strip('- \n') for line in features_section.group(1).split('\n') if line.strip()]
        
        # Extract MoT moments
        mot_moments = []
        mot_match = re.search(r'MoT Moments: (.+)', block)
        if mot_match:
            mot_moments = [m.strip() for m in mot_match.group(1).split(',')]
        
        # Extract artifacts
        yaml_match = re.search(r'YAML Artifact: (.+)', block)
        e2e_match = re.search(r'E2E Test: (.+)', block)
        
        scenarios.append(Scenario(
            number=number,
            title=title_match.group(1) if title_match else "",
            level=level_match.group(1) if level_match else "",
            persona=persona_match.group(1) if persona_match else "",
            time=time_match.group(1) if time_match else "",
            main_question=question_match.group(1) if question_match else "",
            covered_features=features,
            mot_moments=mot_moments,
            yaml_artifact=yaml_match.group(1) if yaml_match and yaml_match.group(1) != "Not found" else None,
            e2e_test=e2e_match.group(1) if e2e_match and e2e_match.group(1) != "Not found" else None
        ))
    
    return scenarios


def check_wave_coverage(wave: Wave, scenarios: List[Scenario]) -> Gap:
    """Check if a wave is covered by existing scenarios"""
    
    # Keywords to search for in scenarios
    wave_keywords = extract_keywords(wave.theme, wave.north_star)
    
    # Find scenarios that mention this wave's themes
    affected_scenarios = []
    coverage_notes = []
    
    for scenario in scenarios:
        # Check if scenario covers this wave's MoT
        if wave.entry_mot in scenario.mot_moments or wave.exit_mot in scenario.mot_moments:
            affected_scenarios.append(scenario.number)
            coverage_notes.append(f"Scenario {scenario.number} covers MoT {wave.entry_mot}")
        
        # Check if scenario mentions wave keywords
        scenario_text = f"{scenario.title} {' '.join(scenario.covered_features)} {scenario.main_question}".lower()
        for keyword in wave_keywords:
            if keyword in scenario_text:
                if scenario.number not in affected_scenarios:
                    affected_scenarios.append(scenario.number)
                coverage_notes.append(f"Scenario {scenario.number} mentions '{keyword}'")
    
    # Determine gap type and coverage status
    gap_type = classify_gap_type(wave)
    coverage_status = determine_coverage_status(wave, affected_scenarios, scenarios)
    recommended_action = determine_action(coverage_status, gap_type, affected_scenarios)
    
    notes = "; ".join(coverage_notes) if coverage_notes else "No direct coverage found"
    
    return Gap(
        wave_id=wave.id,
        theme=wave.theme,
        north_star=wave.north_star,
        entry_mot=wave.entry_mot,
        exit_mot=wave.exit_mot,
        gap_type=gap_type,
        coverage_status=coverage_status,
        affected_scenarios=sorted(affected_scenarios),
        recommended_action=recommended_action,
        notes=notes
    )


def extract_keywords(theme: str, north_star: str) -> Set[str]:
    """Extract searchable keywords from wave theme and north_star"""
    text = f"{theme} {north_star}".lower()
    
    # Key terms to look for
    keywords = set()
    
    # Common feature names
    feature_terms = [
        'mission control', 'smart study router', 'ssr', 'flashcard', 'course',
        'tutor', 'quiz', 'plan', 'home', 'mode selection', 'interactive tour',
        'ai vision', 'retention', 'graduation', 'cockpit', 'homework',
        'first answer', 'wait ux', 'skeleton', 'celebration', 'recovery',
        'briefing', 'diagnostic', 'pace', 'resume', 'focus mode'
    ]
    
    for term in feature_terms:
        if term in text:
            keywords.add(term)
    
    return keywords


def classify_gap_type(wave: Wave) -> str:
    """Classify the type of gap this wave represents"""
    theme_lower = wave.theme.lower()
    north_star_lower = wave.north_star.lower()
    
    # UI/UX changes
    if any(term in theme_lower for term in ['ux', 'ui', 'polish', 'screen', 'home', 'mode selection']):
        return "ui_update"
    
    # Flow changes
    if any(term in theme_lower for term in ['flow', 'handoff', 'transition', 'routing', 'navigation']):
        return "flow_change"
    
    # New features
    if any(term in theme_lower for term in ['demo', 'new', 'foundation', 'v2', 'cockpit', 'router']):
        return "new_feature"
    
    # Default to new_feature
    return "new_feature"


def determine_coverage_status(wave: Wave, affected_scenarios: List[int], scenarios: List[Scenario]) -> str:
    """Determine if wave is not_covered, partial, or complete"""
    
    if not affected_scenarios:
        return "not_covered"
    
    # Check if any affected scenario deeply covers this wave
    for scenario_num in affected_scenarios:
        scenario = next((s for s in scenarios if s.number == scenario_num), None)
        if not scenario:
            continue
        
        # Check for deep coverage indicators
        wave_keywords = extract_keywords(wave.theme, wave.north_star)
        scenario_features = [f.lower() for f in scenario.covered_features]
        
        # If multiple keywords match, consider it complete coverage
        matches = sum(1 for kw in wave_keywords if any(kw in feat for feat in scenario_features))
        if matches >= 2:
            return "complete"
    
    return "partial"


def determine_action(coverage_status: str, gap_type: str, affected_scenarios: List[int]) -> str:
    """Determine recommended action based on coverage and gap type"""
    
    if coverage_status == "not_covered":
        return "create_new"
    elif coverage_status == "partial":
        if gap_type == "ui_update" or gap_type == "flow_change":
            return "update_existing"
        else:
            return "create_new"
    else:  # complete
        return "verify_coverage"


def generate_report(gaps: List[Gap], output_path: Path):
    """Generate gap analysis report"""
    
    # Sort gaps by priority (not_covered > partial > complete)
    priority_order = {"not_covered": 0, "partial": 1, "complete": 2}
    gaps_sorted = sorted(gaps, key=lambda g: (priority_order[g.coverage_status], g.wave_id))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GAP ANALYSIS REPORT: Closed Waves vs Scenario Coverage\n")
        f.write("=" * 80 + "\n\n")
        
        # Summary statistics
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total closed waves analyzed: {len(gaps)}\n\n")
        
        # Count by coverage status
        not_covered = [g for g in gaps if g.coverage_status == "not_covered"]
        partial = [g for g in gaps if g.coverage_status == "partial"]
        complete = [g for g in gaps if g.coverage_status == "complete"]
        
        f.write(f"Coverage Status:\n")
        f.write(f"  Not Covered: {len(not_covered)}\n")
        f.write(f"  Partial Coverage: {len(partial)}\n")
        f.write(f"  Complete Coverage: {len(complete)}\n\n")
        
        # Count by gap type
        new_features = [g for g in gaps if g.gap_type == "new_feature"]
        ui_updates = [g for g in gaps if g.gap_type == "ui_update"]
        flow_changes = [g for g in gaps if g.gap_type == "flow_change"]
        
        f.write(f"Gap Types:\n")
        f.write(f"  New Feature: {len(new_features)}\n")
        f.write(f"  UI Update: {len(ui_updates)}\n")
        f.write(f"  Flow Change: {len(flow_changes)}\n\n")
        
        # Count by recommended action
        create_new = [g for g in gaps if g.recommended_action == "create_new"]
        update_existing = [g for g in gaps if g.recommended_action == "update_existing"]
        verify = [g for g in gaps if g.recommended_action == "verify_coverage"]
        
        f.write(f"Recommended Actions:\n")
        f.write(f"  Create New Scenario: {len(create_new)}\n")
        f.write(f"  Update Existing Scenario: {len(update_existing)}\n")
        f.write(f"  Verify Coverage: {len(verify)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("DETAILED GAP ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        # Group by coverage status
        for status_name, status_gaps in [
            ("NOT COVERED", not_covered),
            ("PARTIAL COVERAGE", partial),
            ("COMPLETE COVERAGE", complete)
        ]:
            if not status_gaps:
                continue
            
            f.write(f"\n{status_name} ({len(status_gaps)} waves)\n")
            f.write("-" * 80 + "\n\n")
            
            for gap in status_gaps:
                f.write(f"Wave ID: {gap.wave_id}\n")
                f.write(f"Theme: {gap.theme}\n")
                f.write(f"North Star: {gap.north_star}\n")
                f.write(f"Entry MoT: {gap.entry_mot}\n")
                f.write(f"Exit MoT: {gap.exit_mot}\n")
                f.write(f"Gap Type: {gap.gap_type}\n")
                f.write(f"Coverage Status: {gap.coverage_status}\n")
                f.write(f"Affected Scenarios: {gap.affected_scenarios if gap.affected_scenarios else 'None'}\n")
                f.write(f"Recommended Action: {gap.recommended_action}\n")
                f.write(f"Notes: {gap.notes}\n")
                f.write("\n" + "-" * 40 + "\n\n")


def main():
    """Main execution"""
    spec_dir = Path(__file__).parent
    
    # Load data
    print("Loading closed waves...")
    waves = load_closed_waves(spec_dir / "closed_waves.json")
    print(f"Loaded {len(waves)} closed waves")
    
    print("\nParsing scenario coverage...")
    scenarios = parse_scenario_coverage(spec_dir / "scenario_coverage_report.txt")
    print(f"Parsed {len(scenarios)} scenarios")
    
    # Analyze gaps
    print("\nAnalyzing gaps...")
    gaps = []
    for wave in waves:
        gap = check_wave_coverage(wave, scenarios)
        gaps.append(gap)
    
    # Generate report
    output_path = spec_dir / "gap_analysis_report.txt"
    print(f"\nGenerating report: {output_path}")
    generate_report(gaps, output_path)
    
    print("\n✓ Gap analysis complete!")
    print(f"  - Total waves: {len(gaps)}")
    print(f"  - Not covered: {len([g for g in gaps if g.coverage_status == 'not_covered'])}")
    print(f"  - Partial coverage: {len([g for g in gaps if g.coverage_status == 'partial'])}")
    print(f"  - Complete coverage: {len([g for g in gaps if g.coverage_status == 'complete'])}")


if __name__ == "__main__":
    main()
