
# Fixtures for reusable test data
from src.scheduler.rostering_api import CarYard, CarYardPriority, DayOfWeek, Employee, EmployeeReliabilityRating
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
                            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
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
                min_employees=2, max_employees=4, hours_required=10.0),
        CarYard(id=2, name="Hillcrest Used", priority=CarYardPriority.HIGH,
                min_employees=2, max_employees=3, hours_required=5.0),
        CarYard(id=3, name="Hillcrest New", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, hours_required=2.5),
        CarYard(id=4, name="Eblen Suburu", priority=CarYardPriority.MEDIUM,
                min_employees=1, max_employees=2, hours_required=3.0),
        CarYard(id=5, name="Reynella Kia", priority=CarYardPriority.MEDIUM,
                min_employees=2, max_employees=4, hours_required=6.0),
        CarYard(id=6, name="Reynella Isuzu", priority=CarYardPriority.LOW,
                min_employees=1, max_employees=2, hours_required=1.5),
        CarYard(id=7, name="Reynella Geely", priority=CarYardPriority.LOW,
                min_employees=1, max_employees=2, hours_required=3.0),
        CarYard(id=8, name="Stillwell Ford", priority=CarYardPriority.LOW,
                min_employees=1, max_employees=2, hours_required=2.0),
    ]


@pytest.fixture
def sample_days():
    return [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
