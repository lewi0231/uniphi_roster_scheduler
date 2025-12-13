# Environment Variables

This document lists all environment variables used by the roster scheduler API.

## Required Environment Variables

None - all environment variables have defaults.

## Optional Environment Variables

### `LOG_LEVEL`

- **Description**: Sets the logging level for the application
- **Default**: `"INFO"`
- **Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Usage**: Controls verbosity of application logs
- **Example**: `LOG_LEVEL=DEBUG`

### `ENVIRONMENT`

- **Description**: Environment identifier (e.g., "production", "staging", "development")
- **Default**: `"not set"`
- **Usage**: Used for logging and identification purposes only
- **Example**: `ENVIRONMENT=production`

### `SOLVER_TIMEOUT_SECONDS`

- **Description**: Maximum time (in seconds) the CP-SAT solver can run before timing out
- **Default**: `"120.0"` (120 seconds / 2 minutes)
- **Type**: Float (parsed as float)
- **Usage**: Prevents the solver from running indefinitely on complex problems
- **Example**: `SOLVER_TIMEOUT_SECONDS=180.0`

### `HOURS_OVERAGE_BUFFER_MINUTES`

- **Description**: Allowable buffer (in minutes) for employees to exceed `max_hours_per_day` before incurring a penalty
- **Default**: `"120"` (120 minutes / 2 hours)
- **Type**: Integer (parsed as int)
- **Usage**: Allows soft constraint violations for max hours per day (penalized but not forbidden)
- **Example**: `HOURS_OVERAGE_BUFFER_MINUTES=60`

## Production Configuration Recommendations

For production, consider setting:

```bash
LOG_LEVEL=INFO
ENVIRONMENT=production
SOLVER_TIMEOUT_SECONDS=120.0
HOURS_OVERAGE_BUFFER_MINUTES=120
```

## Notes

- All environment variables are optional and have sensible defaults
- Environment variables are loaded from `.env` file (if present) via `python-dotenv`
- Values are parsed at application startup
- Invalid values may cause runtime errors (e.g., non-numeric values for numeric variables)
