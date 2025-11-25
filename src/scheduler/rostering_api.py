import platform
import sys
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, computed_field, ValidationError
from typing import List, Dict, Optional, Any, Tuple
from ortools.sat.python import cp_model
from datetime import time, datetime, timedelta
from enum import Enum
import logging
import os
import re
import json
import traceback

# Load environment variables from .env file
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

api = FastAPI(title="Car Yard Rostering API", version="1.0.0")

# Log environment info on startup
logger.info(f"Python version: {sys.version}")
logger.info(f"Platform: {platform.platform()}")
logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'not set')}")
logger.info(f"Log level: {LOG_LEVEL}")

# Log OR-Tools version if available
try:
    import ortools
    logger.info(f"OR-Tools version: {ortools.__version__}")
except:
    logger.warning("Could not determine OR-Tools version")


# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url.path}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(
            f"Content-Type: {request.headers.get('content-type', 'not set')}")
        logger.debug(
            f"Content-Length: {request.headers.get('content-length', 'not set')}")

        response = await call_next(request)
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url.path}")
        return response


api.add_middleware(RequestLoggingMiddleware)


# Exception handler for validation errors
@api.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.error(f"Pydantic ValidationError: {exc}")
    logger.debug(f"ValidationError details: {exc.errors()}")
    logger.debug(f"Request path: {request.url.path}")
    logger.debug(f"Request method: {request.method}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": f"Validation error: {str(exc)}",
            "errors": exc.errors()
        }
    )


# Exception handler for HTTP exceptions
@api.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail}")
    logger.debug(f"Request path: {request.url.path}")
    logger.debug(f"Request method: {request.method}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


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


class Employee(BaseModel):
    id: int
    name: str
    ranking: EmployeeReliabilityRating
    available_days: List[DayOfWeek]
    excluded_yards: List[int] = Field(default_factory=list)


class CarYard(BaseModel):
    id: int
    name: str
    startTime: Optional[time] = None
    priority: CarYardPriority
    north_south_position: int
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
    earliest_start_time: Optional[time] = Field(
        default=None,
        description="Earliest allowable start time for any yard unless overridden by the yard's startTime."
    )
    travel_buffer_minutes: int = Field(
        default=30,
        ge=0,
        description="Minimum buffer between consecutive yards for the same day (travel time)."
    )
    max_radius: int = Field(..., ge=0,
                            description="Maximum position difference between yards that can be scheduled same day")


class Assignment(BaseModel):
    employee_id: int
    employee_name: str
    car_yard_id: int
    car_yard_name: str
    day: DayOfWeek
    start_time: str
    finish_time: str


class YardSchedule(BaseModel):
    car_yard_id: int
    car_yard_name: str
    workers: List[str]
    start_time: str
    finish_time: str


class DayRoster(BaseModel):
    day: DayOfWeek
    yards: List[YardSchedule]


class RosterStructure(BaseModel):
    days: List[DayRoster]


class YardTimeblock(BaseModel):
    """Timeblock for a yard on a specific day with employee assignments"""
    car_yard_id: int
    car_yard_name: str
    day: str  # Day of week as string (e.g., "monday")
    start_time: str  # ISO format time (e.g., "06:00")
    finish_time: str  # ISO format time (e.g., "14:00")
    employees: List[int]  # List of employee IDs
    minutes_per_employee: float
    per_employee_hours: float


class ScheduleStats(BaseModel):
    """Statistics about the generated schedule"""
    total_assignments: int
    shifts_per_employee: Dict[int, int]  # employee_id -> number of shifts
    # "yard_{cy_id}_day_{day.value}" -> number of employees
    yards_covered: Dict[str, int]
    # "emp_{emp_id}_day_{day.value}" -> hours worked
    hours_per_employee_day: Dict[str, float]
    yard_timeblocks: List[YardTimeblock]
    solve_time_seconds: float

    @computed_field
    @property
    def employee_hours_by_day(self) -> Dict[str, Dict[int, float]]:
        """
        Reorganized hours data grouped by day for easy frontend access.
        Makes it easy to get all employees' hours for a specific day.

        Returns:
            Dict[str, Dict[int, float]]: day -> {employee_id: hours}
            Example: {"monday": {1: 4.5, 2: 3.0}, "tuesday": {1: 2.0}}

        Usage:
            # Get all employees' hours for Monday
            monday_hours = stats.employee_hours_by_day["monday"]
            # Returns: {1: 4.5, 2: 3.0}

            # Get a specific employee's hours for Monday
            employee_1_monday = stats.employee_hours_by_day["monday"].get(1, 0.0)
        """
        result: Dict[str, Dict[int, float]] = {}

        # Parse keys like "emp_1_day_monday" to extract employee_id and day
        # Pattern: "emp_{employee_id}_day_{day}"
        pattern = r"emp_(\d+)_day_([a-z]+)"

        for key, hours in self.hours_per_employee_day.items():
            match = re.match(pattern, key)
            if match:
                employee_id = int(match.group(1))
                day = match.group(2)

                if day not in result:
                    result[day] = {}
                result[day][employee_id] = hours

        return result

    @computed_field
    @property
    def hours_by_employee(self) -> Dict[int, Dict[str, float]]:
        """
        Reorganized hours data grouped by employee for easy access.
        Makes it easy to get all days' hours for a specific employee.

        Returns:
            Dict[int, Dict[str, float]]: employee_id -> {day: hours}
            Example: {1: {"monday": 4.5, "tuesday": 2.0}, 2: {"monday": 3.0}}

        Usage:
            # Get all days' hours for employee 1
            employee_1_hours = stats.hours_by_employee[1]
            # Returns: {"monday": 4.5, "tuesday": 2.0}

            # Get employee 1's hours for Monday
            employee_1_monday = stats.hours_by_employee[1].get("monday", 0.0)
        """
        result: Dict[int, Dict[str, float]] = {}

        # Parse keys like "emp_1_day_monday" to extract employee_id and day
        pattern = r"emp_(\d+)_day_([a-z]+)"

        for key, hours in self.hours_per_employee_day.items():
            match = re.match(pattern, key)
            if match:
                employee_id = int(match.group(1))
                day = match.group(2)

                if employee_id not in result:
                    result[employee_id] = {}
                result[employee_id][day] = hours

        return result

    @computed_field
    @property
    def employee_total_hours(self) -> Dict[int, float]:
        """
        Total hours worked by each employee across all days.
        Useful for summary views and workload analysis.

        Returns:
            Dict[int, float]: employee_id -> total hours
            Example: {1: 6.5, 2: 3.0}

        Usage:
            # Get total hours for employee 1
            total = stats.employee_total_hours[1]
            # Returns: 6.5
        """
        result: Dict[int, float] = {}

        pattern = r"emp_(\d+)_day_([a-z]+)"

        for key, hours in self.hours_per_employee_day.items():
            match = re.match(pattern, key)
            if match:
                employee_id = int(match.group(1))
                result[employee_id] = result.get(employee_id, 0.0) + hours

        return result


class ScheduleResponse(BaseModel):
    status: str
    assignments: List[Assignment]
    roster: RosterStructure
    stats: ScheduleStats


# Objective function weights (constants)
OBJECTIVE_PRIORITY_WEIGHT = 10000
OBJECTIVE_QUALITY_WEIGHT = 10
OBJECTIVE_GROUPING_WEIGHT = 10
OBJECTIVE_BALANCE_WEIGHT = 100  # previously was set at 50
OBJECTIVE_EXTRA_EMPLOYEE_WEIGHT = 2000
OBJECTIVE_PARTIAL_OVERLAP_WEIGHT = 2000
OBJECTIVE_ASSIGNMENT_PENALTY = 10

# Priority weights for yard coverage
PRIORITY_WEIGHT_HIGH = 1000
PRIORITY_WEIGHT_MEDIUM = 100
PRIORITY_WEIGHT_LOW = 10

# Grouping bonus base weight
GROUPING_BONUS_BASE_WEIGHT = 50

# Solver configuration
# Solver timeout - can be overridden via SOLVER_TIMEOUT_SECONDS environment variable
DEFAULT_SOLVER_TIMEOUT_SECONDS = float(
    os.getenv("SOLVER_TIMEOUT_SECONDS", "30.0"))

# Time constants
DEFAULT_EARLIEST_START_HOUR = 6
DEFAULT_EARLIEST_START_MINUTE = 0
MINUTES_PER_HOUR = 60

# Floating point tolerance
FLOATING_POINT_TOLERANCE = 1e-6

# Default priority rank for sorting (used when priority not found)
DEFAULT_PRIORITY_RANK = 3


def _create_partial_overlap_penalty(
    model: cp_model.CpModel,
    employees: Dict[int, Employee],
    cy_a: int,
    cy_b: int,
    day: DayOfWeek,
    x: Dict[Tuple[int, int, DayOfWeek], cp_model.IntVar]
) -> cp_model.IntVar:
    """
    Create penalty variable for partial crew overlap between two yards on the same day.

    Penalty is 1 if some employees work both yards AND some employees join mid-day
    (i.e., work yard B but not yard A). This discourages crews from splitting/merging
    mid-day, preferring intact crews that stay together.

    Args:
        model: The CP-SAT model
        employees: Dictionary of employees by ID
        cy_a: First car yard ID
        cy_b: Second car yard ID
        day: Day of week
        x: Decision variables x[(emp_id, cy_id, day)]

    Returns:
        A boolean variable that is 1 if partial overlap occurs (penalty case)
    """
    shared_vars = []
    joiner_vars = []

    for emp_id in employees.keys():
        # shared_var = 1 if employee works both yards
        shared_var = model.NewBoolVar(
            f'shared_e{emp_id}_cy{cy_a}_{cy_b}_{day}')
        model.Add(shared_var <= x[(emp_id, cy_a, day)])
        model.Add(shared_var <= x[(emp_id, cy_b, day)])
        model.Add(shared_var >= x[(emp_id, cy_a, day)] +
                  x[(emp_id, cy_b, day)] - 1)
        shared_vars.append(shared_var)

        # joiner_var = 1 if employee works yard B but not yard A (joins mid-day)
        joiner_var = model.NewBoolVar(
            f'joiner_e{emp_id}_cy{cy_a}_{cy_b}_{day}')
        model.Add(joiner_var <= x[(emp_id, cy_b, day)])
        model.Add(joiner_var + x[(emp_id, cy_a, day)] <= 1)
        model.Add(joiner_var >= x[(emp_id, cy_b, day)] -
                  x[(emp_id, cy_a, day)])
        joiner_vars.append(joiner_var)

    # share_any = 1 if any employee works both yards
    share_any = model.NewBoolVar(
        f'share_any_cy{cy_a}_{cy_b}_{day}')
    for shared_var in shared_vars:
        model.Add(shared_var <= share_any)
    model.Add(share_any <= sum(shared_vars))

    # joiner_any = 1 if any employee joins mid-day (works B but not A)
    joiner_any = model.NewBoolVar(
        f'joiner_any_cy{cy_a}_{cy_b}_{day}')
    for joiner_var in joiner_vars:
        model.Add(joiner_var <= joiner_any)
    model.Add(joiner_any <= sum(joiner_vars))

    # mix_var = 1 if both share_any and joiner_any are true (partial overlap penalty)
    mix_var = model.NewBoolVar(
        f'mix_penalty_cy{cy_a}_{cy_b}_{day}')
    model.Add(mix_var >= share_any + joiner_any - 1)
    model.Add(mix_var <= share_any)
    model.Add(mix_var <= joiner_any)

    return mix_var


def solve_roster(request: ScheduleRequest) -> ScheduleResponse:
    """
    Solve the rostering problem using OR-Tools CP-SAT solver

    Constraints:
    - Each yard must have min-max employees if covered
    - Yards respect required days, visit counts, spacing rules, and linked-yard gaps
    - Employees can work multiple yards per day, limited by max_hours_per_day
    - Employees can only work on available days and avoid excluded yards
    - Grouping bonus encourages yards in the same group to be done together

    Objectives (in priority order):
    1. Cover high-priority yards first
    2. Use higher reliability-rated employees
    3. Encourage grouping (yards in same group done together)
    4. Balance workload across employees
    """
    # Input validation
    logger.debug("Starting input validation")

    if len(request.employees) != len({emp.id for emp in request.employees}):
        employee_ids = [emp.id for emp in request.employees]
        duplicates = [
            eid for eid in employee_ids if employee_ids.count(eid) > 1]
        error_msg = f"Duplicate employee IDs found: {set(duplicates)}. Each employee must have a unique ID."
        logger.error(error_msg)
        logger.debug(f"All employee IDs: {employee_ids}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

    if len(request.car_yards) != len({cy.id for cy in request.car_yards}):
        yard_ids = [cy.id for cy in request.car_yards]
        duplicates = [yid for yid in yard_ids if yard_ids.count(yid) > 1]
        error_msg = f"Duplicate car yard IDs found: {set(duplicates)}. Each car yard must have a unique ID."
        logger.error(error_msg)
        logger.debug(f"All car yard IDs: {yard_ids}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

    if not request.employees:
        error_msg = "At least one employee is required."
        logger.error(error_msg)
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

    if not request.car_yards:
        error_msg = "At least one car yard is required."
        logger.error(error_msg)
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

    if not request.days:
        error_msg = "At least one day is required."
        logger.error(error_msg)
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

    logger.debug("Input validation passed")

    # Validate min <= max for each yard
    for cy in request.car_yards:
        if cy.min_employees > cy.max_employees:
            raise HTTPException(
                status_code=400,
                detail=f"Car yard {cy.id} ({cy.name}) has min_employees ({cy.min_employees}) > max_employees ({cy.max_employees})."
            )

    # Validate yard_groups
    if request.yard_groups:
        all_yard_ids = {cy.id for cy in request.car_yards}
        for group_name, cy_ids in request.yard_groups.items():
            invalid_ids = [
                cy_id for cy_id in cy_ids if cy_id not in all_yard_ids]
            if invalid_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Yard group '{group_name}' contains invalid yard IDs: {invalid_ids}. Valid yard IDs are: {sorted(all_yard_ids)}."
                )

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
    # When required_days is set WITHOUT per_week: restrict to only required days (current behavior)
    # When required_days is set WITH per_week: allow all days, but ensure at least one visit on required day
    for cy_id, cy in car_yards.items():
        has_per_week = bool(cy.per_week)
        has_required_days = bool(cy.required_days)

        # If required_days is set but per_week is NOT set: restrict to only required days
        if has_required_days and not has_per_week:
            allowed_days = set(cy.required_days)
            for day in days:
                if day not in allowed_days:
                    model.Add(covered[(cy_id, day)] == 0)
                    for emp_id in employees.keys():
                        model.Add(x[(emp_id, cy_id, day)] == 0)
        # If required_days is set WITH per_week: allow all days (no restriction here)
        # We'll add a constraint later to ensure at least one visit on a required day

        if cy.per_week:
            visits_required, min_gap = cy.per_week
            # Validate that required visits don't exceed available days
            if visits_required > len(days):
                raise HTTPException(
                    status_code=400,
                    detail=f"Car yard {cy_id} ({cy.name}) requires {visits_required} visits per week but only {len(days)} days are scheduled."
                )
            # If required_days is also set, validate that at least one visit can occur on a required day
            # This means we need enough days between required days and other days to satisfy gap
            if has_required_days:
                required_days_set = set(cy.required_days)
                # Check if there are enough days available after considering the gap constraint
                # For example, if per_week=(2, 2) and required_days=[MONDAY], we need:
                # - At least one day that's Monday (required)
                # - At least one day that's at least gap days away from Monday
                available_days_set = set(days)
                if not required_days_set.issubset(available_days_set):
                    missing_days = required_days_set - available_days_set
                    raise HTTPException(
                        status_code=400,
                        detail=f"Car yard {cy_id} ({cy.name}) has required_days {[d.value for d in missing_days]} that are not in the scheduled days {[d.value for d in days]}."
                    )
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
        # Check both source and target yards
        for yard_id in [source_id, target_id]:
            if yard_id in coverage_requirements:
                visits, _ = coverage_requirements[yard_id]
                if visits > 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Linked yard {yard_id} cannot require more than one visit per week."
                    )

    # Employees may have yard exclusions and availability constraints
    for emp_id, emp in employees.items():
        for cy_id, cy in car_yards.items():
            # Check car yard exclusion
            if cy_id in emp.excluded_yards:
                for day in days:
                    model.Add(x[(emp_id, cy_id, day)] == 0)

            else:
                # Check availability
                for day in days:
                    if day not in emp.available_days:
                        model.Add(x[(emp_id, cy_id, day)] == 0)

    # Constraint 1 (UPDATED): If a yard is covered, it must have between min and max employees
    # If not covered, it has 0 employees
    extra_employee_penalties = []
    # Track which yard-days have employees working only that single yard (for penalty application)
    is_single_yard_only: Dict[Tuple[int, DayOfWeek], cp_model.IntVar] = {}

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

            # Check if any employee at this yard is working ONLY this yard (not working other yards)
            # Penalty should only apply when employees are working a single yard, not when doing multiple
            # This allows efficient multi-yard sequences (e.g., Joe and Sam doing Yard A then Yard B)
            employee_single_yard_vars = []
            for emp_id in employees.keys():
                # Check if employee is assigned to this yard
                is_at_this_yard = x[(emp_id, cy_id, day)]

                # Count how many OTHER yards this employee works on the same day
                other_yards_worked = sum(
                    x[(emp_id, other_cy_id, day)]
                    for other_cy_id in car_yards.keys()
                    if other_cy_id != cy_id
                )

                # Employee is working ONLY this yard if:
                # - They're assigned to this yard (is_at_this_yard == 1)
                # - AND they're not working any other yard (other_yards_worked == 0)
                emp_single_yard = model.NewBoolVar(
                    f'emp_single_yard_e{emp_id}_cy{cy_id}_{day}')

                # emp_single_yard == 1 if and only if (is_at_this_yard == 1 AND other_yards_worked == 0)
                # Constraint 1: emp_single_yard can only be 1 if employee is at this yard
                model.Add(emp_single_yard <= is_at_this_yard)

                # Constraint 2: emp_single_yard can only be 1 if employee works no other yards
                # If emp_single_yard == 1, then other_yards_worked == 0
                max_other_yards = len(car_yards) - 1
                model.Add(other_yards_worked <=
                          max_other_yards * (1 - emp_single_yard))

                # Constraint 3: If employee is at this yard and works no other yards, emp_single_yard must be 1
                # We encode: if (is_at_this_yard == 1 AND other_yards_worked == 0), then emp_single_yard == 1
                # Using: emp_single_yard >= is_at_this_yard - other_yards_worked
                # This works because:
                # - If is_at_this_yard == 0: emp_single_yard >= 0 - other_yards_worked (no constraint, but emp_single_yard <= 0 from constraint 1)
                # - If is_at_this_yard == 1 and other_yards_worked == 0: emp_single_yard >= 1 (forces it to 1)
                # - If is_at_this_yard == 1 and other_yards_worked >= 1: emp_single_yard >= 1 - 1 = 0 (allows 0, and constraint 2 prevents 1)
                model.Add(emp_single_yard >=
                          is_at_this_yard - other_yards_worked)

                employee_single_yard_vars.append(emp_single_yard)

            # Check if ANY employee at this yard is working only this yard (single yard only)
            # Penalty applies only if at least one employee is working a single yard
            any_employee_single_yard = model.NewBoolVar(
                f'any_emp_single_yard_cy{cy_id}_{day}')
            is_single_yard_only[(cy_id, day)] = any_employee_single_yard

            # If any employee is single-yard, then any_employee_single_yard == 1
            for emp_single_yard_var in employee_single_yard_vars:
                model.Add(emp_single_yard_var <= any_employee_single_yard)
            # If any_employee_single_yard == 1, then at least one employee must be single-yard
            model.Add(any_employee_single_yard <=
                      sum(employee_single_yard_vars))

            # Calculate extra employees above minimum
            extra_employees = employees_at_yard - \
                cy.min_employees * covered[(cy_id, day)]

            # Only apply penalty if:
            # 1. Yard is covered (covered == 1)
            # 2. At least one employee is working only this yard (any_employee_single_yard == 1)
            # 3. There are extra employees above minimum
            # penalty_amount = extra_employees if (covered == 1 AND any_employee_single_yard == 1), else 0
            penalty_amount = model.NewIntVar(
                0, len(employees), f'penalty_amount_cy{cy_id}_{day}')

            # Upper bounds: penalty cannot exceed extra_employees, and only applies when both conditions are true
            model.Add(penalty_amount <= extra_employees)
            model.Add(penalty_amount <= covered[(cy_id, day)] * len(employees))
            model.Add(penalty_amount <=
                      any_employee_single_yard * len(employees))

            # Lower bound: if both conditions are true, penalty should equal extra_employees
            # penalty_amount >= extra_employees - M * (1 - covered) - M * (1 - any_employee_single_yard)
            max_penalty = len(employees)
            model.Add(penalty_amount >= extra_employees -
                      max_penalty * (1 - covered[(cy_id, day)]))
            model.Add(penalty_amount >= extra_employees -
                      max_penalty * (1 - any_employee_single_yard))

            extra_employee_penalties.append(penalty_amount)

    # Constraint: Yards scheduled on the same day must be within max_radius
    # This prevents scheduling yards that are too far apart geographically
    # Optimize by pre-computing which yard pairs exceed max_radius
    yard_pairs_exceeding_radius = []
    sorted_yard_ids = sorted(car_yards.keys())
    for i in range(len(sorted_yard_ids)):
        cy_a_id = sorted_yard_ids[i]
        cy_a = car_yards[cy_a_id]
        for j in range(i + 1, len(sorted_yard_ids)):
            cy_b_id = sorted_yard_ids[j]
            cy_b = car_yards[cy_b_id]
            position_diff = abs(cy_a.north_south_position -
                                cy_b.north_south_position)
            if position_diff > request.max_radius:
                yard_pairs_exceeding_radius.append((cy_a_id, cy_b_id))

    # Log how many constraints will be added (for debugging)
    total_radius_constraints = len(yard_pairs_exceeding_radius) * len(days)
    if total_radius_constraints > 0:
        logger.debug(
            f"Adding {total_radius_constraints} max_radius constraints ({len(yard_pairs_exceeding_radius)} pairs × {len(days)} days)")

    # Only add constraints for pairs that actually exceed the radius
    for day in days:
        for cy_a_id, cy_b_id in yard_pairs_exceeding_radius:
            # Cannot schedule both yards on the same day
            # If yard A is covered, then yard B cannot be covered on this day
            # If yard B is covered, then yard A cannot be covered on this day
            model.AddBoolOr([
                covered[(cy_a_id, day)].Not(),
                covered[(cy_b_id, day)].Not()
            ])

    # Constraint 2: Limit total hours per employee per day
    # Distribute total yard hours across assigned employees while respecting per-employee limits
    SCALE_FACTOR = MINUTES_PER_HOUR  # Convert hours to minutes for integer arithmetic
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

            # Enforce approximately equal work distribution
            # When a yard is covered, all assigned employees should work approximately the same amount
            # This ensures consistency between solver distribution and post-processing assumption
            # Approach: for any two assigned employees, their work difference is at most 1 minute
            # This allows for integer rounding while keeping distribution fair
            if len(employees) > 1:
                # Only enforce when yard is covered and there are multiple employees
                # For each pair of employees, if both are assigned, their work should differ by at most 1 minute
                emp_id_list = list(employees.keys())
                for i in range(len(emp_id_list)):
                    for j in range(i + 1, len(emp_id_list)):
                        emp_i_id = emp_id_list[i]
                        emp_j_id = emp_id_list[j]
                        work_i = work_minutes[(emp_i_id, cy_id, day)]
                        work_j = work_minutes[(emp_j_id, cy_id, day)]

                        # If both employees are assigned, their work difference should be <= 1
                        # This is enforced via: if both x[i] and x[j] are 1, then |work_i - work_j| <= 1
                        # We use: work_i - work_j <= 1 when both assigned, and work_j - work_i <= 1 when both assigned
                        diff_ij = model.NewIntVar(-total_minutes, total_minutes,
                                                  f'diff_ij_e{emp_i_id}_e{emp_j_id}_cy{cy_id}_d{day}')
                        model.Add(diff_ij == work_i - work_j)

                        # When both are assigned, enforce |diff_ij| <= 1
                        # both_assigned == 1 if and only if both x[i] and x[j] are 1
                        both_assigned = model.NewBoolVar(
                            f'both_e{emp_i_id}_e{emp_j_id}_cy{cy_id}_d{day}')
                        model.Add(both_assigned <= x[(emp_i_id, cy_id, day)])
                        model.Add(both_assigned <= x[(emp_j_id, cy_id, day)])
                        model.Add(both_assigned >= x[(emp_i_id, cy_id, day)] +
                                  x[(emp_j_id, cy_id, day)] - 1)

                        # When both assigned, diff_ij <= 1 and diff_ij >= -1
                        model.Add(diff_ij <= 1).OnlyEnforceIf(both_assigned)
                        model.Add(diff_ij >= -1).OnlyEnforceIf(both_assigned)

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

        # Constraint 3b: When both required_days and per_week are set,
        # ensure at least one visit occurs on a required day
        if cy.required_days and cy.per_week:
            # At least one visit must occur on one of the required days
            required_day_coverage_vars = [
                covered[(cy_id, day)]
                for day in days
                if day in cy.required_days
            ]
            if required_day_coverage_vars:
                # At least one of the required days must be covered
                model.Add(sum(required_day_coverage_vars) >= 1)

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

    # Constraint 5: Employee availability is already handled above (combined with yard exclusion)

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
        CarYardPriority.HIGH: PRIORITY_WEIGHT_HIGH,
        CarYardPriority.MEDIUM: PRIORITY_WEIGHT_MEDIUM,
        CarYardPriority.LOW: PRIORITY_WEIGHT_LOW
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
                    # This encourages grouping but doesn't force it
                    # (works as a soft constraint via objective function)
                    grouping_bonus.append(
                        yards_worked_in_group * GROUPING_BONUS_BASE_WEIGHT)

    # Combined objective: prioritize high-priority yards, maximize quality, minimize workload imbalance
    # Add grouping bonus to encourage grouped yards to be done together
    total_assignments = sum(
        x[(emp_id, cy_id, day)]
        for emp_id in employees.keys()
        for cy_id in car_yards.keys()
        for day in days
    )

    partial_overlap_penalties = []

    sorted_cy_ids = sorted(car_yards.keys())
    for day in days:
        for idx_a in range(len(sorted_cy_ids)):
            cy_a = sorted_cy_ids[idx_a]
            for idx_b in range(idx_a + 1, len(sorted_cy_ids)):
                cy_b = sorted_cy_ids[idx_b]
                mix_var = _create_partial_overlap_penalty(
                    model, employees, cy_a, cy_b, day, x
                )
                partial_overlap_penalties.append(mix_var)

    objective_components = [
        # Highest priority: cover high-priority yards
        sum(priority_score) * OBJECTIVE_PRIORITY_WEIGHT,
        # Second: use better employees
        sum(quality_score) * OBJECTIVE_QUALITY_WEIGHT,
        # Third: encourage grouping (weight 10x the base bonus)
        sum(grouping_bonus) * OBJECTIVE_GROUPING_WEIGHT,
        # Fourth: balance workload (penalty for imbalance)
        -workload_balance * OBJECTIVE_BALANCE_WEIGHT,
        # Discourage assigning more employees than necessary
        -sum(extra_employee_penalties) * OBJECTIVE_EXTRA_EMPLOYEE_WEIGHT,
        # Mild penalty on total assignments to avoid redundant coverage
        -total_assignments * OBJECTIVE_ASSIGNMENT_PENALTY,
        # Penalize partial overlaps where new employees join existing crews mid-day
        -sum(partial_overlap_penalties) * OBJECTIVE_PARTIAL_OVERLAP_WEIGHT
    ]

    model.Maximize(sum(objective_components))

    # Solve
    logger.info("Starting CP-SAT solver")
    logger.debug(f"Solver timeout: {DEFAULT_SOLVER_TIMEOUT_SECONDS} seconds")

    # Log model statistics before solving
    logger.debug(
        f"Model has {len(x)} decision variables (employee-yard-day assignments)")
    logger.debug(
        f"Model has {len(covered)} coverage variables (yard-day coverage)")
    logger.debug(
        f"Total employees: {len(employees)}, Total yards: {len(car_yards)}, Total days: {len(days)}")

    # Create a hash of key input data for comparison
    import hashlib
    input_data_str = json.dumps({
        "employee_count": len(employees),
        "yard_count": len(car_yards),
        "day_count": len(days),
        "employee_availabilities": {eid: len(emp.available_days) for eid, emp in employees.items()},
        "yard_requirements": {cyid: (cy.min_employees, cy.max_employees) for cyid, cy in car_yards.items()},
        "max_hours": request.max_hours_per_day
    }, sort_keys=True)
    input_hash = hashlib.md5(input_data_str.encode()).hexdigest()
    logger.info(f"Input data hash (for comparison): {input_hash}")

    # Log feasibility analysis before solving
    total_employee_days_available = sum(
        len(emp.available_days) for emp in employees.values()
    )
    total_yard_days = len(car_yards) * len(days)
    min_employees_needed = sum(cy.min_employees for cy in car_yards.values())
    max_employees_needed = sum(cy.max_employees for cy in car_yards.values())

    logger.info(
        f"Feasibility check: {len(employees)} employees, {total_employee_days_available} total employee-days available")
    logger.info(
        f"Coverage needed: {len(car_yards)} yards × {len(days)} days = {total_yard_days} yard-days")
    logger.info(
        f"Employee availability: {[(e.id, e.name, len(e.available_days), [d.value for d in e.available_days]) for e in employees.values()]}")
    logger.debug(
        f"Min employees needed per yard: {min_employees_needed}, Max: {max_employees_needed}")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = DEFAULT_SOLVER_TIMEOUT_SECONDS
    status = solver.Solve(model)

    # Log solver status
    status_names = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN"
    }
    status_name = status_names.get(status, f"UNKNOWN_STATUS_{status}")
    logger.info(f"Solver status: {status_name} (code: {status})")
    logger.info(f"Solver wall time: {solver.WallTime():.2f} seconds")
    logger.debug(
        f"Solver statistics: {solver.NumBooleans()} booleans, {solver.NumBranches()} branches, {solver.NumConflicts()} conflicts")

    if status == cp_model.INFEASIBLE:
        logger.error(
            "Solver returned INFEASIBLE - constraints cannot be satisfied")
        logger.error("Possible reasons:")
        logger.error(
            f"  - Not enough employees available (have {len(employees)} employees)")
        logger.error(
            f"  - Employee availability too restrictive (total {total_employee_days_available} employee-days)")
        logger.error(
            f"  - Yard requirements too high (need {min_employees_needed}-{max_employees_needed} employees per assignment)")
        logger.error(
            f"  - Max hours per day too restrictive ({request.max_hours_per_day} hours)")
        # Check for employees with no availability
        no_availability = [
            e for e in employees.values() if not e.available_days]
        if no_availability:
            logger.error(
                f"  - Employees with NO available days: {[(e.id, e.name) for e in no_availability]}")
    elif status == cp_model.UNKNOWN:
        logger.warning(
            "Solver returned UNKNOWN - may have timed out or hit resource limits")
        logger.warning(
            f"  - Timeout was {DEFAULT_SOLVER_TIMEOUT_SECONDS} seconds")
        logger.warning(
            f"  - Actual solve time: {solver.WallTime():.2f} seconds")

    # Build response (same as before)
    # First collect raw assignment data (without creating Assignment objects yet)
    raw_assignments = []
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for emp_id, emp in employees.items():
            for cy_id, cy in car_yards.items():
                for day in days:
                    if solver.Value(x[(emp_id, cy_id, day)]) == 1:
                        raw_assignments.append({
                            "employee_id": emp_id,
                            "employee_name": emp.name,
                            "car_yard_id": cy_id,
                            "car_yard_name": cy.name,
                            "day": day
                        })

        if not raw_assignments:
            raise HTTPException(
                status_code=400,
                detail="No feasible assignments produced. Check availability, required days, or coverage limits."
            )

        # Calculate stats from raw assignments
        shifts_count = {emp_id: 0 for emp_id in employees.keys()}
        yards_covered = {}  # Track which yards were covered
        for assignment_data in raw_assignments:
            shifts_count[assignment_data["employee_id"]] += 1
            key = (assignment_data["car_yard_id"], assignment_data["day"])
            if key not in yards_covered:
                yards_covered[key] = []
            yards_covered[key].append(assignment_data["employee_id"])

        day_assignments: Dict[DayOfWeek, List[Tuple[int, List[int]]]] = {}
        for (cy_id, day), employee_ids in yards_covered.items():
            day_assignments.setdefault(day, []).append((cy_id, employee_ids))

        hours_per_employee_day = {
            f"emp_{emp_id}_day_{day.value}":
            solver.Value(minutes_var) / SCALE_FACTOR
            for (emp_id, day), minutes_var in employee_day_minutes.items()
        }

        default_start = request.earliest_start_time or time(
            hour=DEFAULT_EARLIEST_START_HOUR, minute=DEFAULT_EARLIEST_START_MINUTE)

        def add_minutes(base: time, minutes: float) -> time:
            base_dt = datetime.combine(datetime.today(), base)
            end_dt = base_dt + timedelta(minutes=minutes)
            return end_dt.time()

        yard_timeblocks: List[YardTimeblock] = []
        travel_buffer = request.travel_buffer_minutes

        priority_rank = {
            CarYardPriority.HIGH: 0,
            CarYardPriority.MEDIUM: 1,
            CarYardPriority.LOW: 2,
            # Default rank for unknown priorities (shouldn't happen, but safe fallback)
        }

        # Get actual work hours from solver for each employee at each yard
        # work_minutes stores integer minutes (scaled by SCALE_FACTOR=60)
        actual_work_hours: Dict[Tuple[int, int, DayOfWeek], float] = {}
        for (emp_id, cy_id, day), work_var in work_minutes.items():
            # Convert from minutes to hours
            actual_work_hours[(emp_id, cy_id, day)] = solver.Value(
                work_var) / SCALE_FACTOR

        for day in days:
            if day not in day_assignments:
                continue
            day_yards = day_assignments[day]
            # Sort by yard specific start time then priority then id
            day_yards = sorted(
                day_yards,
                key=lambda item: (
                    car_yards[item[0]].startTime or default_start,
                    priority_rank.get(car_yards[item[0]].priority,
                                      DEFAULT_PRIORITY_RANK),
                    item[0]
                )
            )
            availability: Dict[int, time] = {}

            for cy_id, employee_ids in day_yards:
                employee_count = len(employee_ids)
                if employee_count == 0:
                    continue
                cy = car_yards[cy_id]
                earliest_allowed = cy.startTime or default_start
                start_candidates = [availability.get(emp_id, default_start)
                                    for emp_id in employee_ids]
                proposed_start = max(
                    earliest_allowed, *start_candidates) if start_candidates else earliest_allowed

                # All workers work equally: each works hours_required / num_employees
                # This is the correct calculation since hours_required is the total if done by one worker
                per_employee_hours = cy.hours_required / \
                    employee_count if employee_count > 0 else 0.0

                # DEBUG: Log actual vs expected work distribution
                solver_work_hours = [
                    actual_work_hours.get((emp_id, cy_id, day), 0.0)
                    for emp_id in employee_ids
                ]
                if solver_work_hours:
                    logger.debug(
                        f"Yard {cy_id} ({cy.name}) on {day.value}: "
                        f"{employee_count} employees, hours_required={cy.hours_required}, "
                        f"expected_per_employee={per_employee_hours:.2f}h, "
                        f"solver_distribution={[f'{h:.2f}h' for h in solver_work_hours]}"
                    )

                # Calculate finish time: all workers start together and finish together
                # since they all work the same amount (hours_required / num_employees)
                finish_time = add_minutes(
                    proposed_start, per_employee_hours * MINUTES_PER_HOUR)

                # Update availability for each employee (all finish at the same time)
                for emp_id in employee_ids:
                    availability[emp_id] = add_minutes(
                        finish_time, travel_buffer)

                yard_timeblocks.append(YardTimeblock(
                    car_yard_id=cy_id,
                    car_yard_name=cy.name,
                    day=day.value,
                    start_time=proposed_start.isoformat(timespec="minutes"),
                    finish_time=finish_time.isoformat(timespec="minutes"),
                    employees=employee_ids,
                    minutes_per_employee=per_employee_hours * MINUTES_PER_HOUR,
                    per_employee_hours=per_employee_hours
                ))

        # Validate that no employee exceeds max_hours_per_day
        # Use the solver's actual work distribution for validation (not equal distribution)
        # The solver constraint should already enforce this, but we verify as a safety check
        employee_total_hours_per_day: Dict[Tuple[int, DayOfWeek], float] = {}
        for (emp_id, cy_id, day), work_hours in actual_work_hours.items():
            if work_hours > 0:  # Only count actual work assignments
                key = (emp_id, day)
                employee_total_hours_per_day[key] = employee_total_hours_per_day.get(
                    key, 0.0) + work_hours

        # Also validate using equal distribution calculation (for reporting/scheduling purposes)
        # This is what we use for finish times, so it should also respect max_hours_per_day
        # Reuse per_employee_hours from yard_timeblocks to avoid duplicate calculation
        employee_total_hours_equal_dist: Dict[Tuple[int, DayOfWeek], float] = {
        }
        # Create lookup for per_employee_hours from yard_timeblocks
        per_employee_hours_lookup = {
            (block.car_yard_id, DayOfWeek(block.day)): block.per_employee_hours
            for block in yard_timeblocks
        }
        for (cy_id, day), employee_ids in yards_covered.items():
            if not employee_ids:
                continue
            # Reuse calculated per_employee_hours from yard_timeblocks
            per_employee_hours = per_employee_hours_lookup.get(
                (cy_id, day), 0.0)
            if per_employee_hours == 0.0:
                # Fallback calculation if not found in lookup (shouldn't happen)
                cy = car_yards[cy_id]
                employee_count = len(employee_ids)
                per_employee_hours = cy.hours_required / \
                    employee_count if employee_count > 0 else 0.0
            for emp_id in employee_ids:
                key = (emp_id, day)
                employee_total_hours_equal_dist[key] = employee_total_hours_equal_dist.get(
                    key, 0.0) + per_employee_hours

        # Check both: solver's actual distribution and our equal distribution
        for (emp_id, day), total_hours in employee_total_hours_equal_dist.items():
            if total_hours > request.max_hours_per_day + FLOATING_POINT_TOLERANCE:
                # Log warning but don't fail - the solver constraint should handle this
                solver_hours = employee_total_hours_per_day.get(
                    (emp_id, day), 0.0)
                emp_name = next(
                    (emp.name for emp in request.employees if emp.id == emp_id), f"Employee {emp_id}")
                logger.warning(
                    f"Employee {emp_name} would exceed max_hours_per_day ({request.max_hours_per_day}) "
                    f"on {day.value} with equal distribution ({total_hours:.2f}h), "
                    f"but solver distribution shows {solver_hours:.2f}h. "
                    f"This may indicate a constraint issue."
                )

        # Create mapping from (car_yard_id, day) to (start_time, finish_time) from yard_timeblocks
        yard_timing_map: Dict[Tuple[int, DayOfWeek], Tuple[str, str]] = {}
        for block in yard_timeblocks:
            day = DayOfWeek(block.day)
            key = (block.car_yard_id, day)
            yard_timing_map[key] = (block.start_time, block.finish_time)

        # Create Assignment objects with start and finish times
        assignments = []
        for assignment_data in raw_assignments:
            timing_key = (
                assignment_data["car_yard_id"], assignment_data["day"])
            start_time, finish_time = yard_timing_map.get(
                timing_key, ("", ""))
            assignments.append(Assignment(
                employee_id=assignment_data["employee_id"],
                employee_name=assignment_data["employee_name"],
                car_yard_id=assignment_data["car_yard_id"],
                car_yard_name=assignment_data["car_yard_name"],
                day=assignment_data["day"],
                start_time=start_time,
                finish_time=finish_time
            ))

        # Build roster structure for frontend
        employee_name_map = {emp.id: emp.name for emp in request.employees}
        roster_by_day: Dict[DayOfWeek, List[YardSchedule]] = {}

        for block in yard_timeblocks:
            day = DayOfWeek(block.day)
            worker_names = [employee_name_map[emp_id]
                            for emp_id in block.employees]

            yard_schedule = YardSchedule(
                car_yard_id=block.car_yard_id,
                car_yard_name=block.car_yard_name,
                workers=worker_names,
                start_time=block.start_time,
                finish_time=block.finish_time
            )

            if day not in roster_by_day:
                roster_by_day[day] = []
            roster_by_day[day].append(yard_schedule)

        # Build DayRoster for each day in the request (even if empty)
        day_rosters = []
        for day in days:
            yards = roster_by_day.get(day, [])
            day_rosters.append(DayRoster(day=day, yards=yards))

        roster_structure = RosterStructure(days=day_rosters)

        # Create typed stats object
        stats = ScheduleStats(
            total_assignments=len(assignments),
            shifts_per_employee=shifts_count,
            yards_covered={f"yard_{cy_id}_day_{day.value}": len(employee_ids)
                           for (cy_id, day), employee_ids in yards_covered.items()},
            hours_per_employee_day=hours_per_employee_day,
            yard_timeblocks=yard_timeblocks,
            solve_time_seconds=solver.WallTime()
        )

        return ScheduleResponse(
            status="optimal" if status == cp_model.OPTIMAL else "feasible",
            assignments=assignments,
            roster=roster_structure,
            stats=stats
        )
    else:
        # Provide detailed error message based on solver status
        if status == cp_model.INFEASIBLE:
            no_availability = [
                e for e in employees.values() if not e.available_days]
            detail = f"No feasible solution found. The constraints cannot be satisfied. "
            if no_availability:
                detail += f"Employees with no available days: {[e.name for e in no_availability]}. "
            detail += f"Check employee availability, yard requirements, and max hours per day ({request.max_hours_per_day}h)."
        elif status == cp_model.UNKNOWN:
            detail = f"Solver could not determine feasibility (may have timed out after {DEFAULT_SOLVER_TIMEOUT_SECONDS}s). Try increasing timeout or relaxing constraints."
        else:
            detail = f"No feasible solution found. Solver status: {status_name}. Check constraints (availability, min/max employees per yard)"

        logger.error(f"Raising HTTPException: {detail}")
        raise HTTPException(
            status_code=400,
            detail=detail
        )


@api.post("/api/v1/roster", response_model=ScheduleResponse)
async def generate_roster(request: ScheduleRequest):
    """
    Generate an optimal roster for car yard cleaning
    """
    try:
        logger.info("=== Starting roster generation ===")
        logger.info(
            f"Pydantic parsed request: {len(request.employees)} employees, {len(request.car_yards)} car yards, {len(request.days)} days")

        # Log the actual Pydantic model data to see what was parsed
        logger.debug(
            f"Parsed request model: employees={len(request.employees)}, car_yards={len(request.car_yards)}, days={len(request.days)}")
        logger.debug(f"Request model dict keys: {request.model_dump().keys()}")

        # Log serialized request to compare with what was sent
        try:
            request_dict = request.model_dump()
            logger.debug(
                f"Full parsed request (first 2000 chars): {json.dumps(request_dict, indent=2, default=str)[:2000]}")
        except Exception as e:
            logger.warning(f"Could not serialize request model: {e}")

        # Log request details at debug level
        logger.debug(
            f"Employees: {[{'id': e.id, 'name': e.name, 'ranking': e.ranking.value, 'available_days': [d.value for d in e.available_days]} for e in request.employees]}")
        logger.debug(f"Car yards: {[{'id': cy.id, 'name': cy.name, 'priority': cy.priority.value, 'north_south_position': cy.north_south_position, 'min_employees': cy.min_employees, 'max_employees': cy.max_employees} for cy in request.car_yards]}")
        logger.debug(f"Days: {[d.value for d in request.days]}")
        logger.debug(f"Max hours per day: {request.max_hours_per_day}")
        logger.debug(f"Travel buffer: {request.travel_buffer_minutes} minutes")

        result = solve_roster(request)

        logger.info(
            f"Roster generated successfully: {result.status}, {len(result.assignments)} assignments")
        logger.debug(
            f"Stats: {result.stats.total_assignments} total assignments, solve time: {result.stats.solve_time_seconds:.2f}s")

        return result

    except HTTPException as e:
        logger.error(
            f"HTTPException in roster generation: {e.status_code} - {e.detail}")
        logger.debug(f"HTTPException traceback: {traceback.format_exc()}")
        raise
    except ValidationError as e:
        logger.error(f"ValidationError in roster generation: {e}")
        logger.debug(f"ValidationError details: {e.errors()}")
        logger.debug(f"ValidationError traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in roster generation: {type(e).__name__}: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}: {str(e)}"
        )


@api.get("/")
async def root():
    return {
        "message": "Car Yard Rostering API",
        "docs": "/docs"
    }


@api.get("/health")
async def health():
    """Liveness probe endpoint"""
    return {"status": "healthy"}


@api.get("/ready")
async def ready():
    """Readiness probe endpoint"""
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8888)
