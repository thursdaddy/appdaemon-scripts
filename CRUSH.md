# CRUSH.md

## Build/Lint/Test Commands

- **No explicit build or test commands found.** AppDaemon scripts are typically run directly by the AppDaemon server.
- **Linting:** For Python, `ruff check .` is a common and recommended linter.
- **Type Checking:** For Python, `mypy .` is a common and recommended type checker.

## Code Style Guidelines

### Imports
- Imports should be grouped: standard library, third-party, then local application-specific imports.
- Imports should be absolute from the project root where possible.

### Formatting
- Follow PEP 8 guidelines.
- Use 4 spaces for indentation.
- Maximum line length of 90 characters.

### Naming Conventions
- Variables and functions: `snake_case` (e.g., `tv_consumption_entity`, `turn_on_lights`).
- Classes: `PascalCase` (e.g., `TvLights`, `MotionRGBLight`).
- Constants: `UPPER_SNAKE_CASE` (though not explicitly used in provided examples).
- Private-like attributes: prefix with a single underscore (e.g., `_motion_sensor`).

### Types
- Type hints are not consistently used in the provided examples, but their use is encouraged for better code clarity and maintainability.

### Error Handling
- Use `try...except` blocks for handling potential runtime errors, especially when dealing with external data (e.g., `json.JSONDecodeError`, `ValueError`, `TypeError`).
- Log errors using `self.log()` for AppDaemon applications.

### General
- Docstrings should be used for classes and complex functions.
- Comments should explain *why* something is done, not *what* is done.
- Prefer f-strings for string formatting.
