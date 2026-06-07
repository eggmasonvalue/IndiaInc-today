from indiainc_today.xbrl_parser import XBRLParser
from nse import NSE


def test_parse_xml_content():
    # Setup mock/dummy NSE client
    nse = NSE(download_folder=".", server=False)
    parser = XBRLParser(nse)

    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <xbrl xmlns="http://www.xbrl.org/2003/instance">
        <identifier>RAILTEL</identifier>
        <NameOfTheCompany>RAILTEL CORPORATION OF INDIA LIMITED</NameOfTheCompany>
        <TypeOfEvent>Bagging/Receiving of orders/contracts</TypeOfEvent>
        <AmountOfTheOrdersOrContracts>413200000</AmountOfTheOrdersOrContracts>
        <WhetherTheAgreementWouldFallWithinRelatedPartyTransactions>false</WhetherTheAgreementWouldFallWithinRelatedPartyTransactions>
        <SomeFloatValue>12.34</SomeFloatValue>
        <SomeEmptyField></SomeEmptyField>
    </xbrl>
    """

    fields = parser.parse_xml_content(xml_data)

    # Check that blocklisted fields are omitted
    assert "identifier" not in fields
    assert "NameOfTheCompany" not in fields

    # Check present fields
    assert fields["TypeOfEvent"] == "Bagging/Receiving of orders/contracts"

    # Check type conversions
    assert fields["AmountOfTheOrdersOrContracts"] == 413200000
    assert isinstance(fields["AmountOfTheOrdersOrContracts"], int)

    assert fields["WhetherTheAgreementWouldFallWithinRelatedPartyTransactions"] is False
    assert isinstance(
        fields["WhetherTheAgreementWouldFallWithinRelatedPartyTransactions"], bool
    )

    assert fields["SomeFloatValue"] == 12.34
    assert isinstance(fields["SomeFloatValue"], float)

    # Check empty fields are omitted
    assert "SomeEmptyField" not in fields
