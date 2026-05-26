from datetime import date
import pytest
from src.shared_kernel.domain.value_objects import DateRange
from src.shared_kernel.domain.exceptions import BusinessRuleValidationException

def test_valid_date_range():
    start = date(2026, 6, 1)
    end = date(2026, 6, 15)
    date_range = DateRange(start_date=start, end_date=end)
    assert date_range.start_date == start
    assert date_range.end_date == end
    assert date_range.duration_days == 14

def test_invalid_date_range_raises_exception():
    start = date(2026, 6, 15)
    end = date(2026, 6, 1)
    with pytest.raises(BusinessRuleValidationException) as exc_info:
        DateRange(start_date=start, end_date=end)
    assert "La fecha de inicio no puede ser posterior a la fecha de fin" in str(exc_info.value)

def test_date_range_with_non_date_types_raises_exception():
    with pytest.raises(BusinessRuleValidationException) as exc_info:
        DateRange(start_date="2026-06-01", end_date=date(2026, 6, 15)) # type: ignore
    assert "Las fechas de inicio y fin deben ser instancias válidas de fecha" in str(exc_info.value)
