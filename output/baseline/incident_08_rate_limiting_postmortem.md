# Incident Post-Mortem

## Executive Summary
An outage occurred where services were throwing errors. The team investigated and fixed the issue.

## Impact
Users experienced elevated error rates and slow responses.

## Timeline
- 14:00: Deployment started
- 14:05: Errors started appearing
- 14:15: Team noticed errors and began investigation
- 14:25: Fix applied and service restored

## Root Cause
The service had a database issue after the deployment. The developer forgot to verify connection limits under load.

## Contributing Factors
- High user traffic during deployment
- Insufficient monitoring alerts

## Resolution
The database configuration was changed back and service returned to normal.

## Action Items
- Monitor database more closely
- Test deployments better
