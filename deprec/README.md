# Deprecated Files

This directory contains files that are no longer actively used in the REanna Router application but are kept for reference or historical purposes.

## Contents

- `mainv2.py` - Original single-file implementation of the REanna Router application.
  - This was the initial implementation with all functionality contained in a single file.
  - The functionality has been replaced by the modular architecture in the `app/` directory.
  - A backward compatibility endpoint `/optimize` is maintained in `app/main.py` to support legacy integrations.

## Integration with Current System

The current implementation in `main.py` (which loads the modular FastAPI application from `app/main.py`) maintains backward compatibility with scripts that were designed for the original implementation:

1. `test.py` - Uses the `/optimize` endpoint which is still supported by the compatibility layer
2. `benchmark.py` - Runs `test.py` to benchmark performance

If you need to adapt existing code that uses the deprecated API:

- Use the modular endpoints in the new API where possible (`/tours/`, `/property-visits/`, etc.)
- For backward compatibility, the `/optimize` endpoint is still available but consider migrating to the new endpoints for new development
