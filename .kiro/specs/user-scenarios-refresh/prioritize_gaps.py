#!/usr/bin/env python3
"""
Gap Prioritization Script for User Scenarios Refresh

Implements priority scoring algorithm:
- MoT impact (weight 10)
- UX breakthrough keywords (weight 8)
- Cross-loop value (weight 6)

Classifies gaps as high/medium/low priority and generates prioritized list
with recommended actions.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Gap:
    wave_id: str
    theme: str
    north_star: str
    entry_mot: str
    exit_mot: str
    gap_type: str
    coverage_status: str
    affected_scenarios: List[int]
    recommended_action: str
    notes: str
    priority_score: int = 0
    priority_level: str = ""


def parse_gap_analysis_report(file_path: str) -> List[Gap]:
    """Parse the gap analysis report and extract gap data."""
    gaps = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into sections
    sections = content.split('--------------------------------------------------------------------------------')
    
    # Find the detailed analysis section
    detailed_section = None
    for i, section in enumerate(sections):
        if 'DETAILED GAP ANALYSIS' in section:
            # Get all sections after this header
            detailed_section = '--------------------------------------------------------------------------------'.join(sections[i+1:])
            break
    
    if not detailed_section:
        return gaps
    
    # Split by wave entries (each starts with "Wave ID:")
    wave_entries = re.split(r'\n\nWave ID: ', detailed_section)
    
    for entry in wave_entries:
        if not entry.strip():
            continue
        
        # Add back the "Wave ID: " prefix if it was split
        if not entry.startswith('Wave ID:'):
            entry = 'Wave ID: ' + entry
        
        # Parse fields
        wave_id_match = re.search(r'Wave ID: (.+)', entry)
        theme_match = re.search(r'Theme: (.+)', entry)
        north_star_match = re.search(r'North Star: (.+)', entry)
        entry_mot_match = re.search(r'Entry MoT: (.+)', entry)
        exit_mot_match = re.search(r'Exit MoT: (.+)', entry)
        gap_type_match = re.search(r'Gap Type: (.+)', entry)
        coverage_match = re.search(r'Coverage Status: (.+)', entry)
        affected_match = re.search(r'Affected Scenarios: (.+)', entry)
        action_match = re.search(r'Recommended Action: (.+)', entry)
        notes_match = re.search(r'Notes: (.+)', entry)
        
        if not all([wave_id_match, theme_match, north_star_match, entry_mot_match]):
            continue
        
        # Parse affected scenarios
        affected_scenarios = []
        if affected_match:
            affected_str = affected_match.group(1).strip()
            if affected_str != 'None':
                # Extract numbers from list format [1, 2, 3]
                numbers = re.findall(r'\d+', affected_str)
                affected_scenarios = [int(n) for n in numbers]
        
        gap = Gap(
            wave_id=wave_id_match.group(1).strip(),
            theme=theme_match.group(1).strip(),
            north_star=north_star_match.group(1).strip(),
            entry_mot=entry_mot_match.group(1).strip(),
            exit_mot=exit_mot_match.group(1).strip() if exit_mot_match else "",
            gap_type=gap_type_match.group(1).strip() if gap_type_match else "",
            coverage_status=coverage_match.group(1).strip() if coverage_match else "",
            affected_scenarios=affected_scenarios,
            recommended_action=action_match.group(1).strip() if action_match else "",
            notes=notes_match.group(1).strip() if notes_match else ""
        )
        
        gaps.append(gap)
    
    return gaps


def calculate_priority_score(gap: Gap) -> int:
    """
    Calculate priority score for a gap.
    
    Scoring algorithm:
    - MoT impact (weight 10): High priority for MoT #1-#3, medium for #4-#14
    - UX breakthrough keywords (weight 8): Keywords like "ux breakthrough", "wow", "mission control", "smart study router"
    - Cross-loop value (weight 6): Waves that span multiple learning loops
    - Infrastructure penalty: Exclude infrastructure-only waves unless user-visible
    """
    score = 0
    
    # MoT impact (highest weight: 10)
    entry_mot_lower = gap.entry_mot.lower()
    
    # Extract MoT number if present
    mot_number_match = re.search(r'#(\d+)', gap.entry_mot)
    if mot_number_match:
        mot_number = int(mot_number_match.group(1))
        
        # High priority MoT moments (#1-#3: Discover, First Answer, Transition to tutor)
        if mot_number in [1, 2, 3]:
            score += 10
        # Medium priority MoT moments (#4-#14)
        elif mot_number <= 14:
            score += 7
        # Lower priority for higher MoT numbers
        else:
            score += 3
    
    # UX breakthrough keywords (weight 8)
    ux_keywords = [
        "ux breakthrough", "wow", "mission control", "smart study router",
        "perceived quality", "celebration", "skeleton", "progressive reveal",
        "seamless", "motivating", "transparent"
    ]
    
    theme_lower = gap.theme.lower()
    north_star_lower = gap.north_star.lower()
    
    for keyword in ux_keywords:
        if keyword in theme_lower or keyword in north_star_lower:
            score += 8
            break  # Only add once even if multiple keywords match
    
    # Cross-loop value (weight 6)
    if gap.entry_mot == "cross-loop" or gap.exit_mot == "cross-loop":
        score += 6
    
    # Course-workspace value (medium priority)
    if "course-workspace" in gap.entry_mot or "course-workspace" in gap.exit_mot:
        score += 5
    
    # Infrastructure penalty (negative weight)
    if gap.entry_mot in ["infra", "platform"]:
        # Check if user-visible
        if "learner" not in north_star_lower and "user" not in north_star_lower:
            score -= 20  # Exclude infrastructure-only waves
    
    # Boost for already partially covered waves (easier to update than create new)
    if gap.coverage_status == "partial" and gap.recommended_action == "update_existing":
        score += 2
    
    # Boost for waves with many affected scenarios (indicates broad impact)
    if len(gap.affected_scenarios) >= 10:
        score += 3
    elif len(gap.affected_scenarios) >= 5:
        score += 1
    
    return score


def classify_priority(score: int) -> str:
    """Classify priority level based on score."""
    if score >= 15:
        return "high"
    elif score >= 8:
        return "medium"
    else:
        return "low"


def generate_prioritized_report(gaps: List[Gap], output_path: str):
    """Generate prioritized gap list with recommended actions."""
    
    # Calculate scores and classify
    for gap in gaps:
        gap.priority_score = calculate_priority_score(gap)
        gap.priority_level = classify_priority(gap.priority_score)
    
    # Sort by priority score (descending)
    gaps.sort(key=lambda g: g.priority_score, reverse=True)
    
    # Generate report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PRIORITIZED GAP ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # Summary statistics
        high_priority = [g for g in gaps if g.priority_level == "high"]
        medium_priority = [g for g in gaps if g.priority_level == "medium"]
        low_priority = [g for g in gaps if g.priority_level == "low"]
        
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total gaps analyzed: {len(gaps)}\n\n")
        f.write("Priority Distribution:\n")
        f.write(f"  High Priority: {len(high_priority)}\n")
        f.write(f"  Medium Priority: {len(medium_priority)}\n")
        f.write(f"  Low Priority: {len(low_priority)}\n\n")
        
        f.write("Recommended Actions:\n")
        create_new = [g for g in gaps if g.recommended_action == "create_new"]
        update_existing = [g for g in gaps if g.recommended_action == "update_existing"]
        verify_coverage = [g for g in gaps if g.recommended_action == "verify_coverage"]
        f.write(f"  Create New Scenario: {len(create_new)}\n")
        f.write(f"  Update Existing Scenario: {len(update_existing)}\n")
        f.write(f"  Verify Coverage: {len(verify_coverage)}\n\n")
        
        # Detailed prioritized list
        f.write("=" * 80 + "\n")
        f.write("PRIORITIZED GAP LIST\n")
        f.write("=" * 80 + "\n\n")
        
        # High priority gaps
        if high_priority:
            f.write("HIGH PRIORITY GAPS (Score >= 15)\n")
            f.write("-" * 80 + "\n\n")
            
            for gap in high_priority:
                write_gap_entry(f, gap)
        
        # Medium priority gaps
        if medium_priority:
            f.write("\n\nMEDIUM PRIORITY GAPS (Score 8-14)\n")
            f.write("-" * 80 + "\n\n")
            
            for gap in medium_priority:
                write_gap_entry(f, gap)
        
        # Low priority gaps
        if low_priority:
            f.write("\n\nLOW PRIORITY GAPS (Score < 8)\n")
            f.write("-" * 80 + "\n\n")
            
            for gap in low_priority:
                write_gap_entry(f, gap)
        
        # Implementation recommendations
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("IMPLEMENTATION RECOMMENDATIONS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Phase 1: High Priority Waves (Must Have)\n")
        f.write("-" * 80 + "\n")
        for i, gap in enumerate(high_priority, 1):
            f.write(f"{i}. {gap.wave_id}\n")
            f.write(f"   Action: {gap.recommended_action}\n")
            if gap.affected_scenarios:
                f.write(f"   Affected Scenarios: {gap.affected_scenarios}\n")
            f.write(f"   Rationale: {get_priority_rationale(gap)}\n\n")
        
        f.write("\nPhase 2: Medium Priority Waves (Should Have)\n")
        f.write("-" * 80 + "\n")
        for i, gap in enumerate(medium_priority, 1):
            f.write(f"{i}. {gap.wave_id}\n")
            f.write(f"   Action: {gap.recommended_action}\n")
            if gap.affected_scenarios:
                f.write(f"   Affected Scenarios: {gap.affected_scenarios}\n")
            f.write(f"   Rationale: {get_priority_rationale(gap)}\n\n")
        
        f.write("\nPhase 3: Low Priority Waves (Nice to Have)\n")
        f.write("-" * 80 + "\n")
        for i, gap in enumerate(low_priority, 1):
            f.write(f"{i}. {gap.wave_id}\n")
            f.write(f"   Action: {gap.recommended_action}\n")
            f.write(f"   Rationale: {get_priority_rationale(gap)}\n\n")


def write_gap_entry(f, gap: Gap):
    """Write a single gap entry to the report."""
    f.write(f"Wave ID: {gap.wave_id}\n")
    f.write(f"Priority Score: {gap.priority_score}\n")
    f.write(f"Theme: {gap.theme}\n")
    f.write(f"North Star: {gap.north_star}\n")
    f.write(f"Entry MoT: {gap.entry_mot}\n")
    f.write(f"Exit MoT: {gap.exit_mot}\n")
    f.write(f"Gap Type: {gap.gap_type}\n")
    f.write(f"Coverage Status: {gap.coverage_status}\n")
    f.write(f"Recommended Action: {gap.recommended_action}\n")
    
    if gap.affected_scenarios:
        f.write(f"Affected Scenarios: {gap.affected_scenarios}\n")
    
    f.write(f"Priority Rationale: {get_priority_rationale(gap)}\n")
    f.write(f"Notes: {gap.notes}\n")
    f.write("\n" + "-" * 40 + "\n\n")


def get_priority_rationale(gap: Gap) -> str:
    """Generate human-readable rationale for priority score."""
    reasons = []
    
    # MoT impact
    mot_number_match = re.search(r'#(\d+)', gap.entry_mot)
    if mot_number_match:
        mot_number = int(mot_number_match.group(1))
        if mot_number in [1, 2, 3]:
            reasons.append(f"Critical MoT #{mot_number}")
        elif mot_number <= 14:
            reasons.append(f"Important MoT #{mot_number}")
    
    # UX breakthrough
    ux_keywords = ["ux breakthrough", "wow", "mission control", "smart study router"]
    theme_lower = gap.theme.lower()
    north_star_lower = gap.north_star.lower()
    
    for keyword in ux_keywords:
        if keyword in theme_lower or keyword in north_star_lower:
            reasons.append(f"UX breakthrough feature")
            break
    
    # Cross-loop
    if gap.entry_mot == "cross-loop" or gap.exit_mot == "cross-loop":
        reasons.append("Cross-loop value")
    
    # Course workspace
    if "course-workspace" in gap.entry_mot or "course-workspace" in gap.exit_mot:
        reasons.append("Course learning feature")
    
    # Partial coverage
    if gap.coverage_status == "partial":
        reasons.append(f"Partially covered by {len(gap.affected_scenarios)} scenarios")
    
    # Infrastructure
    if gap.entry_mot in ["infra", "platform"]:
        reasons.append("Infrastructure wave (low user visibility)")
    
    if not reasons:
        reasons.append("Standard priority")
    
    return "; ".join(reasons)


def main():
    """Main execution function."""
    input_file = "d:\\Projects\\home-rag_v2\\.kiro\\specs\\user-scenarios-refresh\\gap_analysis_report.txt"
    output_file = "d:\\Projects\\home-rag_v2\\.kiro\\specs\\user-scenarios-refresh\\prioritized_gaps_report.txt"
    
    print("Parsing gap analysis report...")
    gaps = parse_gap_analysis_report(input_file)
    print(f"Found {len(gaps)} gaps to prioritize")
    
    print("Calculating priority scores...")
    print("Generating prioritized report...")
    generate_prioritized_report(gaps, output_file)
    
    print(f"\nPrioritized gap report generated: {output_file}")
    
    # Print summary to console
    high_priority = [g for g in gaps if classify_priority(calculate_priority_score(g)) == "high"]
    medium_priority = [g for g in gaps if classify_priority(calculate_priority_score(g)) == "medium"]
    low_priority = [g for g in gaps if classify_priority(calculate_priority_score(g)) == "low"]
    
    print(f"\nPriority Distribution:")
    print(f"  High Priority: {len(high_priority)}")
    print(f"  Medium Priority: {len(medium_priority)}")
    print(f"  Low Priority: {len(low_priority)}")


if __name__ == "__main__":
    main()
