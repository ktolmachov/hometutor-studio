#!/usr/bin/env python3
"""
Parse backlog_registry.yaml and extract closed waves for user scenarios refresh.

This script implements Task 1 of the user-scenarios-refresh spec:
- Parse doc/backlog_registry.yaml to extract all waves with status: completed
- Create structured data model for waves
- Filter out infrastructure-only waves unless they have user-visible impact
- Generate initial list of closed waves for analysis
"""

import yaml
from dataclasses import dataclass, asdict
from typing import List, Optional
import json
from pathlib import Path


@dataclass
class Wave:
    """Structured data model for a wave from backlog_registry.yaml"""
    id: str
    theme: str
    north_star: str
    entry_mot: str
    exit_mot: str
    packages: List[str]
    status: str
    created: str
    last_touched_mot: Optional[str] = None
    kill_switch: Optional[str] = None


def is_infrastructure_only(wave: Wave) -> bool:
    """
    Determine if a wave is infrastructure-only without user-visible impact.
    
    Filter criteria from requirements 1.6:
    - entry_mot == "infra" or "platform" 
    - UNLESS north_star mentions user-visible impact (learner, user, etc.)
    """
    infra_keywords = ["infra", "platform"]
    
    # Check if entry_mot indicates infrastructure
    if wave.entry_mot.lower() in infra_keywords:
        # Check if north_star has user-visible impact
        user_visible_keywords = ["learner", "user", "студент", "пользователь"]
        north_star_lower = wave.north_star.lower()
        
        # If north_star mentions users, it has user-visible impact
        if any(keyword in north_star_lower for keyword in user_visible_keywords):
            return False
        
        # Otherwise, it's infrastructure-only
        return True
    
    return False


def parse_backlog_registry(file_path: str) -> List[Wave]:
    """
    Parse backlog_registry.yaml and extract all waves with status: completed.
    
    Returns:
        List of Wave objects for closed waves (excluding infrastructure-only)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    waves_data = data.get('waves', [])
    closed_waves = []
    
    for wave_data in waves_data:
        # Extract wave fields
        wave = Wave(
            id=wave_data.get('id', ''),
            theme=wave_data.get('theme', ''),
            north_star=wave_data.get('north_star', ''),
            entry_mot=wave_data.get('entry_mot', ''),
            exit_mot=wave_data.get('exit_mot', ''),
            packages=wave_data.get('packages', []),
            status=wave_data.get('status', ''),
            created=wave_data.get('created', ''),
            last_touched_mot=wave_data.get('last_touched_mot'),
            kill_switch=wave_data.get('kill_switch')
        )
        
        # Filter: only completed waves
        if wave.status == 'completed':
            # Filter out infrastructure-only waves
            if not is_infrastructure_only(wave):
                closed_waves.append(wave)
    
    return closed_waves


def main():
    """Main entry point for the script."""
    registry_path = Path(__file__).parent.parent / 'doc' / 'backlog_registry.yaml'
    
    print(f"Parsing {registry_path}...")
    closed_waves = parse_backlog_registry(str(registry_path))
    
    print(f"\nFound {len(closed_waves)} closed waves with user-visible impact:\n")
    
    # Print summary
    for wave in closed_waves:
        print(f"  - {wave.id}")
        print(f"    Theme: {wave.theme}")
        print(f"    North Star: {wave.north_star}")
        print(f"    Entry MoT: {wave.entry_mot}")
        print(f"    Exit MoT: {wave.exit_mot}")
        print(f"    Packages: {len(wave.packages)}")
        print()
    
    # Save to JSON for further analysis
    output_path = Path(__file__).parent.parent / '.kiro' / 'specs' / 'user-scenarios-refresh' / 'closed_waves.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert waves to dict and handle date serialization
    waves_data = []
    for wave in closed_waves:
        wave_dict = asdict(wave)
        # Convert date to string if needed
        if hasattr(wave_dict['created'], 'isoformat'):
            wave_dict['created'] = wave_dict['created'].isoformat()
        waves_data.append(wave_dict)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(waves_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved closed waves data to {output_path}")
    print(f"\nSummary:")
    print(f"  Total closed waves: {len(closed_waves)}")
    
    # Count by entry_mot
    mot_counts = {}
    for wave in closed_waves:
        mot = wave.entry_mot
        mot_counts[mot] = mot_counts.get(mot, 0) + 1
    
    print(f"\nBreakdown by entry MoT:")
    for mot, count in sorted(mot_counts.items()):
        print(f"  {mot}: {count} waves")


if __name__ == '__main__':
    main()
