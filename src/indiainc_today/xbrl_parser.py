"""Downloads and parses raw corporate XBRL XML filings from NSE."""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, Union
from nse import NSE
from . import config

logger = logging.getLogger(__name__)


class XBRLParser:
    """Parser for corporate XBRL XML filings."""

    def __init__(self, nse_client: NSE) -> None:
        """Initialize parser with an NSE client session.

        Args:
            nse_client: The shared NSE client instance for downloads.
        """
        self.nse = nse_client

    def parse_xml_content(
        self, xml_content: str
    ) -> Dict[str, Union[str, int, float, bool]]:
        """Parse raw XML content, filtering and converting data types.

        Args:
            xml_content: Raw XBRL XML string.

        Returns:
            A dictionary of parsed tag-value pairs.
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML string: {e}")
            return {}

        fields: Dict[str, Union[str, int, float, bool]] = {}

        for elem in root.iter():
            # Extract tag name without namespace
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Skip metadata/boilerplate tags from blocklist
            if tag in config.XBRL_FIELD_BLOCKLIST:
                continue

            text = (elem.text or "").strip()
            if not text:
                continue

            # Only capture the first occurrence of a tag to preserve document order hierarchy
            if tag not in fields:
                # Type conversion
                # 1. Booleans
                if text.lower() == "true":
                    fields[tag] = True
                elif text.lower() == "false":
                    fields[tag] = False
                # 2. Integers
                elif text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
                    fields[tag] = int(text)
                # 3. Floats
                else:
                    try:
                        # Handle cases like "123.45" or "-123.45"
                        fields[tag] = float(text)
                    except ValueError:
                        # Fallback to original string
                        fields[tag] = text

        return fields

    def download_and_parse(self, url: str) -> Dict[str, Union[str, int, float, bool]]:
        """Download XBRL XML from URL and parse it.

        Args:
            url: The absolute HTTP/HTTPS URL of the XBRL XML file.

        Returns:
            A dictionary of parsed tag-value pairs, or empty dict if failed.
        """
        try:
            logger.info(f"Downloading XBRL XML from {url}")
            response = self.nse._req(url)
            xml_content = response.content.decode("utf-8", errors="replace")
            return self.parse_xml_content(xml_content)
        except Exception as e:
            logger.error(f"Error downloading or parsing XBRL from {url}: {e}")
            return {}
