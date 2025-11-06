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


class EmployeeReliabilityRating(int, Enum):
    EXCELLENT = 10
    ACCEPTABLE = 7
    BELOW_AVERAGE = 5


class CarYardPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Employee(BaseModel):
    id: int
    name: str
    ranking: EmployeeReliabilityRating
    available_days: List[DayOfWeek]


class CarYard(BaseModel):
    id: int
    name: str
    startTime: Optional[time] = None
    priority: CarYardPriority
    min_employees: int = Field(..., ge=1)
    max_employees: int = Field(..., ge=1)
    hours_required: float = Field(
        default=1.0, ge=0.1, description="Total hours required to complete this yard. " +
        "This is divided among assigned employees (e.g., 10 hours with 2 employees = 5 hours each)")


class ScheduleRequest(BaseModel):
    employees: List[Employee]
    car_yards: List[CarYard]
    days: List[DayOfWeek]
    # Optional: groups of yard IDs that should be done together
    yard_groups: Optional[Dict[str, List[int]]] = None
    # Example: {"group1": [1, 2, 3], "group2": [4, 5]} means yards 1,2,3 often work together
    max_hours_per_day: float = Field(
        default=5.0, ge=0.5, description="Maximum hours an employee can work per day")


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

    Constraints:
    - Each yard must have min-max employees if covered
    - Every yard must be covered exactly once during the week
    - Employees can work multiple yards per day, limited by max_hours_per_day
    - Employees can only work on their available days
    - Grouping bonus encourages yards in the same group to be done together

    Objectives (in priority order):
    1. Cover high-priority yards first
    2. Use higher reliability-rated employees
    3. Encourage grouping (yards in same group done together)
    4. Balance workload across employees
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

    # Constraint 2: Limit total hours per employee per day
    # Hours per employee at a yard = hours_required / num_employees_at_yard
    # Since CP-SAT doesn't support division directly, we use constraints for each possible
    # number of employees (min_employees to max_employees) and compute hours per employee
    SCALE_FACTOR = 60  # Convert hours to minutes for integer arithmetic

    # For each yard-day combination, compute hours per employee based on number of employees
    # We'll create constraints that enforce: hours_per_employee = hours_required / employees_at_yard
    hours_per_employee = {}  # (cy_id, day) -> hours per employee in minutes

    for cy_id, cy in car_yards.items():
        for day in days:
            employees_at_yard = sum(x[(emp_id, cy_id, day)]
                                    for emp_id in employees.keys())

            # Create integer variable for hours per employee (in minutes)
            total_minutes = int(cy.hours_required * SCALE_FACTOR)
            hours_per_emp_var = model.NewIntVar(
                0, total_minutes,
                f'hours_per_emp_cy{cy_id}_d{day}')
            hours_per_employee[(cy_id, day)] = hours_per_emp_var

            # Enforce hours_per_employee calculation using constraints for each possible n
            # If employees_at_yard = n, then hours_per_emp_var = total_minutes / n
            # We use OnlyEnforceIf with indicators for each possible value

            # Create indicator boolean variables for each possible employee count
            indicators = {}
            for n in range(cy.min_employees, cy.max_employees + 1):
                indicator = model.NewBoolVar(f'count_eq_{n}_cy{cy_id}_d{day}')
                indicators[n] = indicator

                # If indicator = True, then employees_at_yard == n AND hours_per_emp_var = total_minutes / n
                hours_for_n = total_minutes // n  # Integer division
                model.Add(employees_at_yard == n).OnlyEnforceIf(indicator)
                model.Add(hours_per_emp_var ==
                          hours_for_n).OnlyEnforceIf(indicator)

            # Ensure exactly one indicator is True when covered, or all False when not covered
            # If covered, exactly one indicator must be True
            indicator_list = list(indicators.values())
            model.Add(sum(indicator_list) == 1).OnlyEnforceIf(
                covered[(cy_id, day)])
            model.Add(sum(indicator_list) == 0).OnlyEnforceIf(
                covered[(cy_id, day)].Not())

            # If not covered, hours_per_emp_var = 0
            model.Add(hours_per_emp_var == 0).OnlyEnforceIf(
                covered[(cy_id, day)].Not())

    # Now apply hours constraint per employee per day
    for emp_id in employees.keys():
        for day in days:
            # Total minutes worked = sum of hours_per_employee for yards where this employee works
            yard_contributions = []
            for cy_id in car_yards.keys():
                # Create contribution variable: hours from this yard if employee works there
                contribution = model.NewIntVar(
                    0, int(car_yards[cy_id].hours_required * SCALE_FACTOR),
                    f'contrib_e{emp_id}_cy{cy_id}_d{day}')

                # If employee works at this yard, contribution = hours_per_employee
                # If not, contribution = 0
                model.Add(contribution == hours_per_employee[(cy_id, day)]).OnlyEnforceIf(
                    x[(emp_id, cy_id, day)])
                model.Add(contribution == 0).OnlyEnforceIf(
                    x[(emp_id, cy_id, day)].Not())

                yard_contributions.append(contribution)

            # Total minutes worked must not exceed max_hours_per_day
            total_minutes_worked = model.NewIntVar(
                0, int(request.max_hours_per_day *
                       SCALE_FACTOR * len(car_yards)),
                f'total_minutes_e{emp_id}_d{day}')
            model.Add(total_minutes_worked == sum(yard_contributions))
            max_minutes = int(request.max_hours_per_day * SCALE_FACTOR)
            model.Add(total_minutes_worked <= max_minutes)

    # Constraint 2b: Optional grouping constraint - encourage yards from same group together
    # This is a soft preference (handled by bonus), but we can add a constraint to prevent
    # mixing yards from different groups if yard_groups are defined
    # (This is optional - removing it makes grouping purely preference-based via bonus)

    # Constraint 3: Every car yard must be covered exactly once during the week
    # This ensures all yards are cleaned exactly once, spread across the week
    for cy_id in car_yards.keys():
        # Sum of covered[(cy_id, day)] across all days must be exactly 1
        # This means the yard must be covered on exactly one day
        model.Add(sum(covered[(cy_id, day)] for day in days) == 1)

    # Constraint 4: Employees can only work on their available days
    for emp_id, emp in employees.items():
        for cy_id in car_yards.keys():
            for day in days:
                if day not in emp.available_days:
                    model.Add(x[(emp_id, cy_id, day)] == 0)

    # Objective 1: Prefer higher reliability-rated employees (higher rating = better)
    # EmployeeReliabilityRating: EXCELLENT=10, ACCEPTABLE=7, BELOW_AVERAGE=5
    quality_score = []
    for emp_id, emp in employees.items():
        for cy_id in car_yards.keys():
            for day in days:
                # Use the reliability rating value directly (higher is better)
                weight = emp.ranking.value
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

    # Objective 4: Grouping bonus - prefer employees working multiple yards in the same group
    # This encourages grouped yards to be done together by the same employee
    # The bonus increases with the number of yards worked in the group on the same day
    # Example: If an employee works 2 yards in a group on Monday, bonus = 2 * 50 = 100
    grouping_bonus = []
    if request.yard_groups:
        for group_name, cy_ids in request.yard_groups.items():
            for emp_id in employees.keys():
                for day in days:
                    # Count how many yards in this group the employee works on this day
                    yards_worked_in_group = sum(x[(emp_id, cy_id, day)]
                                                for cy_id in cy_ids
                                                if cy_id in car_yards.keys())
                    # Bonus increases with the number of yards worked in the group
                    # Using weight 50 as suggested - this encourages grouping but doesn't force it
                    # (works as a soft constraint via objective function)
                    grouping_bonus.append(yards_worked_in_group * 50)

    # Combined objective: prioritize high-priority yards, maximize quality, minimize workload imbalance
    # Add grouping bonus to encourage grouped yards to be done together
    objective_components = [
        # Highest priority: cover high-priority yards
        sum(priority_score) * 10000,
        sum(quality_score) * 100,     # Second: use better employees
        # Third: encourage grouping (weight 10x the base bonus)
        sum(grouping_bonus) * 10,
        # Fourth: balance workload (penalty for imbalance)
        -workload_balance * 50
    ]

    model.Maximize(sum(objective_components))

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
