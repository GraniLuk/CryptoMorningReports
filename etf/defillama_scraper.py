"""DefiLlama ETF data scraper using Selenium for Cloudflare bypass.

This module scrapes ETF flow and AUM data from the DefiLlama ETF dashboard
(https://defillama.com/etfs) using Selenium WebDriver to bypass Cloudflare
protection. The data includes daily flows, total AUM, and individual ETF details
for Bitcoin and Ethereum spot ETFs.

Data Source: DefiLlama aggregates data from Farside Investors
Target URL: https://defillama.com/etfs
Update Frequency: Daily

Key Features:
- Cloudflare bypass using Selenium with headless Chrome
- Extraction of daily stats (BTC/ETH flows and AUM)
- Individual ETF table parsing (ticker, issuer, flows, AUM, volume)
- Robust error handling and logging
- Value parsing for amounts like "$1.2m", "$114.612b"
"""

import re
import time
from datetime import UTC, datetime
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from infra.telegram_logging_handler import app_logger


# Configuration
DEFILLAMA_ETF_URL = "https://defillama.com/etfs"
CLOUDFLARE_WAIT_SECONDS = 10
PAGE_LOAD_TIMEOUT = 20


def parse_flow_value(value_str: str) -> float | None:
    """Parse flow/AUM string values to numeric format.

    Converts strings like "$1.2m", "$114.612b", "$0" to numeric values in dollars.

    Args:
        value_str: String like "$1.2m", "$0", "$114.612b", "1.2M"

    Returns:
        Numeric value in dollars, or None if parsing fails

    Examples:
        >>> parse_flow_value("$1.2m")
        1200000.0
        >>> parse_flow_value("$114.612b")
        114612000000.0
        >>> parse_flow_value("$0")
        0.0
        >>> parse_flow_value("invalid")
        None
    """
    if not value_str:
        return None

    # Handle zero values
    if value_str in ["$0", "0", "$0.0", "0.0"]:
        return 0.0

    try:
        # Remove $ and whitespace, convert to lowercase
        clean = value_str.replace("$", "").replace(",", "").strip().lower()

        if not clean:
            return None

        # Extract number and multiplier (k, m, b)
        match = re.match(r"^([-+]?\d+\.?\d*)([kmb])?$", clean)
        if not match:
            app_logger.debug(f"Could not parse value: {value_str}")
            return None

        number = float(match.group(1))
        multiplier = match.group(2)

        # Apply multiplier mapping
        multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
        factor = multipliers.get(multiplier, 1)
        return number * factor

    except (ValueError, AttributeError) as e:
        app_logger.debug(f"Error parsing value '{value_str}': {e!s}")
        return None


def create_chrome_driver() -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver for scraping.

    Sets up headless Chrome with options optimized for scraping and
    Cloudflare bypass. Automatically manages ChromeDriver installation.

    Returns:
        Configured Chrome WebDriver instance

    Raises:
        WebDriverException: If Chrome driver initialization fails
    """
    chrome_options = Options()

    # Headless mode for background operation
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # User agent to appear as regular Chrome browser
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    # Disable automation flags to avoid detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    use_automation_ext = False
    chrome_options.add_experimental_option("useAutomationExtension", use_automation_ext)

    # Initialize WebDriver with automatic ChromeDriver management
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Set page load timeout
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    return driver


def scrape_defillama_etf() -> list[dict[str, Any]] | None:
    """Scrape ETF data from DefiLlama dashboard.

    Navigates to DefiLlama ETF page using Selenium, waits for Cloudflare
    challenge to complete, then extracts daily stats and ETF table data.

    Returns:
        List of ETF data dictionaries with structure:
        [
            {
                "Ticker": str,      # ETF ticker symbol (e.g., "IBIT")
                "Coin": str,        # Coin type ("BTC" or "ETH")
                "Issuer": str,      # ETF issuer name (e.g., "BlackRock")
                "Price": None,      # Not available from DefiLlama
                "AUM": float,       # Assets Under Management in dollars
                "Flows": float,     # Daily net flows in dollars
                "FlowsChange": None,# Not available from DefiLlama
                "Volume": float,    # Trading volume in dollars
                "Date": int,        # Unix timestamp of data fetch
            },
            ...
        ]
        Returns None if scraping fails.

    Example:
        >>> data = scrape_defillama_etf()
        >>> if data:
        ...     btc_etfs = [e for e in data if e["Coin"] == "BTC"]
        ...     print(f"Found {len(btc_etfs)} BTC ETFs")
    """
    driver = None

    try:
        app_logger.info("Initializing Chrome WebDriver for DefiLlama scraping...")
        driver = create_chrome_driver()

        # Navigate to DefiLlama ETF page
        app_logger.info(f"Navigating to {DEFILLAMA_ETF_URL}...")
        driver.get(DEFILLAMA_ETF_URL)

        # Wait for Cloudflare challenge to complete
        # Cloudflare typically takes 5-10 seconds to verify and redirect
        app_logger.info(f"Waiting {CLOUDFLARE_WAIT_SECONDS}s for Cloudflare challenge...")
        time.sleep(CLOUDFLARE_WAIT_SECONDS)

        # Wait for page content to load
        app_logger.info("Waiting for page content to load...")
        wait = WebDriverWait(driver, PAGE_LOAD_TIMEOUT)

        # Wait for key content to be present (Bitcoin section)
        try:
            wait.until(
                expected_conditions.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(), 'Bitcoin')]"),
                ),
            )
            app_logger.info("✓ Page content loaded successfully")
        except TimeoutException:
            app_logger.error("Timeout waiting for page content - Cloudflare may have blocked us")
            return None

        # Get page source for parsing
        page_source = driver.page_source

        # Verify we bypassed Cloudflare
        if "Just a moment" in page_source or "Checking your browser" in page_source:
            app_logger.error("Still blocked by Cloudflare protection")
            return None

        app_logger.info("✓ Successfully bypassed Cloudflare protection")

        # Extract ETF data from page
        etf_data = parse_defillama_page(page_source)

        if not etf_data:
            app_logger.warning("No ETF data extracted from page")
            return None

        app_logger.info(f"✓ Successfully scraped {len(etf_data)} ETF records from DefiLlama")
        return etf_data  # noqa: TRY300

    except WebDriverException as e:
        app_logger.error(f"WebDriver error during scraping: {e!s}")
        return None
    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Unexpected error during DefiLlama scraping: {e!s}")
        return None
    finally:
        # Always close the browser
        if driver:
            try:
                driver.quit()
                app_logger.debug("Chrome WebDriver closed")
            except Exception as e:  # noqa: BLE001
                app_logger.debug(f"Error closing WebDriver: {e!s}")


def parse_defillama_page(page_source: str) -> list[dict[str, Any]] | None:
    """Parse ETF data from DefiLlama page HTML.

    Extracts daily stats (flows and AUM for BTC/ETH) and individual ETF
    table data from the page HTML.

    Args:
        page_source: HTML source of the DefiLlama ETF page

    Returns:
        List of ETF data dictionaries or None if parsing fails
    """
    try:
        app_logger.info("Parsing DefiLlama page HTML...")

        # Extract daily stats (flows and AUM)
        daily_stats = parse_daily_stats(page_source)

        if not daily_stats:
            app_logger.warning("Could not extract daily stats from page")
            return None

        app_logger.info(
            f"✓ Parsed daily stats: BTC flows=${daily_stats.get('btc_flows', 0):,.0f}, "
            f"BTC AUM=${daily_stats.get('btc_aum', 0):,.0f}, "
            f"ETH flows=${daily_stats.get('eth_flows', 0):,.0f}, "
            f"ETH AUM=${daily_stats.get('eth_aum', 0):,.0f}",
        )

        # Extract individual ETF data from table
        etf_table_data = parse_etf_table(page_source, daily_stats)

        if not etf_table_data:
            app_logger.warning("Could not extract ETF table data from page")
            # Still return data with daily stats only
            return create_fallback_etf_data(daily_stats)

        app_logger.info(f"✓ Parsed {len(etf_table_data)} ETF records from table")
        return etf_table_data  # noqa: TRY300

    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error parsing DefiLlama page: {e!s}")
        return None


def parse_daily_stats(page_source: str) -> dict[str, float] | None:
    """Parse daily stats (flows and AUM) from page HTML.

    Extracts BTC and ETH daily flows and total AUM from the page.
    The page displays flows and AUM separately for Bitcoin and Ethereum.

    Args:
        page_source: HTML source of the page

    Returns:
        Dictionary with keys: btc_flows, btc_aum, eth_flows, eth_aum
        or None if parsing fails
    """
    try:
        # Look for Bitcoin and Ethereum sections
        # The HTML has values separated by newlines/tags:
        # "Bitcoin" ... "Flows" ... "$1.2m" ... "AUM" ... "$114.612b"
        # "Ethereum" ... "Flows" ... "$0" ... "AUM" ... "$17.183b"

        # Extract Bitcoin section first (ends before "Ethereum")
        btc_section = re.search(
            r"Bitcoin[\s\S]*?Flows[\s\S]*?\$([\d.]+[kmb]?)[\s\S]*?AUM[\s\S]*?\$([\d.]+[kmb]?)[\s\S]*?(?=Ethereum)",
            page_source,
            re.IGNORECASE,
        )

        if not btc_section:
            app_logger.debug("Could not find Bitcoin section in page")
            return None

        # Now extract Ethereum section (starts after Bitcoin stats)
        # Find where Bitcoin AUM value is, then search for Ethereum after that
        btc_aum_pos = btc_section.end()
        remaining_page = page_source[btc_aum_pos:]

        eth_section = re.search(
            r"Ethereum[\s\S]*?Flows[\s\S]*?\$([\d.]+[kmb]?)[\s\S]*?AUM[\s\S]*?\$([\d.]+[kmb]?)",
            remaining_page,
            re.IGNORECASE,
        )

        if not eth_section:
            app_logger.debug("Could not find Ethereum section in page")
            return None

        # Parse values
        btc_flows = parse_flow_value(f"${btc_section.group(1)}")
        btc_aum = parse_flow_value(f"${btc_section.group(2)}")
        eth_flows = parse_flow_value(f"${eth_section.group(1)}")
        eth_aum = parse_flow_value(f"${eth_section.group(2)}")

        return {  # noqa: TRY300
            "btc_flows": btc_flows or 0.0,
            "btc_aum": btc_aum or 0.0,
            "eth_flows": eth_flows or 0.0,
            "eth_aum": eth_aum or 0.0,
        }

    except Exception as e:  # noqa: BLE001
        app_logger.debug(f"Error parsing daily stats: {e!s}")
        return None


def parse_etf_table(
    page_source: str,
    daily_stats: dict[str, float],
) -> list[dict[str, Any]] | None:
    """Parse individual ETF data from JSON embedded in the DefiLlama page.

    The DefiLlama page embeds ETF data as JSON objects in the HTML source.
    Example: {"ticker":"IBIT","timestamp":...,"asset":"bitcoin","issuer":"Blackrock",...}

    Args:
        page_source: HTML source of the page
        daily_stats: Daily stats dictionary with total flows/AUM

    Returns:
        List of ETF data dictionaries or None if parsing fails
    """
    try:
        etf_data_list = []
        current_timestamp = int(datetime.now(UTC).timestamp())

        # Regex to find JSON objects with ETF data embedded in HTML
        # Pattern: {"ticker":"XXX",...,"asset":"bitcoin/ethereum",...,"issuer":"YYY",...}
        json_pattern = (
            r'\{"ticker":"([A-Z]+)"[^}]*"asset":"(bitcoin|ethereum)"'
            r'[^}]*"issuer":"([^"]+)"[^}]*"aum":([0-9.]+)[^}]*"volume":([0-9.]+)[^}]*\}'
        )

        matches = re.finditer(json_pattern, page_source)

        for match in matches:
            ticker = match.group(1)
            asset = match.group(2)
            issuer = match.group(3)
            aum_value = float(match.group(4))
            volume_value = float(match.group(5))

            # Map asset to coin
            coin = "BTC" if asset == "bitcoin" else "ETH"

            # Create ETF record
            etf_data = {
                "ticker": ticker,
                "coin": coin,
                "issuer": issuer,
                "price": None,  # Not available from DefiLlama
                "aum": aum_value,
                "flows": 0.0,  # Individual flows not in JSON, only daily totals
                "flowsChange": None,
                "volume": volume_value,
                "date": current_timestamp,
            }

            etf_data_list.append(etf_data)

        if etf_data_list:
            app_logger.info(f"✓ Parsed {len(etf_data_list)} individual ETF records from JSON")
            return etf_data_list

        # Fallback to summary data if no ETFs found
        app_logger.warning("Could not parse individual ETF data - using summary data")
        return create_fallback_etf_data(daily_stats)

    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error in parse_etf_table: {e!s}")
        return create_fallback_etf_data(daily_stats)




def create_fallback_etf_data(daily_stats: dict[str, float]) -> list[dict[str, Any]]:
    """Create fallback ETF data using only daily stats.

    When individual ETF data cannot be extracted, this creates summary
    records for BTC and ETH using the total flows and AUM.

    Args:
        daily_stats: Daily stats with btc_flows, btc_aum, eth_flows, eth_aum

    Returns:
        List with two summary ETF records (BTC and ETH)
    """
    current_timestamp = int(datetime.now(UTC).timestamp())

    return [
        {
            "Ticker": "BTC_TOTAL",
            "Coin": "BTC",
            "Issuer": "Multiple",
            "Price": None,
            "AUM": daily_stats.get("btc_aum", 0.0),
            "Flows": daily_stats.get("btc_flows", 0.0),
            "FlowsChange": None,
            "Volume": None,
            "Date": current_timestamp,
        },
        {
            "Ticker": "ETH_TOTAL",
            "Coin": "ETH",
            "Issuer": "Multiple",
            "Price": None,
            "AUM": daily_stats.get("eth_aum", 0.0),
            "Flows": daily_stats.get("eth_flows", 0.0),
            "FlowsChange": None,
            "Volume": None,
            "Date": current_timestamp,
        },
    ]
