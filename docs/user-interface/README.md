# Operator user interface

The first user interface is a local, responsive web application built on the transport-neutral application API. It requires no JavaScript build step or additional web framework.

## Start the application

Install the development requirements, then run:

```powershell
python scripts/run_web_app.py --database schedule-generator.db
```

Open `http://127.0.0.1:8765`. On a new database, use **Load demonstration school** to create a safe synthetic workspace.

## Operator workflow

1. Review configuration readiness on **Overview**.
2. Edit classes, teachers, subjects, classrooms, groups, cohorts, curriculum requirements, and availability on **School data**. Every save validates the complete dataset and creates a revision.
3. Review subject difficulty, preference weights, and rule coverage on **Rules**.
4. Choose the number of alternatives, time limit, and seed on **Generate**. Progress is refreshed while the persistent job runs, and a cancellation request is available.
5. Review the selected alternative on **Results**. Timetables can be viewed by class, teacher, or classroom alongside the quality report.

The server listens on the loopback interface by default. Binding it to another interface is not recommended until authentication and authorization are implemented in Stage 12.

## Architecture

`WebApplication.dispatch` contains route behavior independently of the HTTP server, which keeps integration tests fast. `ThreadingHTTPServer` serves static assets and JSON routes using only the Python standard library. Generation runs in a background thread with a separate SQLite connection, while the browser polls persisted progress.
