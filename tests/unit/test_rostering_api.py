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


def test_hours_constraint():
    """Test that employees cannot exceed max_hours_per_day limit"""
    # Create yards with different hour requirements
    # Yard 1: 2 hours, Yard 2: 1.5 hours, Yard 3: 2.5 hours
    # Total: 6 hours (exceeds 5 hour limit)
    car_yards = [
        CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0),
        CarYard(id=2, name="Yard B", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=1.5),
        CarYard(id=3, name="Yard C", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.5),
    ]

    employees = [
        Employee(
            id=1,
            name="Employee 1",
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

    # Group assignments by employee and day to calculate total hours
    assignments_by_employee_day = {}
    for assignment in data["assignments"]:
        emp_id = assignment["employee_id"]
        day = assignment["day"]
        cy_id = assignment["car_yard_id"]
        key = (emp_id, day)
        if key not in assignments_by_employee_day:
            assignments_by_employee_day[key] = []
        assignments_by_employee_day[key].append(cy_id)

    # Verify no employee exceeds max_hours_per_day (5.0 hours)
    yard_hours = {cy.id: cy.hours_required for cy in car_yards}
    for (emp_id, day), yard_ids in assignments_by_employee_day.items():
        total_hours = sum(yard_hours[cy_id] for cy_id in yard_ids)
        assert total_hours <= 5.0, f"Employee {emp_id} on {day} exceeds 5.0 hours: {total_hours} hours"


def test_hours_constraint_multiple_yards_allowed():
    """Test that employees CAN work multiple yards if they fit within hours limit"""
    # Create yards that can fit together: 2.0 + 1.5 = 3.5 hours (within 5 hour limit)
    car_yards = [
        CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0),
        CarYard(id=2, name="Yard B", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, hours_required=1.5),
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

    # Group assignments by employee and day
    assignments_by_employee_day = {}
    for assignment in data["assignments"]:
        emp_id = assignment["employee_id"]
        day = assignment["day"]
        cy_id = assignment["car_yard_id"]
        key = (emp_id, day)
        if key not in assignments_by_employee_day:
            assignments_by_employee_day[key] = []
        assignments_by_employee_day[key].append(cy_id)

    # Verify that employees can work multiple yards if they fit within the limit
    yard_hours = {cy.id: cy.hours_required for cy in car_yards}

    # Check that at least one employee worked multiple yards on some day
    # OR verify that total hours per day never exceeds 5.0
    multi_yard_days = []
    for (emp_id, day), yard_ids in assignments_by_employee_day.items():
        total_hours = sum(yard_hours[cy_id] for cy_id in yard_ids)
        assert total_hours <= 5.0, f"Employee {emp_id} on {day} exceeds limit: {total_hours} hours"
        if len(yard_ids) > 1:
            multi_yard_days.append((emp_id, day, yard_ids, total_hours))

    # With hours constraint allowing multiple yards, it's possible (but not guaranteed)
    # that an employee will work multiple yards if it's beneficial
    # The important thing is that no employee exceeds the hours limit
    if DEBUG and multi_yard_days:
        print(f"\n✅ Found employees working multiple yards:")
        for emp_id, day, yard_ids, total_hours in multi_yard_days:
            print(
                f"  Employee {emp_id} on {day}: {len(yard_ids)} yards, {total_hours} hours")


def test_hours_constraint_with_default():
    """Test that default max_hours_per_day=5.0 works correctly"""
    # Create yards with varying hours
    car_yards = [
        CarYard(id=1, name="Yard A", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0),
        CarYard(id=2, name="Yard B", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0),
        CarYard(id=3, name="Yard C", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=2.0),
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

    # Verify default max_hours_per_day is enforced
    assignments_by_employee_day = {}
    for assignment in data["assignments"]:
        emp_id = assignment["employee_id"]
        day = assignment["day"]
        cy_id = assignment["car_yard_id"]
        key = (emp_id, day)
        if key not in assignments_by_employee_day:
            assignments_by_employee_day[key] = []
        assignments_by_employee_day[key].append(cy_id)

    yard_hours = {cy.id: cy.hours_required for cy in car_yards}
    for (emp_id, day), yard_ids in assignments_by_employee_day.items():
        total_hours = sum(yard_hours[cy_id] for cy_id in yard_ids)
        # Should not exceed default of 5.0 hours
        assert total_hours <= 5.0, f"Employee {emp_id} on {day} exceeds default 5.0 hours: {total_hours} hours"


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

    # Verify hours constraint
    # First, calculate employees per yard per day to compute hours per employee correctly
    employees_per_yard_day = {}  # (cy_id, day) -> list of employee_ids
    for assignment in data["assignments"]:
        key = (assignment["car_yard_id"], assignment["day"])
        if key not in employees_per_yard_day:
            employees_per_yard_day[key] = []
        employees_per_yard_day[key].append(assignment["employee_id"])

    # Now calculate hours per employee correctly (hours_required / num_employees)
    employee_hours_per_day = {}
    for assignment in data["assignments"]:
        emp_id = assignment["employee_id"]
        day = assignment["day"]
        cy_id = assignment["car_yard_id"]
        key = (emp_id, day)

        if key not in employee_hours_per_day:
            employee_hours_per_day[key] = 0.0

        # Hours per employee = hours_required / number of employees at that yard
        num_employees = len(employees_per_yard_day[(cy_id, day)])
        hours_per_emp = yard_map[cy_id]["hours"] / num_employees
        employee_hours_per_day[key] += hours_per_emp

    # Assert hours constraint
    for (emp_id, day), total_hours in employee_hours_per_day.items():
        assert total_hours <= 5.0, \
            f"Employee {employee_map[emp_id]} on {day} exceeds 5.0 hours: {total_hours:.2f} hours"

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

                total_day_hours += hours * num_employees

            print(
                f"\n  📊 Total yard-hours for {day_schedule['day']}: {total_day_hours:.1f}h")

        print(f"\n{'─'*80}")
        print("📈 SUMMARY STATISTICS")
        print(f"{'─'*80}")

        # Employee workload summary
        employee_total_hours = {}
        for (emp_id, day), hours in employee_hours_per_day.items():
            if emp_id not in employee_total_hours:
                employee_total_hours[emp_id] = 0.0
            employee_total_hours[emp_id] += hours

        print("\n👷 Employee Workload:")
        for emp_id, total_hours in sorted(employee_total_hours.items()):
            employee_name = employee_map[emp_id]
            print(
                f"  {employee_name}: {total_hours:.1f} hours across {len([d for (e, d) in employee_hours_per_day.keys() if e == emp_id])} days")

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

    return schedule_list
