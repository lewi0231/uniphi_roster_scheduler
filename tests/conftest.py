
# Fixtures for reusable test data
from datetime import date, time
from src.scheduler.rostering_api import CarYard, CarYardPriority, CarYardRegion, DayOfWeek, Employee, EmployeeReliabilityRating
import pytest


@pytest.fixture
def sample_employees():
    return [
        Employee(
            id=1,
            name="Chris",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY,
                            DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
        ),
        Employee(
            id=2,
            name="Vashaal",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY,
                            DayOfWeek.TUESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
        ),
        Employee(
            id=3,
            name="Paul",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY],
            not_region=CarYardRegion.SOUTH
        ),
        Employee(
            id=4,
            name="Nitish",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
        ),
        Employee(
            id=5,
            name="Sam",
            ranking=EmployeeReliabilityRating.ACCEPTABLE,
            available_days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
        ),
        Employee(
            id=6,
            name="Sanskar",
            ranking=EmployeeReliabilityRating.EXCELLENT,
            available_days=[DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY,
                            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
        ),
    ]


@pytest.fixture
def sample_car_yards():
    return [
        CarYard(id=1, name="Adrien Brian", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=4, hours_required=8.0, region=CarYardRegion.CENTRAL, per_week=(2, 2)),
        CarYard(id=2, name="Hillcrest Used/New", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=3, hours_required=7.5,  required_days=[DayOfWeek.THURSDAY], region=CarYardRegion.NORTH),
        CarYard(id=4, name="Eblen Suburu", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, hours_required=3.0, region=CarYardRegion.CENTRAL, per_week=(2, 2)),
        CarYard(id=5, name="Reynella Kia", priority=CarYardPriority.MEDIUM,
                min_employees=2, max_employees=4, hours_required=6.0, region=CarYardRegion.SOUTH, linked_yard=(6, 1)),
        CarYard(id=6, name="Reynella All", priority=CarYardPriority.LOW,
                min_employees=3, max_employees=4, hours_required=12.0, region=CarYardRegion.SOUTH),

        CarYard(id=8, name="Stillwell Ford", priority=CarYardPriority.LOW,
                min_employees=1, max_employees=2, hours_required=2.0, region=CarYardRegion.CENTRAL),
        CarYard(id=9, name="EasyAuto123 Tender", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=4, hours_required=8.0, required_days=[DayOfWeek.MONDAY], region=CarYardRegion.CENTRAL, startTime=time(hour=8, minute=30)),
        CarYard(id=10, name="EasyAuto123 Warehouse", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=3, hours_required=2.0, required_days=[DayOfWeek.FRIDAY], region=CarYardRegion.CENTRAL, startTime=time(hour=8, minute=30)),
        CarYard(id=11, name="Main North Toyota", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=3, hours_required=6.0, required_days=[DayOfWeek.FRIDAY], region=CarYardRegion.NORTH),
        CarYard(id=12, name="MG Reynella", priority=CarYardPriority.HIGH,
                min_employees=1, max_employees=2, hours_required=5.0, required_days=[DayOfWeek.THURSDAY], region=CarYardRegion.SOUTH),
    ]


@pytest.fixture
def sample_days():
    return [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
