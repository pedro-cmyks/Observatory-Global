# GEMINI Code Assistant Context

This document provides context for the Gemini AI assistant to understand the "Observatory Global" project.

## Project Overview

**Observatory Global** is a full-stack web application designed for real-time trend and narrative tracking. It aggregates data from multiple public sources, including GDELT, Google Trends, and Wikipedia, to provide a comprehensive view of global trends.

The application consists of two main components:

*   **Backend:** A Python-based API built with the **FastAPI** framework. It is responsible for data aggregation, analysis, and serving the data to the frontend. Key Python libraries used include `pytrends` for Google Trends data, `nltk` and `scikit-learn` for natural language processing, and `h3` for hexagonal grid mapping.
*   **Frontend:** A modern, interactive user interface built with **React** and **TypeScript**. It utilizes `recharts` for data visualization, `mapbox-gl` and `deck.gl` for advanced map visualizations, and `zustand` for state management.

The entire application is containerized using **Docker** and orchestrated with **Docker Compose**, ensuring a consistent development and production environment. It is designed for deployment on **Google Cloud Run**.

## Building and Running the Project

The project includes a comprehensive `Makefile` that simplifies common development tasks.

### Key Commands

*   **Start all services:**
    ```bash
    make up
    ```
    This command builds the Docker images and starts the backend, frontend, Redis, and PostgreSQL services.
    *   Frontend is available at `http://localhost:5173`
    *   Backend is available at `http://localhost:8000`

*   **Stop all services:**
    ```bash
    make down
    ```

*   **Run tests:**
    ```bash
    make test
    ```
    This runs both backend (`pytest`) and frontend tests.

*   **Linting and Formatting:**
    *   `make lint`: Lints both backend and frontend code.
    *   `make format`: Formats the entire codebase.

For more specific commands (e.g., running only backend tests, tailing logs), refer to the `Makefile`.

## Development Conventions

*   **Dependency Management:**
    *   Backend: `poetry`
    *   Frontend: `npm`

*   **Code Style:**
    *   Backend: `black` for formatting and `ruff` for linting.
    *   Frontend: `prettier` for formatting and `eslint` for linting.

*   **Testing:**
    *   Backend: `pytest` is used for unit and integration tests.
    *   Frontend: The project is set up for testing, but specific testing frameworks are not explicitly defined in the provided context.

*   **API Documentation:**
    *   The backend API is self-documenting. Once the application is running, API documentation is available at:
        *   Swagger UI: `http://localhost:8000/docs`
        *   ReDoc: `http://localhost:8000/redoc`

*   **Database Migrations:**
    *   Database migrations are handled by `alembic`. New migrations can be created with `make migrate-create MSG="your message"` and applied with `make migrate`.
