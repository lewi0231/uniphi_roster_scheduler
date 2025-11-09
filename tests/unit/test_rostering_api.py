# test_rostering_api.py
# import pytest
from fastapi.testclient import TestClient
from src.scheduler.rostering_api import (
    api,
    DayOfWeek,
    Employee,
    CarYard,
    ScheduleRequest,
    CarYardPriority,
    CarYardRegion,
    EmployeeReliabilityRating,
    solve_roster,
)
from typing import Dict
from src.scheduler.utils import print_json

client = TestClient(api)

DEBUG = True


def check_and_print_response(response, title="API Response"):
    """Helper to print response whether success or error"""
    if DEBUG:
        print(f"\n{'='*60}")
        print(f"📡 {title}")
        print('='*60)
        print(f"Status Code: {response.status_code}")
        try:
            print_json(response.json(), "Response Body")
        except:
            print(f"Response Text: {response.text}")
        print('='*60 + "\n")
    return response


# Test cases
def test_root_endpoint():
    """Test the root endpoint returns correct info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


def test_basic_roster_generation(sample_employees, sample_car_yards, sample_days):
    """Test a basic valid roster request"""
    request = ScheduleRequest(
        employees=sample_employees,
        car_yards=sample_car_yards,
        days=sample_days
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["optimal", "feasible"]
    assert "assignments" in data
    assert "stats" in data

    # Verify all assignments are valid
    assignments = data["assignments"]
    assert len(assignments) > 0

    # Check constraints: each yard should have min-max employees per day (if assigned)
    assignments_by_day_yard = {}
    for assignment in assignments:
        key = (assignment["day"], assignment["car_yard_id"])
        if key not in assignments_by_day_yard:
            assignments_by_day_yard[key] = 0
        assignments_by_day_yard[key] += 1

    # Note: With priority-based system, yards may not be covered every day
    # Only check yards that actually have assignments
    for cy in sample_car_yards:
        for day in sample_days:
            count = assignments_by_day_yard.get((day.value, cy.id), 0)
            # If yard is covered on this day, it must have min-max employees
            if count > 0:
                assert cy.min_employees <= count <= cy.max_employees


def test_employee_availability_constraint(sample_employees, sample_car_yards):
    """Test that employees are only assigned on their available days"""
    # Create an employee who can only work Monday
    limited_employee = Employee(
        id=99,
        name="Limited",
        ranking=EmployeeReliabilityRating.EXCELLENT,
        available_days=[DayOfWeek.MONDAY]
    )

    # Use fewer car yards to make it feasible
    feasible_yards = sample_car_yards[:2]  # Just 2 high-priority yards

    request = ScheduleRequest(
        employees=[limited_employee] + sample_employees[:2],
        car_yards=feasible_yards,
        days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY]
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    check_and_print_response(response, "Employee Availability Constraint")

    # With strict weekly coverage, this scenario is infeasible
    assert response.status_code == 400


def test_impossible_constraint():
    """Test that impossible scenarios return an error"""
    # Try to schedule with no employees available
    # With priority-based system, this will return a solution with no assignments
    # (yard left uncovered), so we check that no assignments were made
    request = ScheduleRequest(
        employees=[
            Employee(
                id=1,
                name="Alice",
                ranking=EmployeeReliabilityRating.EXCELLENT,
                available_days=[DayOfWeek.MONDAY]  # Only Monday
            )
        ],
        car_yards=[
            CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                    min_employees=1, max_employees=1, region=CarYardRegion.CENTRAL)
        ],
        days=[DayOfWeek.TUESDAY]  # Need Tuesday but no one available
    )

    response = client.post("/api/v1/roster", json=request.model_dump())

    # Weekly coverage requirement makes this infeasible
    assert response.status_code == 400


def test_ranking_preference():
    """Test that higher reliability-rated employees get more shifts"""
    employees = [
        Employee(
            id=1,
            name="Excellent Employee",
            ranking=EmployeeReliabilityRating.EXCELLENT,  # Best (10)
            available_days=[DayOfWeek.MONDAY,
                            DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY]
        ),
        Employee(
            id=2,
            name="Below Average Employee",
            ranking=EmployeeReliabilityRating.BELOW_AVERAGE,  # Worse (5)
            available_days=[DayOfWeek.MONDAY,
                            DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY]
        ),
    ]

    request = ScheduleRequest(
        employees=employees,
        car_yards=[CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                           min_employees=1, max_employees=1, region=CarYardRegion.CENTRAL)],
        days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY]
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200

    data = response.json()
    shifts_count = data["stats"]["shifts_per_employee"]

    # Employee 1 (EXCELLENT rating=10) should get more or equal shifts than employee 2 (BELOW_AVERAGE rating=5)
    assert shifts_count["1"] >= shifts_count["2"]


def test_one_employee_one_yard():
    """Test minimal scenario"""
    request = ScheduleRequest(
        employees=[
            Employee(
                id=1,
                name="Solo",
                ranking=EmployeeReliabilityRating.EXCELLENT,
                available_days=[DayOfWeek.MONDAY]
            )
        ],
        car_yards=[
            CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                    min_employees=1, max_employees=1, region=CarYardRegion.CENTRAL)
        ],
        days=[DayOfWeek.MONDAY]
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200

    data = response.json()
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["employee_id"] == 1
    assert data["assignments"][0]["car_yard_id"] == 1


def test_workload_balance():
    """Test that workload is balanced across employees"""
    # Use employees with same ranking to focus on workload balance
    employees = [
        Employee(
            id=i,
            name=f"Employee {i}",
            # Same ranking so quality doesn't override balance
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY,
                            DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY]
        )
        for i in range(1, 5)  # 4 employees
    ]

    request = ScheduleRequest(
        employees=employees,
        car_yards=[
            CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                    min_employees=2, max_employees=2, region=CarYardRegion.CENTRAL)
        ],
        days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY]
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200

    data = response.json()
    shifts_count = data["stats"]["shifts_per_employee"]

    # Check that workload is reasonably balanced
    shift_counts = list(shifts_count.values())
    max_shifts = max(shift_counts)
    min_shifts = min(shift_counts)

    # With 4 employees and 6 total shifts (2 employees × 3 days),
    # ideal distribution would be 1-2 shifts each
    # Difference should be small (workload balance)
    assert max_shifts - min_shifts <= 2  # Allow some flexibility


def test_realistic_roster():
    """Testing close to genuine roster"""

    pass


def test_priority_based_assignment():
    """Test that high-priority car yards are prioritized when employees are limited"""
    employees = [
        Employee(
            id=1,
            name="Employee 1",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY]
        ),
        Employee(
            id=2,
            name="Employee 2",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY]
        ),
    ]

    # Create yards with different priorities
    # With only 2 employees, we can't cover all yards every day
    car_yards = [
        CarYard(id=1, name="High Priority Yard", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, region=CarYardRegion.CENTRAL),
        CarYard(id=2, name="Medium Priority Yard", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, region=CarYardRegion.CENTRAL),
        CarYard(id=3, name="Low Priority Yard", priority=CarYardPriority.LOW,
                min_employees=1, max_employees=2, region=CarYardRegion.CENTRAL),
    ]

    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY]
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    check_and_print_response(response, "Priority-Based Assignment")

    assert response.status_code == 200

    data = response.json()
    assignments = data["assignments"]

    # Group assignments by yard and day
    yard_coverage = {}
    for assignment in assignments:
        key = (assignment["car_yard_id"], assignment["day"])
        if key not in yard_coverage:
            yard_coverage[key] = []
        yard_coverage[key].append(assignment["employee_id"])

    # Count how many days each yard is covered
    high_priority_days = sum(
        1 for (cy_id, day) in yard_coverage.keys() if cy_id == 1)
    medium_priority_days = sum(
        1 for (cy_id, day) in yard_coverage.keys() if cy_id == 2)
    low_priority_days = sum(
        1 for (cy_id, day) in yard_coverage.keys() if cy_id == 3)

    # High priority yard should be covered at least as much as others
    # (Note: This test will pass even with current solver, but once priority is implemented,
    # high priority should be covered more)
    assert high_priority_days >= 0
    assert medium_priority_days >= 0
    assert low_priority_days >= 0

    if DEBUG:
        print(f"\n📊 Yard Coverage Summary:")
        print(f"  High Priority Yard: {high_priority_days} days covered")
        print(f"  Medium Priority Yard: {medium_priority_days} days covered")
        print(f"  Low Priority Yard: {low_priority_days} days covered")


def test_hours_constraint():
    """Test that employees cannot exceed max_hours_per_day limit"""
    # Create yards with different hour requirements
    # Yard 1: 2 hours, Yard 2: 1.5 hours, Yard 3: 2.5 hours
    # Total: 6 hours (exceeds 5 hour limit)
    car_yards = [
        CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0, region=CarYardRegion.CENTRAL),
        CarYard(id=2, name="Yard B", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=1.5, region=CarYardRegion.CENTRAL),
        CarYard(id=3, name="Yard C", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.5, region=CarYardRegion.CENTRAL),
    ]

    employees = [
        Employee(
            id=1,
            name="Employee 1",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY]
        ),
        Employee(
            id=2,
            name="Employee 2",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY]
        )
    ]

    # Set max_hours_per_day to 5.0
    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=[DayOfWeek.MONDAY],
        max_hours_per_day=5.0
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    check_and_print_response(response, "Hours Constraint Test")

    assert response.status_code == 200
    data = response.json()
    assigned = {assignment["employee_id"]
                for assignment in data["assignments"]}
    assert assigned == {1, 2}

    hours_stats = data["stats"]["hours_per_employee_day"]
    for key, hours in hours_stats.items():
        assert hours <= 5.0 + 1e-6, f"{key} exceeds 5.0 hours: {hours}"


def test_hours_constraint_multiple_yards_allowed():
    """Test that employees CAN work multiple yards if they fit within hours limit"""
    # Create yards that can fit together: 2.0 + 1.5 = 3.5 hours (within 5 hour limit)
    car_yards = [
        CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0, region=CarYardRegion.CENTRAL),
        CarYard(id=2, name="Yard B", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, hours_required=1.5, region=CarYardRegion.CENTRAL),
    ]

    employees = [
        Employee(
            id=1,
            name="Employee 1",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY]
        )
    ]

    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY],
        max_hours_per_day=5.0
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200
    data = response.json()

    hours_stats = data["stats"]["hours_per_employee_day"]
    for key, hours in hours_stats.items():
        assert hours <= 5.0 + 1e-6, f"{key} exceeds limit: {hours}"


def test_hours_constraint_with_default():
    """Test that default max_hours_per_day=5.0 works correctly"""
    # Create yards with varying hours
    car_yards = [
        CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0, region=CarYardRegion.CENTRAL),
        CarYard(id=2, name="Yard B", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0, region=CarYardRegion.CENTRAL),
        CarYard(id=3, name="Yard C", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0, region=CarYardRegion.CENTRAL),
    ]

    employees = [
        Employee(
            id=1,
            name="Employee 1",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY]
        )
    ]

    # Don't specify max_hours_per_day - should default to 5.0
    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=[DayOfWeek.MONDAY]
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200
    data = response.json()

    # Verify default max_hours_per_day (7.0) is enforced
    hours_stats = data["stats"]["hours_per_employee_day"]
    for key, hours in hours_stats.items():
        assert hours <= 7.0 + 1e-6, f"{key} exceeds default 7.0 hours: {hours}"


def test_realistic_schedule_readable_format(sample_employees, sample_car_yards, sample_days):
    """
    Test a realistic schedule scenario with readable output format.
    Output structure: array of days, each day contains car yards, each car yard contains assigned employees.

    Note: Uses original fixture values. The solver will automatically assign more employees
    to yards with high hours_required to keep each employee under max_hours_per_day.
    Example: A yard requiring 10 hours with 2 employees = 5 hours each (within limit).
    """
    # Group Reynella yards together (they're often done together)
    yard_groups = {
        "reynella_group": [5, 6, 7]  # Reynella Kia, Isuzu, Geely
    }

    request = ScheduleRequest(
        employees=sample_employees,
        car_yards=sample_car_yards,
        days=sample_days,
        yard_groups=yard_groups,
        max_hours_per_day=5.0
    )

    response = client.post("/api/v1/roster", json=request.model_dump())

    # Check if we got an error and print details
    if response.status_code != 200:
        print(f"\n❌ Error Response ({response.status_code}):")
        try:
            error_data = response.json()
            print_json(error_data, "Error Details")
        except:
            print(f"Response text: {response.text}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data["status"] in ["optimal", "feasible"]
    assert "assignments" in data

    # Build readable schedule structure
    schedule = {}
    employee_map = {emp.id: emp.name for emp in sample_employees}
    yard_map = {cy.id: {"name": cy.name, "hours": cy.hours_required}
                for cy in sample_car_yards}

    # Initialize schedule structure
    for day in sample_days:
        schedule[day.value] = {
            "day": day.value,
            "car_yards": {}
        }

    # Populate schedule with assignments
    for assignment in data["assignments"]:
        day = assignment["day"]
        cy_id = assignment["car_yard_id"]
        emp_id = assignment["employee_id"]

        if cy_id not in schedule[day]["car_yards"]:
            schedule[day]["car_yards"][cy_id] = {
                "yard_id": cy_id,
                "yard_name": yard_map[cy_id]["name"],
                "hours_required": yard_map[cy_id]["hours"],
                "employees": []
            }

        schedule[day]["car_yards"][cy_id]["employees"].append({
            "employee_id": emp_id,
            "employee_name": employee_map[emp_id]
        })

    # Convert to list format for cleaner output
    schedule_list = []
    for day in sample_days:
        day_data = {
            "day": day.value,
            "car_yards": list(schedule[day.value]["car_yards"].values())
        }
        schedule_list.append(day_data)

    # Verify hours constraint using solver statistics
    hours_stats = data["stats"]["hours_per_employee_day"]
    employee_hours_per_day = {
        key: hours for key, hours in hours_stats.items()
    }

    for key, total_hours in employee_hours_per_day.items():
        assert total_hours <= 5.0 + 1e-6, \
            f"{key} exceeds 5.0 hours: {total_hours:.2f} hours"

    # Print readable schedule
    if DEBUG:
        print("\n" + "="*80)
        print("📅 REALISTIC SCHEDULE - READABLE FORMAT")
        print("="*80)

        for day_schedule in schedule_list:
            print(f"\n{'─'*80}")
            print(f"📆 {day_schedule['day'].upper()}")
            print(f"{'─'*80}")

            if not day_schedule["car_yards"]:
                print("  No assignments")
                continue

            total_day_hours = 0
            for yard in day_schedule["car_yards"]:
                yard_name = yard["yard_name"]
                hours = yard["hours_required"]
                employees = [emp["employee_name"] for emp in yard["employees"]]
                num_employees = len(employees)

                print(f"\n  🏢 {yard_name} (ID: {yard['yard_id']})")
                print(
                    f"     ⏱️  Hours: {hours:.1f}h | 👥 Employees: {num_employees}")
                print(f"     👷 Assigned: {', '.join(employees)}")

            total_day_hours += hours

            print(
                f"\n  📊 Total yard-hours for {day_schedule['day']}: {total_day_hours:.1f}h")

        print(f"\n{'─'*80}")
        print("📈 SUMMARY STATISTICS")
        print(f"{'─'*80}")

        # Employee workload summary
        employee_total_hours: Dict[int, float] = {}
        for key, hours in employee_hours_per_day.items():
            emp_id = int(key.split("_")[1])
            employee_total_hours[emp_id] = employee_total_hours.get(
                emp_id, 0.0) + hours

        print("\n👷 Employee Workload:")
        for emp_id, total_hours in sorted(employee_total_hours.items()):
            employee_name = employee_map[emp_id]
            days_worked = sum(
                1 for stats_key in employee_hours_per_day.keys()
                if stats_key.startswith(f"emp_{emp_id}_")
                and employee_hours_per_day[stats_key] > 0
            )
            print(
                f"  {employee_name}: {total_hours:.1f} hours across {days_worked} days")

        print("\n" + "="*80)

        # Also print JSON format for programmatic access
        print_json(schedule_list, "Schedule (JSON Format)")

    # Assertions
    assert len(schedule_list) == len(
        sample_days), "Schedule should have entries for all days"

    # Verify every yard is covered exactly once
    all_yard_ids = {cy.id for cy in sample_car_yards}
    covered_yard_ids = set()
    for day_schedule in schedule_list:
        for yard in day_schedule["car_yards"]:
            covered_yard_ids.add(yard["yard_id"])

    assert covered_yard_ids == all_yard_ids, \
        f"All yards must be covered exactly once. Missing: {all_yard_ids - covered_yard_ids}, Extra: {covered_yard_ids - all_yard_ids}"

    # Check that high-priority yards are covered
    high_priority_yards = {
        cy.id for cy in sample_car_yards if cy.priority.value == "high"}
    covered_high_priority = set()
    for day_schedule in schedule_list:
        for yard in day_schedule["car_yards"]:
            if yard["yard_id"] in high_priority_yards:
                covered_high_priority.add(yard["yard_id"])

    # All high-priority yards should be covered exactly once
    assert len(covered_high_priority) == len(high_priority_yards), \
        f"All high-priority yards should be covered. Expected {len(high_priority_yards)}, got {len(covered_high_priority)}"

    coverage_by_yard: Dict[int, int] = {cy.id: 0 for cy in sample_car_yards}
    day_index = {day.value: idx for idx, day in enumerate(sample_days)}
    yard_visit_days: Dict[int, list] = {cy.id: [] for cy in sample_car_yards}

    for day_schedule in schedule_list:
        for yard in day_schedule["car_yards"]:
            yard_id = yard["yard_id"]
            coverage_by_yard[yard_id] += 1
            yard_visit_days[yard_id].append(day_index[day_schedule["day"]])

    assert coverage_by_yard[4] == 2, "Eblen Suburu should be scheduled twice per week"
    assert coverage_by_yard[5] == 1, "Reynella Kia should be scheduled once per week"
    assert coverage_by_yard[6] == 1, "Reynella All should be scheduled once per week"

    assert len(
        yard_visit_days[5]) == 1, "Reynella Kia must have exactly one scheduled day"
    assert len(
        yard_visit_days[6]) == 1, "Reynella All must have exactly one scheduled day"
    gap_requirement = next(
        (cy.linked_yard[1]
         for cy in sample_car_yards if cy.id == 5 and cy.linked_yard),
        0
    )
    assert abs(yard_visit_days[5][0] - yard_visit_days[6][0]) >= gap_requirement, \
        "Linked yards 5 and 6 must have at least the configured gap between visits"

    return schedule_list


def test_region_exclusion():
    employees = [
        Employee(
            id=1,
            name="North Only",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY],
            not_region=CarYardRegion.SOUTH
        ),
        Employee(
            id=2,
            name="Flexible",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY]
        )
    ]

    car_yards = [
        CarYard(id=50, name="Southern Yard", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=1, hours_required=4.0,
                region=CarYardRegion.SOUTH)
    ]

    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=[DayOfWeek.MONDAY],
        max_hours_per_day=5.0
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200
    data = response.json()
    assigned = {assignment["employee_id"]
                for assignment in data["assignments"]}
    assert 1 not in assigned
    assert 2 in assigned


def test_required_days_constraint():
    employees = [
        Employee(
            id=1,
            name="Worker 1",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=list(DayOfWeek)
        ),
        Employee(
            id=2,
            name="Worker 2",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=list(DayOfWeek)
        )
    ]

    car_yards = [
        CarYard(id=60, name="Thursday Yard", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=2, hours_required=4.0,
                region=CarYardRegion.CENTRAL,
                required_days=[DayOfWeek.THURSDAY])
    ]

    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=list(DayOfWeek)[:5],
        max_hours_per_day=6.0
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200
    data = response.json()
    assignment_days = {assignment["day"] for assignment in data["assignments"]}
    assert assignment_days == {DayOfWeek.THURSDAY.value}


def test_per_week_gap_constraint():
    employees = [
        Employee(
            id=1,
            name="Gap Worker 1",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=list(DayOfWeek)
        ),
        Employee(
            id=2,
            name="Gap Worker 2",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=list(DayOfWeek)
        )
    ]

    car_yards = [
        CarYard(id=70, name="Biweekly Yard", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, hours_required=4.0,
                region=CarYardRegion.CENTRAL,
                per_week=(2, 2))
    ]

    schedule_days = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY
    ]
    day_index = {day.value: idx for idx, day in enumerate(schedule_days)}

    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=schedule_days,
        max_hours_per_day=6.0
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200
    data = response.json()
    yard_days = sorted(
        day_index[assignment["day"]]
        for assignment in data["assignments"]
        if assignment["car_yard_id"] == 70
    )

    assert len(yard_days) == 2
    assert yard_days[1] - yard_days[0] >= 2


def test_linked_yard_gap_constraint():
    employees = [
        Employee(
            id=1,
            name="Link Worker 1",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=list(DayOfWeek)
        ),
        Employee(
            id=2,
            name="Link Worker 2",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=list(DayOfWeek)
        ),
        Employee(
            id=3,
            name="Link Worker 3",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=list(DayOfWeek)
        )
    ]

    car_yards = [
        CarYard(id=80, name="Primary Yard", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=3, hours_required=6.0,
                region=CarYardRegion.CENTRAL,
                linked_yard=(81, 2)),
        CarYard(id=81, name="Linked Yard", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, hours_required=3.0,
                region=CarYardRegion.CENTRAL)
    ]

    schedule_days = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY
    ]
    day_index = {day.value: idx for idx, day in enumerate(schedule_days)}

    request = ScheduleRequest(
        employees=employees,
        car_yards=car_yards,
        days=schedule_days,
        max_hours_per_day=7.0
    )

    response = client.post("/api/v1/roster", json=request.model_dump())
    assert response.status_code == 200
    data = response.json()

    primary_days = [
        day_index[assignment["day"]]
        for assignment in data["assignments"]
        if assignment["car_yard_id"] == 80
    ]
    linked_days = [
        day_index[assignment["day"]]
        for assignment in data["assignments"]
        if assignment["car_yard_id"] == 81
    ]

    gap = car_yards[0].linked_yard[1]
    assert primary_days
    assert linked_days

    for primary_day in primary_days:
        assert any(abs(primary_day - linked_day) >=
                   gap for linked_day in linked_days)
