from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Tuple
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


class EmployeeReliabilityRating(int, Enum):
    EXCELLENT = 10
    ACCEPTABLE = 7
    BELOW_AVERAGE = 5


class CarYardPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CarYardRegion(str, Enum):
    NORTH = "north"
    CENTRAL = "central"
    SOUTH = "south"


class Employee(BaseModel):
    id: int
    name: str
    ranking: EmployeeReliabilityRating
    available_days: List[DayOfWeek]
    not_region: Optional[CarYardRegion] = None


class CarYard(BaseModel):
    id: int
    name: str
    startTime: Optional[time] = None
    priority: CarYardPriority
    region: CarYardRegion
    required_days: Optional[List[DayOfWeek]] = None
    # (linked yard id, minimum gap in days between visits to the yards)
    linked_yard: Optional[Tuple[int, int]] = None
    per_week: Optional[Tuple[int, int]] = None
    min_employees: int = Field(..., ge=1,
                               description="The absolute minimum number of workers required")
    max_employees: int = Field(..., ge=1,
                               description="The absolute max number of employees")
    hours_required: float = Field(
        default=2.0, ge=1.0, description="Total hours required to complete this yard. " +
        "This is divided among assigned employees (e.g., 10 hours with 2 employees = 5 hours each)")


class ScheduleRequest(BaseModel):
    employees: List[Employee]
    car_yards: List[CarYard]
    days: List[DayOfWeek]
    # Optional: groups of yard IDs that should be done together
    yard_groups: Optional[Dict[str, List[int]]] = None
    # Example: {"group1": [1, 2, 3], "group2": [4, 5]} means yards 1,2,3 often work together
    max_hours_per_day: float = Field(
        default=7.0, ge=3, description="Maximum hours an employee can work per day")


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
    - Yards respect required days, visit counts, spacing rules, and linked-yard gaps
    - Employees can work multiple yards per day, limited by max_hours_per_day
    - Employees can only work on available days and avoid excluded regions
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

    day_index = {day: idx for idx, day in enumerate(days)}
    coverage_requirements: Dict[int, Tuple[int, int]] = {}
    link_pairs: Dict[Tuple[int, int], int] = {}

    # Restrict assignments to allowed days and collect visit requirements
    for cy_id, cy in car_yards.items():
        allowed_days = set(cy.required_days) if cy.required_days else set(days)
        for day in days:
            if day not in allowed_days:
                model.Add(covered[(cy_id, day)] == 0)
                for emp_id in employees.keys():
                    model.Add(x[(emp_id, cy_id, day)] == 0)

        if cy.per_week:
            visits_required, min_gap = cy.per_week
        else:
            visits_required, min_gap = (1, 0)
        coverage_requirements[cy_id] = (visits_required, min_gap)

        if cy.linked_yard:
            linked_id, gap_days = cy.linked_yard
            if linked_id in car_yards:
                if gap_days < 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Linked yard gap must be non-negative between {cy_id} and {linked_id}."
                    )
                if visits_required > 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Linked yard {cy_id} cannot require more than one visit per week."
                    )
                key = tuple(sorted((cy_id, linked_id)))
                if key in link_pairs and link_pairs[key] != gap_days:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Conflicting linked yard gaps between {cy_id} and {linked_id}."
                    )
                link_pairs[key] = gap_days

    # Ensure linked yards have compatible visit counts
    for (source_id, target_id), gap in link_pairs.items():
        if target_id in coverage_requirements:
            target_visits, _ = coverage_requirements[target_id]
            if target_visits > 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Linked yard {target_id} cannot require more than one visit per week."
                )

    # Employees may have region exclusions
    for emp_id, emp in employees.items():
        if emp.not_region:
            for cy_id, cy in car_yards.items():
                if cy.region == emp.not_region:
                    for day in days:
                        model.Add(x[(emp_id, cy_id, day)] == 0)

    # Constraint 1 (UPDATED): If a yard is covered, it must have between min and max employees
    # If not covered, it has 0 employees
    extra_employee_penalties = []
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

            extra_employee_penalties.append(
                employees_at_yard - cy.min_employees * covered[(cy_id, day)]
            )

    # Constraint 2: Limit total hours per employee per day
    # Distribute total yard hours across assigned employees while respecting per-employee limits
    SCALE_FACTOR = 60  # Convert hours to minutes for integer arithmetic
    work_minutes: Dict[Tuple[int, int, DayOfWeek], cp_model.IntVar] = {}
    employee_day_minutes: Dict[Tuple[int, DayOfWeek], cp_model.IntVar] = {}
    for cy_id, cy in car_yards.items():
        total_minutes = int(cy.hours_required * SCALE_FACTOR)
        for day in days:
            work_vars = []
            for emp_id in employees.keys():
                work_var = model.NewIntVar(
                    0, total_minutes,
                    f'work_e{emp_id}_cy{cy_id}_d{day}')
                work_minutes[(emp_id, cy_id, day)] = work_var
                model.Add(work_var == 0).OnlyEnforceIf(
                    x[(emp_id, cy_id, day)].Not())
                model.Add(work_var <= total_minutes).OnlyEnforceIf(
                    x[(emp_id, cy_id, day)])
                work_vars.append(work_var)

            total_work = sum(work_vars)
            model.Add(total_work == total_minutes).OnlyEnforceIf(
                covered[(cy_id, day)])
            model.Add(total_work == 0).OnlyEnforceIf(
                covered[(cy_id, day)].Not())

    # Now apply hours constraint per employee per day using distributed minutes
    for emp_id in employees.keys():
        for day in days:
            total_minutes_worked = model.NewIntVar(
                0, int(request.max_hours_per_day *
                       SCALE_FACTOR * len(car_yards)),
                f'total_minutes_e{emp_id}_d{day}')
            employee_day_minutes[(emp_id, day)] = total_minutes_worked
            model.Add(total_minutes_worked == sum(
                work_minutes[(emp_id, cy_id, day)] for cy_id in car_yards.keys()))
            max_minutes = int(request.max_hours_per_day * SCALE_FACTOR)
            model.Add(total_minutes_worked <= max_minutes)

    # Constraint 2b: Optional grouping constraint - encourage yards from same group together
    # This is a soft preference (handled by bonus), but we can add a constraint to prevent
    # mixing yards from different groups if yard_groups are defined
    # (This is optional - removing it makes grouping purely preference-based via bonus)

    # Constraint 3: Car yard visit frequency and spacing (per_week)
    linked_yard_ids = {cy for pair in link_pairs.keys() for cy in pair}

    for cy_id, cy in car_yards.items():
        required_visits, min_gap = coverage_requirements[cy_id]
        coverage_vars = [covered[(cy_id, day)] for day in days]
        is_linked = cy_id in linked_yard_ids

        # Mandate exact coverage when the yard has explicit frequency requirements
        # (per-week visits or explicitly required days). Otherwise, allow the solver
        # to skip visits if resources are tight, letting priorities drive decisions.
        requires_exact_coverage = (
            not is_linked and (bool(cy.per_week) or bool(cy.required_days))
        )
        if requires_exact_coverage:
            model.Add(sum(coverage_vars) == required_visits)
        elif not is_linked:
            model.Add(sum(coverage_vars) <= required_visits)

        if is_linked:
            if cy.required_days and len(cy.required_days) > 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Linked yard {cy_id} cannot have multiple required days."
                )
            model.Add(sum(coverage_vars) == 1)

        if required_visits > 1 and min_gap > 0:
            for i in range(len(days)):
                for j in range(i + 1, len(days)):
                    if day_index[days[j]] - day_index[days[i]] < min_gap:
                        model.AddBoolOr([
                            coverage_vars[i].Not(),
                            coverage_vars[j].Not()
                        ])

    # Constraint 4: Linked yards must be within the specified gap
    for (source_id, target_id), gap_days in link_pairs.items():
        if source_id not in car_yards or target_id not in car_yards:
            continue

        if gap_days <= 0:
            for day in days:
                model.Add(covered[(source_id, day)] ==
                          covered[(target_id, day)])
            continue

        for day_a in days:
            for day_b in days:
                diff = abs(day_index[day_a] - day_index[day_b])
                if diff < gap_days:
                    model.AddBoolOr([
                        covered[(source_id, day_a)].Not(),
                        covered[(target_id, day_b)].Not()
                    ])

    # Constraint 5: Employees can only work on their available days
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
    total_assignments = sum(
        x[(emp_id, cy_id, day)]
        for emp_id in employees.keys()
        for cy_id in car_yards.keys()
        for day in days
    )

    EXTRA_EMPLOYEE_PENALTY_WEIGHT = 2000

    objective_components = [
        # Highest priority: cover high-priority yards
        sum(priority_score) * 10000,
        sum(quality_score) * 100,     # Second: use better employees
        # Third: encourage grouping (weight 10x the base bonus)
        sum(grouping_bonus) * 10,
        # Fourth: balance workload (penalty for imbalance)
        -workload_balance * 50,
        # Discourage assigning more employees than necessary
        -sum(extra_employee_penalties) * EXTRA_EMPLOYEE_PENALTY_WEIGHT,
        # Mild penalty on total assignments to avoid redundant coverage
        -total_assignments * 10
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

        if not assignments:
            raise HTTPException(
                status_code=400,
                detail="No feasible assignments produced. Check availability, required days, or coverage limits."
            )

        # Calculate stats
        shifts_count = {emp_id: 0 for emp_id in employees.keys()}
        yards_covered = {}  # Track which yards were covered
        for assignment in assignments:
            shifts_count[assignment.employee_id] += 1
            key = (assignment.car_yard_id, assignment.day)
            if key not in yards_covered:
                yards_covered[key] = 0
            yards_covered[key] += 1

        hours_per_employee_day = {
            f"emp_{emp_id}_day_{day.value}":
            solver.Value(minutes_var) / SCALE_FACTOR
            for (emp_id, day), minutes_var in employee_day_minutes.items()
        }

        return ScheduleResponse(
            status="optimal" if status == cp_model.OPTIMAL else "feasible",
            assignments=assignments,
            stats={
                "total_assignments": len(assignments),
                "shifts_per_employee": shifts_count,
                "yards_covered": {f"yard_{cy_id}_day_{day.value}": count
                                  for (cy_id, day), count in yards_covered.items()},
                "hours_per_employee_day": hours_per_employee_day,
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
