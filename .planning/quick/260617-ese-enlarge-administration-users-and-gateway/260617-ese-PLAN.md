# Quick Task 260617-ese: Enlarge Administration users and gateway evidence tables

Date: 2026-06-17

## Must haves

- Users and Gateway evidence tables in Administration have a wider desktop layout so words are not broken awkwardly.
- Important columns in those two tables are visually highlighted.
- Other evidence tables keep their current density and behavior.

## Tasks

1. Extend `EvidenceTable` with optional width and important-column configuration.
2. Add scoped table CSS for wider, cleaner evidence tables and highlighted cells.
3. Pass the configuration from Users and Gateway evidence views and run frontend checks.
