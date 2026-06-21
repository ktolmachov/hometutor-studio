import pathlib

target_text = "5. Update summary counters: `coverage_groups_completed`, `coverage_packages_pass`, `coverage_packages_fail`, and `coverage_packages_stale`."
replacement_text = "5. Update summary counters: `coverage_groups_completed`, `coverage_packages_pass`, `coverage_packages_fail`, `coverage_packages_stale`, and `coverage_packages_total`."

root = pathlib.Path(".")
files = list(root.glob("doc/team_workflow/audit_groups_2026-04_cursor_ai/group_*.md"))
files.append(root / "archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md")

for file_path in files:
    if not file_path.exists():
        print(f"File not found: {file_path}")
        continue
    content = file_path.read_text(encoding="utf-8")
    if target_text in content:
        new_content = content.replace(target_text, replacement_text)
        file_path.write_text(new_content, encoding="utf-8")
        print(f"Updated: {file_path}")
    else:
        print(f"Target text not found in: {file_path}")

print("Done.")
