import platform
import sys
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, computed_field, ValidationError
from typing import List, Dict, Optional, Any, Tuple, Set
from ortools.sat.python import cp_model
from datetime import time, datetime, timedelta
from enum import Enum
from collections import Counter
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
    # Health check endpoints that should be logged at DEBUG level only
    HEALTH_CHECK_PATHS = ["/health", "/ready", "/"]

    async def dispatch(self, request: Request, call_next):
        # Log health checks at DEBUG level to reduce log clutter
        is_health_check = request.url.path in self.HEALTH_CHECK_PATHS

        if is_health_check:
            logger.debug(f"Health check: {request.method} {request.url.path}")
        else:
            logger.info(f"Request: {request.method} {request.url.path}")
            logger.debug(f"Request headers: {dict(request.headers)}")
            logger.debug(
                f"Content-Type: {request.headers.get('content-type', 'not set')}")
            logger.debug(
                f"Content-Length: {request.headers.get('content-length', 'not set')}")

        response = await call_next(request)

        if is_health_check:
            logger.debug(
                f"Health check response: {response.status_code} for {request.method} {request.url.path}")
        else:
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


class RadiusMode(str, Enum):
    """How to apply the geographic radius rule (north_south_position)."""
    SOFT = "soft"  # penalize far-apart yards on the same day
    HARD = "hard"  # forbid far-apart yards on the same day
    OFF = "off"    # ignore radius entirely


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
    max_radius: int = Field(
        default=1000, ge=0,
        description="Maximum position difference between yards that can be scheduled same day")
    radius_mode: RadiusMode = Field(
        default=RadiusMode.SOFT,
        description="How to apply max_radius: 'soft' (penalty), 'hard' (forbid), or 'off' (ignore)."
    )


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
# New penalty weights (soft constraints)
OBJECTIVE_RADIUS_PENALTY_WEIGHT = 500
OBJECTIVE_GAP_PENALTY_WEIGHT = 300
OBJECTIVE_LINKED_GAP_PENALTY_WEIGHT = 400
OBJECTIVE_MAX_HOURS_OVERAGE_WEIGHT = 200
OBJECTIVE_HOURS_SHORTFALL_WEIGHT = 150

# Priority weights for yard coverage
PRIORITY_WEIGHT_HIGH = 1000
PRIORITY_WEIGHT_MEDIUM = 100
PRIORITY_WEIGHT_LOW = 10

# Grouping bonus base weight
GROUPING_BONUS_BASE_WEIGHT = 50

# Solver configuration
# Solver timeout - can be overridden via SOLVER_TIMEOUT_SECONDS environment variable
DEFAULT_SOLVER_TIMEOUT_SECONDS = float(
    os.getenv("SOLVER_TIMEOUT_SECONDS", "120.0"))
# CP-SAT parallelism (number of workers/threads). Defaults to CPU cores.
# Handle empty string case from docker-compose environment variables
_solver_workers_env = os.getenv("SOLVER_NUM_WORKERS", "").strip()
if _solver_workers_env:
    DEFAULT_SOLVER_NUM_WORKERS = int(_solver_workers_env)
else:
    DEFAULT_SOLVER_NUM_WORKERS = os.cpu_count() or 1
# Allowable overage buffer for max-hours (minutes)
HOURS_OVERAGE_BUFFER_MINUTES = int(
    os.getenv("HOURS_OVERAGE_BUFFER_MINUTES", "120"))

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
    x: Dict[Tuple[int, int, DayOfWeek], cp_model.IntVar],
    invalid_assignments: Set[Tuple[int, int, DayOfWeek]],
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
    # PERFORMANCE NOTE:
    # This penalty can easily dominate model size (O(days * yards^2 * employees)).
    # We avoid creating unnecessary variables/constraints by:
    # - skipping employees where assignments are impossible (vars fixed to 0 / absent)
    # - using AddMaxEquality for "any" flags rather than O(n) implications
    shared_vars: List[cp_model.IntVar] = []
    joiner_vars: List[cp_model.IntVar] = []

    for emp_id in employees.keys():
        a_key = (emp_id, cy_a, day)
        b_key = (emp_id, cy_b, day)
        xa = x.get(a_key)
        xb = x.get(b_key)

        # NOTE: We can't do "if xa == 0" in Python because (xa == 0) is an
        # OR-Tools expression, not a boolean. We instead use membership in the
        # precomputed invalid_assignments set to determine impossibility.
        a_impossible = a_key in invalid_assignments
        b_impossible = b_key in invalid_assignments

        # If neither assignment is possible, this employee can never contribute.
        if a_impossible and b_impossible:
            continue

        # If A is impossible but B is possible, then "joiner" is simply (works B).
        # (They can't be a "shared" employee since shared requires both A and B.)
        if a_impossible and not b_impossible:
            if xb is None:
                # Shouldn't happen if invalid_assignments is consistent with x creation,
                # but be defensive to avoid runtime crashes.
                continue
            joiner_vars.append(xb)
            continue

        # If B is impossible, they can't be a joiner or shared employee for this pair.
        if b_impossible:
            continue

        # If we got here, both A and B should be possible, so xa/xb must exist.
        if xa is None or xb is None:
            continue

        # shared_var = 1 if employee works both yards (A AND B)
        shared_var = model.NewBoolVar(
            f'shared_e{emp_id}_cy{cy_a}_{cy_b}_{day}')
        model.Add(shared_var <= xa)
        model.Add(shared_var <= xb)
        model.Add(shared_var >= xa + xb - 1)
        shared_vars.append(shared_var)

        # joiner_var = 1 if employee works yard B but not yard A (B AND NOT A)
        joiner_var = model.NewBoolVar(
            f'joiner_e{emp_id}_cy{cy_a}_{cy_b}_{day}')
        model.Add(joiner_var <= xb)
        model.Add(joiner_var + xa <= 1)
        model.Add(joiner_var >= xb - xa)
        joiner_vars.append(joiner_var)

    # If either side is impossible, partial overlap cannot occur.
    if not shared_vars or not joiner_vars:
        return model.NewConstant(0)

    # share_any = OR(shared_vars)
    share_any = model.NewBoolVar(f'share_any_cy{cy_a}_{cy_b}_{day}')
    model.AddMaxEquality(share_any, shared_vars)

    # joiner_any = OR(joiner_vars)
    joiner_any = model.NewBoolVar(f'joiner_any_cy{cy_a}_{cy_b}_{day}')
    model.AddMaxEquality(joiner_any, joiner_vars)

    # mix_var = 1 if both share_any and joiner_any are true (partial overlap penalty)
    mix_var = model.NewBoolVar(f'mix_penalty_cy{cy_a}_{cy_b}_{day}')
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
    - Yards scheduled on the same day must be within max_radius (geographic constraint)

    Objectives (in priority order):
    1. Cover high-priority yards first
    2. Use higher reliability-rated employees
    3. Balance workload across employees
    """
    # Input validation
    logger.debug("Starting input validation")

    # Optimized: Use Counter for O(n) duplicate detection instead of O(n²)
    employee_ids = [emp.id for emp in request.employees]
    employee_id_counts = Counter(employee_ids)
    duplicates = [eid for eid, count in employee_id_counts.items()
                  if count > 1]
    if duplicates:
        error_msg = f"Duplicate employee IDs found: {set(duplicates)}. Each employee must have a unique ID."
        logger.error(error_msg)
        logger.debug(f"All employee IDs: {employee_ids}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

    # Optimized: Use Counter for O(n) duplicate detection instead of O(n²)
    yard_ids = [cy.id for cy in request.car_yards]
    yard_id_counts = Counter(yard_ids)
    duplicates = [yid for yid, count in yard_id_counts.items() if count > 1]
    if duplicates:
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

    # Comprehensive validation with explicit error messages
    # Pre-compute all yard IDs for reference validation
    all_yard_ids = {cy.id for cy in request.car_yards}

    # Validate employees
    for idx, emp in enumerate(request.employees):
        if not emp.name or not emp.name.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Employee at index {idx} has an empty or missing name. Employee ID: {emp.id if hasattr(emp, 'id') else 'unknown'}"
            )
        if emp.id is None or emp.id < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Employee '{emp.name}' has invalid ID: {emp.id}. Employee ID must be a positive integer."
            )
        # Validate excluded_yards reference existing yards
        if emp.excluded_yards:
            invalid_yard_ids = [
                yid for yid in emp.excluded_yards if yid not in all_yard_ids]
            if invalid_yard_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Employee '{emp.name}' (ID: {emp.id}) has excluded_yards referencing non-existent yard IDs: {invalid_yard_ids}. Valid yard IDs are: {sorted(all_yard_ids)}"
                )

    # Validate car yards

    for idx, cy in enumerate(request.car_yards):
        if not cy.name or not cy.name.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Car yard at index {idx} has an empty or missing name. Car yard ID: {cy.id if hasattr(cy, 'id') else 'unknown'}"
            )
        if cy.id is None or cy.id < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Car yard '{cy.name}' has invalid ID: {cy.id}. Car yard ID must be a positive integer."
            )

        # Validate min <= max employees
        if cy.min_employees > cy.max_employees:
            raise HTTPException(
                status_code=400,
                detail=f"Car yard '{cy.name}' (ID: {cy.id}) has min_employees ({cy.min_employees}) greater than max_employees ({cy.max_employees})."
            )

        # Validate linked_yard references existing yard
        if cy.linked_yard:
            linked_yard_id, gap_days = cy.linked_yard
            if linked_yard_id not in all_yard_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Car yard '{cy.name}' (ID: {cy.id}) has linked_yard referencing non-existent yard ID: {linked_yard_id}. Valid yard IDs are: {sorted(all_yard_ids)}"
                )
            if gap_days < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Car yard '{cy.name}' (ID: {cy.id}) has linked_yard with negative gap_days: {gap_days}. Gap must be non-negative."
                )

        # Validate required_days are in the schedule days
        if cy.required_days:
            schedule_days_set = set(request.days)
            invalid_required_days = [
                day for day in cy.required_days if day not in schedule_days_set]
            if invalid_required_days:
                raise HTTPException(
                    status_code=400,
                    detail=f"Car yard '{cy.name}' (ID: {cy.id}) has required_days {[d.value for d in invalid_required_days]} that are not in the scheduled days {[d.value for d in request.days]}."
                )

    # Validate max_hours_per_day is reasonable (note: days list already validated earlier)
    if request.max_hours_per_day < 3:
        raise HTTPException(
            status_code=400,
            detail=f"max_hours_per_day ({request.max_hours_per_day}) is too low. Minimum allowed is 3 hours."
        )
    if request.max_hours_per_day > 24:
        raise HTTPException(
            status_code=400,
            detail=f"max_hours_per_day ({request.max_hours_per_day}) exceeds maximum of 24 hours per day."
        )

    logger.debug("Input validation passed")

    model = cp_model.CpModel()

    # Create indices
    employees = {emp.id: emp for emp in request.employees}
    car_yards = {cy.id: cy for cy in request.car_yards}
    days = request.days

    # Cache repeated calculations for performance
    num_employees = len(employees)
    num_car_yards = len(car_yards)
    num_days = len(days)
    emp_id_list = list(employees.keys())
    cy_id_list = list(car_yards.keys())
    max_other_yards = num_car_yards - 1

    # NEW: Decision variable for whether a yard is covered on a day
    # covered[cy][d] = 1 if car_yard cy is covered (has at least min_employees) on day d
    covered = {}
    for cy_id in cy_id_list:
        for day in days:
            covered[(cy_id, day)] = model.NewBoolVar(
                f'covered_cy{cy_id}_{day}')

    day_index = {day: idx for idx, day in enumerate(days)}
    coverage_requirements: Dict[int, Tuple[int, int]] = {}
    link_pairs: Dict[Tuple[int, int], int] = {}
    disallowed_yard_days: Dict[int, Set[DayOfWeek]] = {
        cy_id: set() for cy_id in cy_id_list}

    # Restrict assignments to allowed days and collect visit requirements
    # When required_days is set WITHOUT per_week: restrict to only required days (current behavior)
    # When required_days is set WITH per_week: allow all days, but ensure at least one visit on required day
    for cy_id, cy in car_yards.items():
        has_per_week = bool(cy.per_week)
        has_required_days = bool(cy.required_days)

        # REQUIRED DAYS TAKE PRECEDENCE
        if has_required_days:
            allowed_days = set(cy.required_days)
            for day in days:
                if day not in allowed_days:
                    model.Add(covered[(cy_id, day)] == 0)
                    disallowed_yard_days[cy_id].add(day)
            # Require coverage on every required day (exactly once per required day)
            for day in cy.required_days:
                model.Add(covered[(cy_id, day)] == 1)

            # Ignore per_week counts when required days are present
            visits_required = len(cy.required_days)
            min_gap = 0
        else:
            if cy.per_week:
                visits_required, min_gap = cy.per_week
                # Validate that required visits don't exceed available days
                if visits_required > num_days:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Car yard {cy_id} ({cy.name}) requires {visits_required} visits per week but only {num_days} days are scheduled."
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
    # Optimized: Pre-compute invalid assignments to reduce constraint creation overhead
    invalid_assignments: Set[Tuple[int, int, DayOfWeek]] = set()

    # Yard-day restrictions: if a yard is disallowed on a day, no employee can be assigned.
    for cy_id, disallowed_days in disallowed_yard_days.items():
        for day in disallowed_days:
            for emp_id in emp_id_list:
                invalid_assignments.add((emp_id, cy_id, day))

    for emp_id, emp in employees.items():
        excluded_yards_set = set(emp.excluded_yards)
        available_days_set = set(emp.available_days)
        for cy_id in cy_id_list:
            if cy_id in excluded_yards_set:
                # All days are invalid for this employee-yard combination
                for day in days:
                    invalid_assignments.add((emp_id, cy_id, day))
            else:
                # Only unavailable days are invalid
                for day in days:
                    if day not in available_days_set:
                        invalid_assignments.add((emp_id, cy_id, day))

    # Decision variables: x[(emp_id, cy_id, day)] = 1 if employee works at yard on day
    # PERFORMANCE: Only create variables for valid (not invalid) assignments.
    x: Dict[Tuple[int, int, DayOfWeek], cp_model.IntVar] = {}
    for emp_id in emp_id_list:
        for cy_id in cy_id_list:
            for day in days:
                key = (emp_id, cy_id, day)
                if key in invalid_assignments:
                    continue
                x[key] = model.NewBoolVar(f'x_e{emp_id}_cy{cy_id}_{day}')

    # Constraint 1 (UPDATED): If a yard is covered, it must have between min and max employees
    # If not covered, it has 0 employees
    extra_employee_penalties = []

    for cy_id, cy in car_yards.items():
        for day in days:
            employees_at_yard = sum(
                x.get((emp_id, cy_id, day), 0) for emp_id in emp_id_list
            )

            # If covered = 1, then employees_at_yard >= min_employees
            # If covered = 0, then employees_at_yard >= 0 (always true)
            model.Add(employees_at_yard >= cy.min_employees *
                      covered[(cy_id, day)])

            # If covered = 1, then employees_at_yard <= max_employees
            # If covered = 0, then employees_at_yard <= 0 (forces 0 employees)
            model.Add(employees_at_yard <= cy.max_employees *
                      covered[(cy_id, day)])

            # Calculate extra employees above minimum (always penalize extras when covered)
            extra_employees = employees_at_yard - \
                cy.min_employees * covered[(cy_id, day)]

            penalty_amount = model.NewIntVar(
                0, num_employees, f'penalty_amount_cy{cy_id}_{day}')

            model.Add(penalty_amount == 0).OnlyEnforceIf(
                covered[(cy_id, day)].Not())
            model.Add(penalty_amount == extra_employees).OnlyEnforceIf(
                covered[(cy_id, day)])

            extra_employee_penalties.append(penalty_amount)

    # Radius rule (north/south position)
    # - SOFT: penalize scheduling far-apart yards on the same day
    # - HARD: forbid scheduling far-apart yards on the same day
    # - OFF: ignore radius entirely
    yard_pairs_exceeding_radius = []
    radius_penalties = []
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

    if request.radius_mode == RadiusMode.SOFT:
        for day in days:
            for cy_a_id, cy_b_id in yard_pairs_exceeding_radius:
                both_covered = model.NewBoolVar(
                    f'radius_violation_cy{cy_a_id}_{cy_b_id}_{day}')
                model.Add(both_covered <= covered[(cy_a_id, day)])
                model.Add(both_covered <= covered[(cy_b_id, day)])
                model.Add(both_covered >= covered[(cy_a_id, day)] +
                          covered[(cy_b_id, day)] - 1)
                radius_penalties.append(both_covered)
    elif request.radius_mode == RadiusMode.HARD:
        # Forbid covering far-apart yards on the same day.
        # This is often faster than SOFT because it reduces the search space.
        for day in days:
            for cy_a_id, cy_b_id in yard_pairs_exceeding_radius:
                model.Add(covered[(cy_a_id, day)] +
                          covered[(cy_b_id, day)] <= 1)
    else:
        # OFF: radius_penalties stays empty and no constraints are added.
        pass

    # Constraint 2: Limit total hours per employee per day
    # Distribute total yard hours across assigned employees while respecting per-employee limits
    SCALE_FACTOR = MINUTES_PER_HOUR  # Convert hours to minutes for integer arithmetic
    work_minutes: Dict[Tuple[int, int, DayOfWeek], cp_model.IntVar] = {}
    employee_day_minutes: Dict[Tuple[int, DayOfWeek], cp_model.IntVar] = {}
    gap_penalties = []
    linked_gap_penalties = []
    hours_shortfall_penalties = []
    hours_overage_penalties = []
    for cy_id, cy in car_yards.items():
        total_minutes = int(cy.hours_required * SCALE_FACTOR)
        for day in days:
            work_vars = []
            for emp_id in emp_id_list:
                x_key = (emp_id, cy_id, day)
                x_var = x.get(x_key)
                if x_var is None:
                    # Impossible assignment => no work minutes variable needed.
                    work_minutes[(emp_id, cy_id, day)] = 0
                    continue

                work_var = model.NewIntVar(
                    0, total_minutes,
                    f'work_e{emp_id}_cy{cy_id}_d{day}')
                work_minutes[(emp_id, cy_id, day)] = work_var
                model.Add(work_var == 0).OnlyEnforceIf(x_var.Not())
                model.Add(work_var <= total_minutes).OnlyEnforceIf(x_var)
                work_vars.append(work_var)

            total_work = sum(work_vars)
            # Allow partial allocation with penalty
            model.Add(total_work <= total_minutes).OnlyEnforceIf(
                covered[(cy_id, day)])
            model.Add(total_work == 0).OnlyEnforceIf(
                covered[(cy_id, day)].Not())

            shortfall = model.NewIntVar(
                0, total_minutes, f'shortfall_cy{cy_id}_d{day}')
            model.Add(shortfall == 0).OnlyEnforceIf(
                covered[(cy_id, day)].Not())
            model.Add(shortfall == total_minutes -
                      total_work).OnlyEnforceIf(covered[(cy_id, day)])
            hours_shortfall_penalties.append(shortfall)

            # Enforce approximately equal work distribution (OPTIMIZED: O(n) instead of O(n²))
            # When a yard is covered, all assigned employees should work approximately the same amount
            # This ensures consistency between solver distribution and post-processing assumption
            # Approach: use min/max bounds instead of pairwise comparisons
            # All assigned employees must be between min_work and max_work, with max_work - min_work <= 1
            # This allows for integer rounding while keeping distribution fair
            if num_employees > 1:
                # Only enforce when yard is covered and there are multiple employees
                # Create min and max work variables for this yard-day
                min_work = model.NewIntVar(
                    0, total_minutes, f'min_work_cy{cy_id}_d{day}')
                max_work = model.NewIntVar(
                    0, total_minutes, f'max_work_cy{cy_id}_d{day}')

                # Always ensure min_work <= max_work
                model.Add(min_work <= max_work)

                # When yard is covered, constrain the spread to be at most 1 minute
                # This ensures all assigned employees work within 1 minute of each other
                model.Add(max_work - min_work <=
                          1).OnlyEnforceIf(covered[(cy_id, day)])

                # For each employee: if assigned, their work must be between min_work and max_work
                for emp_id in emp_id_list:
                    work_var = work_minutes[(emp_id, cy_id, day)]
                    x_var = x.get((emp_id, cy_id, day))
                    if x_var is None:
                        continue

                    # If assigned, work >= min_work
                    # When work_var == 0 (not assigned), this constraint doesn't apply
                    model.Add(work_var >= min_work).OnlyEnforceIf(x_var)

                    # If assigned, work <= max_work
                    # When work_var == 0 (not assigned), this constraint doesn't apply
                    model.Add(work_var <= max_work).OnlyEnforceIf(x_var)

                    # Note: When employee is not assigned, work_var == 0 (already constrained above),
                    # so min_work and max_work constraints don't interfere

    # Now apply hours constraint per employee per day using distributed minutes
    for emp_id in emp_id_list:
        for day in days:
            total_minutes_worked = model.NewIntVar(
                0, int(request.max_hours_per_day *
                       SCALE_FACTOR * num_car_yards) + HOURS_OVERAGE_BUFFER_MINUTES,
                f'total_minutes_e{emp_id}_d{day}')
            employee_day_minutes[(emp_id, day)] = total_minutes_worked
            model.Add(total_minutes_worked == sum(
                work_minutes.get((emp_id, cy_id, day), 0) for cy_id in cy_id_list
            ))
            max_minutes = int(request.max_hours_per_day * SCALE_FACTOR)
            max_minutes_with_buffer = max_minutes + HOURS_OVERAGE_BUFFER_MINUTES

            overage = model.NewIntVar(
                0, HOURS_OVERAGE_BUFFER_MINUTES, f'overage_e{emp_id}_d{day}')
            model.Add(total_minutes_worked <= max_minutes_with_buffer)
            model.Add(overage >= total_minutes_worked - max_minutes)
            model.Add(overage <= HOURS_OVERAGE_BUFFER_MINUTES)

            hours_overage_penalties.append(overage)

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
                        both = model.NewBoolVar(
                            f'gap_violation_cy{cy_id}_{days[i]}_{days[j]}')
                        model.Add(both <= coverage_vars[i])
                        model.Add(both <= coverage_vars[j])
                        model.Add(both >= coverage_vars[i] +
                                  coverage_vars[j] - 1)
                        gap_penalties.append(both)

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

        for day_a in days:
            for day_b in days:
                diff = abs(day_index[day_a] - day_index[day_b])
                if gap_days > 0 and diff < gap_days:
                    both_linked = model.NewBoolVar(
                        f'linked_gap_violation_{source_id}_{target_id}_{day_a}_{day_b}')
                    model.Add(both_linked <= covered[(source_id, day_a)])
                    model.Add(both_linked <= covered[(target_id, day_b)])
                    model.Add(both_linked >= covered[(source_id, day_a)] +
                              covered[(target_id, day_b)] - 1)
                    linked_gap_penalties.append(both_linked)

    # Constraint 5: Employee availability is already handled above (combined with yard exclusion)

    # Optimized: Combine multiple objective calculations into fewer loops
    # Pre-compute priority weights
    priority_weights = {
        CarYardPriority.HIGH: PRIORITY_WEIGHT_HIGH,
        CarYardPriority.MEDIUM: PRIORITY_WEIGHT_MEDIUM,
        CarYardPriority.LOW: PRIORITY_WEIGHT_LOW
    }

    # Objective 2: Prioritize high-priority car yards (calculated once per yard-day)
    priority_score = []
    for cy_id in cy_id_list:
        cy = car_yards[cy_id]  # Cache the dictionary lookup
        cy_priority_weight = priority_weights.get(
            cy.priority, 1)  # Reuse cached object
        for day in days:
            priority_score.append(covered[(cy_id, day)] * cy_priority_weight)

    # Objective 1: Prefer higher reliability-rated employees (higher rating = better)
    # EmployeeReliabilityRating: EXCELLENT=10, ACCEPTABLE=7, BELOW_AVERAGE=5
    quality_score = []

    # Pre-compute employee ranking values for efficiency
    emp_ranking_values = {
        emp_id: emp.ranking.value for emp_id, emp in employees.items()}

    # Calculate quality score
    for emp_id in emp_id_list:
        emp_ranking = emp_ranking_values[emp_id]
        for cy_id in cy_id_list:
            for day in days:
                # Quality score (employee reliability)
                quality_score.append(
                    x.get((emp_id, cy_id, day), 0) * emp_ranking)

    # Objective 3: Balance workload - minimize difference between max and min shifts
    shifts_per_employee_vars = []
    for emp_id in emp_id_list:
        total = sum(
            x.get((emp_id, cy_id, day), 0) for cy_id in cy_id_list for day in days
        )
        shifts_per_employee_vars.append(total)

    min_shifts = model.NewIntVar(0, num_days * num_car_yards, 'min_shifts')
    max_shifts = model.NewIntVar(0, num_days * num_car_yards, 'max_shifts')

    for total in shifts_per_employee_vars:
        model.Add(min_shifts <= total)
        model.Add(max_shifts >= total)

    workload_balance = max_shifts - min_shifts

    # Combined objective: prioritize high-priority yards, maximize quality, minimize workload imbalance
    total_assignments = sum(
        x_var for x_var in x.values()
    )

    partial_overlap_penalties = []

    # IMPORTANT PERFORMANCE OPTIMIZATION:
    # The partial overlap penalty is extremely expensive if computed for *all* yard pairs
    # (O(days * yards^2 * employees)). We only compute it for yard pairs that are
    # geographically plausible to be scheduled on the same day (within max_radius).
    sorted_cy_ids = sorted(car_yards.keys())
    overlap_pairs: List[Tuple[int, int]] = []
    for idx_a in range(len(sorted_cy_ids)):
        cy_a_id = sorted_cy_ids[idx_a]
        for idx_b in range(idx_a + 1, len(sorted_cy_ids)):
            cy_b_id = sorted_cy_ids[idx_b]
            if abs(car_yards[cy_a_id].north_south_position -
                   car_yards[cy_b_id].north_south_position) <= request.max_radius:
                overlap_pairs.append((cy_a_id, cy_b_id))

    for day in days:
        for cy_a, cy_b in overlap_pairs:
            mix_var = _create_partial_overlap_penalty(
                model, employees, cy_a, cy_b, day, x, invalid_assignments
            )
            partial_overlap_penalties.append(mix_var)

    objective_components = [
        # Highest priority: cover high-priority yards
        sum(priority_score) * OBJECTIVE_PRIORITY_WEIGHT,
        # Second: use better employees
        sum(quality_score) * OBJECTIVE_QUALITY_WEIGHT,
        # Third: balance workload (penalty for imbalance)
        -workload_balance * OBJECTIVE_BALANCE_WEIGHT,
        # Discourage assigning more employees than necessary
        -sum(extra_employee_penalties) * OBJECTIVE_EXTRA_EMPLOYEE_WEIGHT,
        # Mild penalty on total assignments to avoid redundant coverage
        -total_assignments * OBJECTIVE_ASSIGNMENT_PENALTY,
        # Penalize partial overlaps where new employees join existing crews mid-day
        -sum(partial_overlap_penalties) * OBJECTIVE_PARTIAL_OVERLAP_WEIGHT,
        # Penalize distant yard pairs scheduled same day
        -sum(radius_penalties) * OBJECTIVE_RADIUS_PENALTY_WEIGHT,
        # Penalize visits that violate per-week spacing
        -sum(gap_penalties) * OBJECTIVE_GAP_PENALTY_WEIGHT,
        # Penalize linked yards scheduled too close together
        -sum(linked_gap_penalties) * OBJECTIVE_LINKED_GAP_PENALTY_WEIGHT,
        # Penalize exceeding max hours guideline
        -sum(hours_overage_penalties) * OBJECTIVE_MAX_HOURS_OVERAGE_WEIGHT,
        # Penalize underservicing yard hours
        -sum(hours_shortfall_penalties) * OBJECTIVE_HOURS_SHORTFALL_WEIGHT
    ]

    model.Maximize(sum(objective_components))

    # Solve
    logger.info("Starting CP-SAT solver")
    logger.debug(f"Solver timeout: {DEFAULT_SOLVER_TIMEOUT_SECONDS} seconds")
    logger.debug(f"Solver workers: {DEFAULT_SOLVER_NUM_WORKERS}")

    # Log model statistics before solving
    logger.debug(
        f"Model has {len(x)} decision variables (employee-yard-day assignments)")
    logger.debug(
        f"Model has {len(covered)} coverage variables (yard-day coverage)")
    logger.debug(
        f"Total employees: {num_employees}, Total yards: {num_car_yards}, Total days: {num_days}")

    # Create a hash of key input data for comparison
    import hashlib
    input_data_str = json.dumps({
        "employee_count": num_employees,
        "yard_count": num_car_yards,
        "day_count": num_days,
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
    active_employees = [
        emp for emp in employees.values() if emp.available_days]
    num_active_employees = len(active_employees)
    inactive_employees = [
        emp for emp in employees.values() if not emp.available_days]

    total_yard_days = len(car_yards) * len(days)
    # Note: min/max_employees_needed is just for logging - each yard has its own requirements
    min_employees_needed = sum(cy.min_employees for cy in car_yards.values())
    max_employees_needed = sum(cy.max_employees for cy in car_yards.values())

    logger.info(
        f"Feasibility check: {num_employees} total employees ({num_active_employees} active, {len(inactive_employees)} with no available days), {total_employee_days_available} total employee-days available")
    logger.info(
        f"Coverage needed: {num_car_yards} yards × {num_days} days = {total_yard_days} yard-days")
    logger.info(
        f"Employee availability: {[(e.id, e.name, len(e.available_days), [d.value for d in e.available_days]) for e in employees.values()]}")
    logger.debug(
        f"Active employees: {[e.id for e in active_employees]}")
    if inactive_employees:
        logger.debug(
            f"Inactive employees (no available days): {[e.id for e in inactive_employees]}")
    logger.debug(
        f"Employee requirements across all yards (sum): min={min_employees_needed}, max={max_employees_needed} (each yard has its own min-max)")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = DEFAULT_SOLVER_TIMEOUT_SECONDS
    solver.parameters.num_search_workers = max(1, DEFAULT_SOLVER_NUM_WORKERS)
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
            f"  - Not enough active employees available (have {num_active_employees} active employees out of {num_employees} total)")
        logger.error(
            f"  - Employee availability too restrictive (total {total_employee_days_available} employee-days from {num_active_employees} active employees)")
        logger.error(
            f"  - Yard requirements: {num_car_yards} yards with individual min-max employee requirements (not per assignment, but per yard)")
        logger.error(
            f"  - Max hours per day too restrictive ({request.max_hours_per_day} hours)")
        # Check for employees with no availability (informational only - they simply won't be assigned)
        no_availability = [
            e for e in employees.values() if not e.available_days]
        if no_availability:
            logger.info(
                f"  - Employees with no available days (will not be assigned): {[(e.id, e.name) for e in no_availability]}")
    elif status == cp_model.UNKNOWN:
        logger.warning(
            "Solver returned UNKNOWN - may have timed out or hit resource limits")
        logger.warning(
            f"  - Timeout was {DEFAULT_SOLVER_TIMEOUT_SECONDS} seconds")
        logger.warning(
            f"  - Actual solve time: {solver.WallTime():.2f} seconds")

    # Build response (same as before)
    # Optimized: Only iterate through assignments where solver.Value == 1
    # Use list comprehension to build raw_assignments more efficiently
    raw_assignments = []
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        # Optimized: Build assignments list directly from solver results
        # Only check assignments that are actually set to 1
        for (emp_id, cy_id, day), x_var in x.items():
            if solver.Value(x_var) == 1:
                emp = employees[emp_id]
                cy = car_yards[cy_id]
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
        # Optimized: Build dictionaries directly from raw_assignments
        shifts_count = {emp_id: 0 for emp_id in emp_id_list}
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
        # Optimized: Only process work_minutes where there's an actual assignment
        actual_work_hours: Dict[Tuple[int, int, DayOfWeek], float] = {}
        # Only process work_minutes for assignments that exist (where x == 1)
        for assignment_data in raw_assignments:
            emp_id = assignment_data["employee_id"]
            cy_id = assignment_data["car_yard_id"]
            day = assignment_data["day"]
            work_var = work_minutes.get((emp_id, cy_id, day))
            if work_var is not None:
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
                detail += f"Note: {len(no_availability)} employee(s) have no available days and will not be assigned: {[e.name for e in no_availability]}. "
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
        # Re-raise as ValidationError to be handled by the exception handler
        raise
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
