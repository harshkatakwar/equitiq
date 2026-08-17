# ResearchOS — Data Licensing

## Licensing Registry Schema

Every data source has a licensing record:

```
provider              — Source provider name
dataset               — Dataset identifier
licence_type          — free / official / commercial / internal
internal_use_allowed  — Can store and process internally
display_allowed       — Can show to end users
derived_data_allowed  — Can create derived metrics
redistribution_allowed — Can redistribute raw data
export_allowed        — Can offer CSV/API export
api_delivery_allowed  — Can serve via API
ai_processing_allowed — Can use as AI input
ai_training_allowed   — Can use for model training
document_retention_allowed — Can retain documents permanently
allowed_channels      — web / api / mobile
allowed_regions       — Jurisdictional restrictions
contract_start        — Licence effective date
contract_expiry       — Licence expiry date
attribution_required  — Must show source attribution
terms_url             — Link to terms of use
notes                 — Additional restrictions
```

## Rights Hierarchy

```
Can retrieve   → Permission to fetch from source
Can store      → Permission to persist in our database
Can process    → Permission to compute derived values
Can display    → Permission to show to users
Can export     → Permission to offer downloads
Can redistribute → Permission to serve via API to third parties
```

Each level requires all previous levels.

## Enforcement Points

1. **Ingestion**: Check `internal_use_allowed` before storing
2. **API responses**: Check `api_delivery_allowed` before serving
3. **Display**: Check `display_allowed` and add attribution if required
4. **Export**: Check `export_allowed` before generating CSV/downloads
5. **AI processing**: Check `ai_processing_allowed` before sending to AI
6. **Retention**: Check `document_retention_allowed` for cleanup schedules

## Demo Mode Licensing

All demo data has unrestricted internal licensing:
- All rights enabled
- No attribution required (self-generated)
- No expiry

## Expiry Monitoring

- Admin dashboard shows contracts expiring within 30 days
- System logs warning when serving data from expired licences
- Automated disable after configurable grace period
