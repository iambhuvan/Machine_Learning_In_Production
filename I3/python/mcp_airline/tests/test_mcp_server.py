"""Test MCP server tools via MCP client connection over HTTP."""

import asyncio
import json
import shutil
from pathlib import Path
import pytest
import pytest_asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp_airline.database import AirlineDatabase


# Default server URL - can be overridden with environment variable
SERVER_URL = "http://localhost:3000/mcp"


@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    """Reset the database before each test."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Call reset tool to restore database to initial state
            await session.call_tool("reset", {})
    yield


@pytest.mark.asyncio
async def test_reset_database():
    """Test that the reset tool properly restores database state."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get initial reservation state
            result = await session.call_tool("get_reservation_details", {"reservation_id": "4WQ150"})
            original_reservation = json.loads(result.content[0].text)
            assert "status" not in original_reservation or original_reservation.get("status") != "cancelled"

            # Create and execute a trusted cancellation
            preview_result = await session.call_tool(
                "request_reservation_cancellation",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "reason": "airline cancelled flight",
                },
            )
            preview = json.loads(preview_result.content[0].text)
            await session.call_tool(
                "_trusted_commit_action",
                {"action_id": preview["action_id"]},
            )

            # Verify it's cancelled
            result = await session.call_tool("get_reservation_details", {"reservation_id": "4WQ150"})
            cancelled_reservation = json.loads(result.content[0].text)
            assert cancelled_reservation["status"] == "cancelled"

            # Call reset
            reset_result = await session.call_tool("reset", {})
            assert reset_result.content[0].text == "true"

            # Verify the reservation is back to original state
            result = await session.call_tool("get_reservation_details", {"reservation_id": "4WQ150"})
            restored_reservation = json.loads(result.content[0].text)
            assert "status" not in restored_reservation or restored_reservation.get("status") != "cancelled"
            # Payment history should be back to original length
            assert len(restored_reservation["payment_history"]) == len(original_reservation["payment_history"])


@pytest.mark.asyncio
async def test_list_tools():
    """Test that we can connect and list available tools."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # List all tools
            tools = await session.list_tools()

            # Verify we have tools
            assert len(tools.tools) > 0

            # Check for expected tools
            tool_names = [tool.name for tool in tools.tools]
            assert "list_all_airports" in tool_names
            assert "calculate" in tool_names
            # assert "reset" in tool_names


@pytest.mark.asyncio
async def test_list_all_airports():
    """Test calling list_all_airports tool."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call the tool
            result = await session.call_tool("list_all_airports", {})

            # Verify result
            assert len(result.content) > 0
            assert result.content[0].type == "text"

            # Parse and verify the airport data
            import json
            airports = json.loads(result.content[0].text)
            assert isinstance(airports, list)
            assert len(airports) > 0
            assert "iata" in airports[0]
            assert "city" in airports[0]


@pytest.mark.asyncio
async def test_calculate():
    """Test calling calculate tool."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call the tool
            result = await session.call_tool("calculate", {"expression": "2 + 2"})

            # Verify result
            assert len(result.content) > 0
            assert result.content[0].type == "text"
            assert result.content[0].text == "4"


@pytest.mark.asyncio
async def test_get_user_details():
    """Test calling get_user_details tool with valid user."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call the tool with a valid user ID
            result = await session.call_tool("get_user_details", {"user_id": "mia_li_3668"})

            # Verify result
            assert len(result.content) > 0
            assert result.content[0].type == "text"

            # Parse and verify the user data
            user_data = json.loads(result.content[0].text)
            assert user_data["user_id"] == "mia_li_3668"
            assert user_data["name"]["first_name"] == "Mia"
            assert user_data["name"]["last_name"] == "Li"
            assert "payment_methods" in user_data
            assert "reservations" in user_data


@pytest.mark.asyncio
async def test_get_user_details_invalid():
    """Test calling get_user_details tool with invalid user returns error."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call the tool with an invalid user ID
            result = await session.call_tool("get_user_details", {"user_id": "invalid_user"})

            # Verify we get an error response
            assert len(result.content) > 0
            assert result.content[0].type == "text"
            assert "not found" in result.content[0].text.lower() or "error" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_get_reservation_details():
    """Test getting reservation details."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Get details for an existing reservation
            result = await session.call_tool("get_reservation_details", {"reservation_id": "4WQ150"})

            assert len(result.content) > 0
            assert result.content[0].type == "text"

            reservation = json.loads(result.content[0].text)
            assert reservation["reservation_id"] == "4WQ150"
            assert "user_id" in reservation
            assert "flights" in reservation
            assert "passengers" in reservation


@pytest.mark.asyncio
async def test_search_direct_flight():
    """Test searching for direct flights."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Search for flights from PHL to LGA on 2024-05-16
            result = await session.call_tool(
                "search_direct_flight",
                {"origin": "PHL", "destination": "LGA", "date": "2024-05-16"}
            )

            assert len(result.content) > 0
            assert result.content[0].type == "text"

            flights = json.loads(result.content[0].text)
            assert isinstance(flights, list)
            # Should find at least one flight
            if len(flights) > 0:
                flight = flights[0]
                assert flight["origin"] == "PHL"
                assert flight["destination"] == "LGA"
                assert "flight_number" in flight
                assert "prices" in flight
                assert "available_seats" in flight


@pytest.mark.asyncio
async def test_search_onestop_flight():
    """Test searching for one-stop flights."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Search for one-stop flights
            result = await session.call_tool(
                "search_onestop_flight",
                {"origin": "SFO", "destination": "JFK", "date": "2024-05-20"}
            )

            assert len(result.content) > 0
            assert result.content[0].type == "text"

            flight_pairs = json.loads(result.content[0].text)
            assert isinstance(flight_pairs, list)
            # Each result should be a pair of flights
            if len(flight_pairs) > 0:
                pair = flight_pairs[0]
                assert len(pair) == 2
                assert pair[0]["destination"] == pair[1]["origin"]


@pytest.mark.asyncio
async def test_get_flight_status():
    """Test getting flight status."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get status for a landed flight
            result = await session.call_tool(
                "get_flight_status",
                {"flight_number": "HAT001", "date": "2024-05-01"}
            )

            assert len(result.content) > 0
            assert result.content[0].type == "text"
            assert result.content[0].text == "landed"

            # Get status for an available flight
            result2 = await session.call_tool(
                "get_flight_status",
                {"flight_number": "HAT001", "date": "2024-05-16"}
            )

            assert len(result2.content) > 0
            assert result2.content[0].type == "text"
            assert result2.content[0].text == "available"


@pytest.mark.asyncio
async def test_request_compensation_only_once():
    """Compensation can only be issued once for the same reservation."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "request_compensation",
                {"user_id": "ava_li_8840", "reservation_id": "EJTH83"},
            )
            receipt = json.loads(result.content[0].text)
            assert receipt["verified_action"] is True
            assert receipt["details"]["amount"] == 300

            second = await session.call_tool(
                "request_compensation",
                {"user_id": "ava_li_8840", "reservation_id": "EJTH83"},
            )
            assert "already issued" in second.content[0].text.lower()


def test_compensation_ledger_persists_across_database_restart(tmp_path: Path):
    """The durable compensation ledger should survive database re-instantiation."""
    source_db = Path(__file__).resolve().parents[4] / "data" / "airline" / "db.json"
    copied_db = tmp_path / "db.json"
    shutil.copy(source_db, copied_db)

    first = AirlineDatabase(copied_db)
    first.get_security_state()["compensated_reservations"]["EJTH83"] = "receipt_123"
    first.persist_security_state()

    second = AirlineDatabase(copied_db)
    assert second.get_security_state()["compensated_reservations"]["EJTH83"] == "receipt_123"

    second.reload()
    third = AirlineDatabase(copied_db)
    assert third.get_security_state()["compensated_reservations"] == {}


@pytest.mark.asyncio
async def test_request_compensation_denies_ineligible_user():
    """Ineligible reservations must not receive compensation."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "request_compensation",
                {"user_id": "daiki_lopez_8334", "reservation_id": "E3M58X"},
            )
            assert "not eligible" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_request_cancellation_enforces_policy():
    """Unsafe cancellations should be rejected before any mutation happens."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "request_reservation_cancellation",
                {
                    "user_id": "olivia_smith_4705",
                    "reservation_id": "HVU16N",
                    "reason": "change of plan",
                },
            )
            assert "not allowed by policy" in result.content[0].text.lower()

            unchanged = await session.call_tool(
                "get_reservation_details",
                {"reservation_id": "HVU16N"},
            )
            reservation = json.loads(unchanged.content[0].text)
            assert reservation.get("status") != "cancelled"


@pytest.mark.asyncio
async def test_baggage_update_requires_commit():
    """Baggage charges only apply after the trusted commit step."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            preview_result = await session.call_tool(
                "request_baggage_update",
                {
                    "user_id": "olivia_smith_4705",
                    "reservation_id": "HVU16N",
                    "total_baggages": 3,
                    "nonfree_baggages": 2,
                    "payment_id": "credit_card_1070466",
                },
            )
            preview = json.loads(preview_result.content[0].text)
            assert preview["requires_confirmation"] is True

            before = await session.call_tool(
                "get_reservation_details",
                {"reservation_id": "HVU16N"},
            )
            reservation_before = json.loads(before.content[0].text)
            assert reservation_before["total_baggages"] == 1
            assert reservation_before["nonfree_baggages"] == 0

            commit_result = await session.call_tool(
                "_trusted_commit_action",
                {"action_id": preview["action_id"]},
            )
            receipt = json.loads(commit_result.content[0].text)
            assert receipt["verified_action"] is True
            assert receipt["details"]["additional_charge"] == 100

            after = await session.call_tool(
                "get_reservation_details",
                {"reservation_id": "HVU16N"},
            )
            reservation_after = json.loads(after.content[0].text)
            assert reservation_after["total_baggages"] == 3
            assert reservation_after["nonfree_baggages"] == 2


@pytest.mark.asyncio
async def test_send_certificate():
    """Direct certificate issuance should be disabled in the hardened server."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "send_certificate",
                {"user_id": "mia_li_3668", "amount": 100.0}
            )
            assert "disabled" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_transfer_to_human_agents():
    """Test transfer to human agents."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "transfer_to_human_agents",
                {"summary": "Customer needs help with complex itinerary"}
            )

            assert len(result.content) > 0
            assert result.content[0].type == "text"
            assert "transfer" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_cancel_reservation():
    """Direct cancellation should be disabled in the hardened server."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("cancel_reservation", {"reservation_id": "4WQ150"})
            assert "disabled" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_update_reservation_passengers():
    """Direct passenger updates should be disabled in the hardened server."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "update_reservation_passengers",
                {
                    "reservation_id": "4WQ150",
                    "passengers": [{"first_name": "Passenger0", "last_name": "Test0", "dob": "1990-01-01"}],
                }
            )
            assert "disabled" in result.content[0].text.lower()
