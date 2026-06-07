from unittest.mock import patch
from indiainc_today.industry import get_company_industry


def test_get_company_industry():
    mock_map = {
        "RELIANCE": ["Energy", "Oil & Gas", "Refineries & Marketing"],
        "TCS": ["IT", "Software", "IT Services"],
    }

    with patch("indiainc_today.industry.get_industry_map", return_value=mock_map):
        assert get_company_industry("RELIANCE") == "Refineries & Marketing"
        assert get_company_industry("TCS") == "IT Services"
        assert get_company_industry("reliance ") == "Refineries & Marketing"
        assert get_company_industry("UNKNOWN") is None
        assert get_company_industry("") is None
