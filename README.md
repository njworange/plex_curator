# Plex Curator

Plex Curator is a FlaskFarm plugin scaffold for post-download Plex library curation.

## Goals

- Group duplicate versions of the same TV episode or movie after Plex indexing
- Score candidates by release group, source, resolution, codec, and filename patterns
- Support safe rollout modes: log-only, review, delete
- Keep Plex-facing integration isolated behind adapter modules

## Initial Scope

This initial version provides:

- FlaskFarm plugin skeleton
- Settings pages for Plex access, execution policy, and scoring rules
- A pure-Python filename analysis engine for duplicate grouping and scoring preview
- A result page describing the future workflow

## Planned Next Steps

1. Add Plex DB and Plex Web adapters
2. Persist analysis history and duplicate groups in plugin DB models
3. Add manual review queue
4. Add scheduled dry-run scans
5. Add optional delete or trash actions after validation
