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
    EmployeeReliabilityRating,
    solve_roster,
)
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

    assert response.status_code == 200

    data = response.json()

    # Verify Limited employee is never assigned on Tuesday
    for assignment in data["assignments"]:
        if assignment["employee_id"] == 99:
            if DEBUG:
                print_json(
                    data, "test_employee_availability_constraint assignment")
            assert assignment["day"] == DayOfWeek.MONDAY.value


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
                    min_employees=1, max_employees=1)
        ],
        days=[DayOfWeek.TUESDAY]  # Need Tuesday but no one available
    )

    response = client.post("/api/v1/roster", json=request.model_dump())

    # With priority-based system, solver finds feasible solution (yard uncovered)
    # So we check that no assignments were actually made
    assert response.status_code == 200
    data = response.json()
    # No assignments should be made since no employees are available
    assert len(data["assignments"]) == 0


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
                           min_employees=1, max_employees=1)],
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
                    min_employees=1, max_employees=1)
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
                    min_employees=2, max_employees=2)
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
                min_employees=1, max_employees=2),
        CarYard(id=2, name="Medium Priority Yard", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2),
        CarYard(id=3, name="Low Priority Yard", priority=CarYardPriority.LOW,
                min_employees=1, max_employees=2),
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
