from datetime import date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from ortools.sat.python import cp_model
from datetime import time
from enum import Enum

api = FastAPI(title="Car Yard Rostering API", version="1.0.0")


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class CarYardPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Employee(BaseModel):
    id: int
    name: str
    ranking: int = Field(..., ge=1, description="1=best, higher=worse")
    available_days: List[DayOfWeek]


class CarYard(BaseModel):
    id: int
    name: str
    startTime: Optional[time] = None
    priority: CarYardPriority
    min_employees: int = Field(..., ge=1)
    max_employees: int = Field(..., ge=1)


class ScheduleRequest(BaseModel):
    employees: List[Employee]
    car_yards: List[CarYard]
    days: List[DayOfWeek]


class Assignment(BaseModel):
    employee_id: int
    employee_name: str
    car_yard_id: int
    car_yard_name: str
    day: DayOfWeek


class ScheduleResponse(BaseModel):
    status: str
    assignments: List[Assignment]
    stats: Dict[str, Any]


def solve_roster(request: ScheduleRequest) -> ScheduleResponse:
    """
    Solve the rostering problem using OR-Tools CP-SAT solver
    Priority-based: Higher priority car yards get staffed first when employees are limited
    """
    model = cp_model.CpModel()

    # Create indices
    employees = {emp.id: emp for emp in request.employees}
    car_yards = {cy.id: cy for cy in request.car_yards}
    days = request.days

    # Decision variables: x[e][cy][d] = 1 if employee e works at car_yard cy on day d
    x = {}
    for emp_id in employees.keys():
        for cy_id in car_yards.keys():
            for day in days:
                x[(emp_id, cy_id, day)] = model.NewBoolVar(
                    f'x_e{emp_id}_cy{cy_id}_{day}')

    # NEW: Decision variable for whether a yard is covered on a day
    # covered[cy][d] = 1 if car_yard cy is covered (has at least min_employees) on day d
    covered = {}
    for cy_id in car_yards.keys():
        for day in days:
            covered[(cy_id, day)] = model.NewBoolVar(
                f'covered_cy{cy_id}_{day}')

    # Constraint 1 (UPDATED): If a yard is covered, it must have between min and max employees
    # If not covered, it has 0 employees
    for cy_id, cy in car_yards.items():
        for day in days:
            employees_at_yard = sum(x[(emp_id, cy_id, day)]
                                    for emp_id in employees.keys())

            # If covered = 1, then employees_at_yard >= min_employees
            # If covered = 0, then employees_at_yard >= 0 (always true)
            model.Add(employees_at_yard >= cy.min_employees *
                      covered[(cy_id, day)])

            # If covered = 1, then employees_at_yard <= max_employees
            # If covered = 0, then employees_at_yard <= 0 (forces 0 employees)
            model.Add(employees_at_yard <= cy.max_employees *
                      covered[(cy_id, day)])

    # Constraint 2: Each employee works at most one car yard per day
    for emp_id in employees.keys():
        for day in days:
            model.Add(sum(x[(emp_id, cy_id, day)]
                      for cy_id in car_yards.keys()) <= 1)

    # Constraint 3: Employees can only work on their available days
    for emp_id, emp in employees.items():
        for cy_id in car_yards.keys():
            for day in days:
                if day not in emp.available_days:
                    model.Add(x[(emp_id, cy_id, day)] == 0)

    # Objective 1: Prefer higher-ranked employees (lower ranking number = better)
    quality_score = []
    for emp_id, emp in employees.items():
        for cy_id in car_yards.keys():
            for day in days:
                weight = len(employees) - emp.ranking + 1
                quality_score.append(x[(emp_id, cy_id, day)] * weight)

    # NEW Objective 2: Prioritize high-priority car yards
    # Give higher weight to covering high-priority yards
    priority_weights = {
        CarYardPriority.HIGH: 1000,
        CarYardPriority.MEDIUM: 100,
        CarYardPriority.LOW: 10
    }
    priority_score = []
    for cy_id, cy in car_yards.items():
        for day in days:
            weight = priority_weights.get(cy.priority, 1)
            priority_score.append(covered[(cy_id, day)] * weight)

    # Objective 3: Balance workload - minimize difference between max and min shifts
    shifts_per_employee = []
    for emp_id in employees.keys():
        total = sum(x[(emp_id, cy_id, day)]
                    for cy_id in car_yards.keys()
                    for day in days)
        shifts_per_employee.append(total)

    min_shifts = model.NewIntVar(0, len(days) * len(car_yards), 'min_shifts')
    max_shifts = model.NewIntVar(0, len(days) * len(car_yards), 'max_shifts')

    for total in shifts_per_employee:
        model.Add(min_shifts <= total)
        model.Add(max_shifts >= total)

    workload_balance = max_shifts - min_shifts

    # Combined objective: prioritize high-priority yards, maximize quality, minimize workload imbalance
    model.Maximize(
        # Highest priority: cover high-priority yards
        sum(priority_score) * 10000 +
        sum(quality_score) * 100 -         # Second: use better employees
        # Third: balance workload (increased weight)
        workload_balance * 50
    )

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    # Build response (same as before)
    assignments = []
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for emp_id, emp in employees.items():
            for cy_id, cy in car_yards.items():
                for day in days:
                    if solver.Value(x[(emp_id, cy_id, day)]) == 1:
                        assignments.append(Assignment(
                            employee_id=emp_id,
                            employee_name=emp.name,
                            car_yard_id=cy_id,
                            car_yard_name=cy.name,
                            day=day
                        ))

        # Calculate stats
        shifts_count = {emp_id: 0 for emp_id in employees.keys()}
        yards_covered = {}  # Track which yards were covered
        for assignment in assignments:
            shifts_count[assignment.employee_id] += 1
            key = (assignment.car_yard_id, assignment.day)
            if key not in yards_covered:
                yards_covered[key] = 0
            yards_covered[key] += 1

        return ScheduleResponse(
            status="optimal" if status == cp_model.OPTIMAL else "feasible",
            assignments=assignments,
            stats={
                "total_assignments": len(assignments),
                "shifts_per_employee": shifts_count,
                "yards_covered": {f"yard_{cy_id}_day_{day.value}": count
                                  for (cy_id, day), count in yards_covered.items()},
                "solve_time_seconds": solver.WallTime()
            }
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="No feasible solution found. Check constraints (availability, min/max employees per yard)"
        )


@api.post("/api/v1/roster", response_model=ScheduleResponse)
async def generate_roster(request: ScheduleRequest):
    """
    Generate an optimal roster for car yard cleaning
    """
    return solve_roster(request)


@api.get("/")
async def root():
    return {
        "message": "Car Yard Rostering API",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8888)
