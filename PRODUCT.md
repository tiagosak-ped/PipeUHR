# PipeUHR — Product Definition

## Vision

PipeUHR is an engineering optimization tool for **Reversible Hydroelectric Power Plants** (Usinas Hidrelétricas Reversíveis). It migrates a legacy spreadsheet-based workflow into a modern, reproducible Python stack (NumPy, SciPy, Flask), enabling researchers and engineers to iterate on design parameters with immediate solver feedback and constraint verification.

## Core Functionalities

| Feature | Description |
|---------|-------------|
| **Parameter Input** | Structured form with grouped engineering parameters (reservoirs, operations, piping, elevations, unit costs, cavitation, constraints). |
| **Constrained Optimization** | SciPy SLSQP solver minimizes total cost (CT) subject to physical and regulatory constraints. |
| **Constraint Verification** | Post-solve simulation validates all inequality constraints and reports slack values, operator compliance, and violation counts. |
| **Results Dashboard** | Displays optimized decision variables, cost composition breakdown, and constraint satisfaction status with numeric precision. |

## How to Use

1. Launch the Flask server: `py webapp/app.py`
2. Open `http://127.0.0.1:5000` in a browser.
3. Review or adjust the engineering parameters organized by category (Reservatórios, Operação, Tubulação, Cotas, Custos unitários, Cavitação, Restrições).
4. Click **Otimizar** to execute the solver.
5. Analyze the results: total cost, decision variables, cost breakdown, and constraint verification table.

## Target Users

- **Hydraulic Engineers** designing pump-turbine systems for reversible hydroelectric plants.
- **R&D Researchers** evaluating cost sensitivity across design parameter variations.
- **Project Managers** reviewing optimization feasibility and constraint compliance for formal deliverables.

## Technical Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Solver | SciPy (SLSQP), NumPy |
| Frontend | Tailwind CSS, DaisyUI, Jinja2 templates |
| Deployment | Local development server (expandable) |

## Project Context

This software is a formal deliverable of an R&D project (P&D ANEEL). The interface must reflect institutional quality: professional, understated, and optimized for data readability by technical reviewers.
