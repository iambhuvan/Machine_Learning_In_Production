"""Test MCP server tools via MCP client connection over HTTP."""

import asyncio
import json
import pytest
import pytest_asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# Default server URL - can be overridden with environment variable
SERVER_URL = "http://localhost:3000/mcp"


async def create_confirmation(session, tool_name: str, args: dict) -> str:
    """Create a pending confirmation for a mutating action."""

    result = await session.call_tool(
        "create_confirmation",
        {
            "tool_name": tool_name,
            "summary": f"Test confirmation for {tool_name}",
            "args_json": json.dumps(args, sort_keys=True),
        },
    )
    payload = json.loads(result.content[0].text)
    return payload["confirmation_id"]


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
            import json

            # Get initial reservation state
            result = await session.call_tool("get_reservation_details", {"reservation_id": "4WQ150"})
            original_reservation = json.loads(result.content[0].text)
            assert "status" not in original_reservation or original_reservation.get("status") != "cancelled"

            # Cancel the reservation
            confirmation_id = await create_confirmation(
                session,
                "cancel_reservation",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                },
            )
            await session.call_tool(
                "cancel_reservation",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                    "confirmation_id": confirmation_id,
                },
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
            import json
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
            import json

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
            import json

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
            import json

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
async def test_send_certificate():
    """Test sending a certificate to a user — requires a prior confirmation."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            import json

            # Use a reservation with a cancelled flight and an eligible user.
            user_id = "isabella_anderson_9682"
            reservation_id = "QDGWHB"

            user_before = await session.call_tool("get_user_details", {"user_id": user_id})
            user_data_before = json.loads(user_before.content[0].text)
            cert_count_before = sum(1 for pm in user_data_before["payment_methods"].values()
                                   if pm.get("source") == "certificate")

            confirmation_id = await create_confirmation(
                session,
                "send_certificate",
                {"user_id": user_id, "reservation_id": reservation_id, "event_type": "cancelled"},
            )
            result = await session.call_tool(
                "send_certificate",
                {
                    "user_id": user_id,
                    "reservation_id": reservation_id,
                    "event_type": "cancelled",
                    "confirmation_id": confirmation_id,
                },
            )

            assert len(result.content) > 0
            assert result.content[0].type == "text"
            payload = json.loads(result.content[0].text)
            assert payload["result"]["source"] == "certificate"
            assert payload["receipt"]["action_type"] == "issue_compensation"

            # Verify the certificate was added
            user_after = await session.call_tool("get_user_details", {"user_id": user_id})
            user_data_after = json.loads(user_after.content[0].text)
            cert_count_after = sum(1 for pm in user_data_after["payment_methods"].values()
                                  if pm.get("source") == "certificate")
            assert cert_count_after == cert_count_before + 1


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
    """Test canceling a reservation."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            import json

            # First get the reservation details
            result = await session.call_tool("get_reservation_details", {"reservation_id": "4WQ150"})
            original = json.loads(result.content[0].text)

            confirmation_id = await create_confirmation(
                session,
                "cancel_reservation",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                },
            )
            result = await session.call_tool(
                "cancel_reservation",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                    "confirmation_id": confirmation_id,
                },
            )

            assert len(result.content) > 0
            assert result.content[0].type == "text"

            payload = json.loads(result.content[0].text)
            reservation = payload["result"]
            assert reservation["reservation_id"] == "4WQ150"
            assert reservation["status"] == "cancelled"
            # Should have refund entries
            assert len(reservation["payment_history"]) > len(original["payment_history"])
            assert payload["receipt"]["action_type"] == "cancel_reservation"


@pytest.mark.asyncio
async def test_update_reservation_passengers():
    """Test updating reservation passengers."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            import json

            # First get the reservation to see how many passengers it has
            res_result = await session.call_tool("get_reservation_details", {"reservation_id": "4WQ150"})
            res_data = json.loads(res_result.content[0].text)
            num_passengers = len(res_data["passengers"])

            # Update passengers for the reservation (must match original passenger count)
            passengers_list = [
                {"first_name": f"Passenger{i}", "last_name": f"Test{i}", "dob": "1990-01-01"}
                for i in range(num_passengers)
            ]

            # Python server expects JSON string, TypeScript expects array
            # Send as array directly (TypeScript format)
            confirmation_id = await create_confirmation(
                session,
                "update_reservation_passengers",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "passengers": passengers_list,
                },
            )
            result = await session.call_tool(
                "update_reservation_passengers",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "passengers": passengers_list,
                    "confirmation_id": confirmation_id,
                }
            )

            assert len(result.content) > 0
            assert result.content[0].type == "text"

            payload = json.loads(result.content[0].text)
            reservation = payload["result"]
            assert len(reservation["passengers"]) == num_passengers
            assert reservation["passengers"][0]["first_name"] == "Passenger0"


@pytest.mark.asyncio
async def test_cancel_reservation_rejects_wrong_user():
    """Cancellation must be rejected if the reservation does not belong to the user."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            confirmation_id = await create_confirmation(
                session,
                "cancel_reservation",
                {
                    "user_id": "mia_li_3668",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                },
            )
            result = await session.call_tool(
                "cancel_reservation",
                {
                    "user_id": "mia_li_3668",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                    "confirmation_id": confirmation_id,
                },
            )

            assert "does not belong" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_compensation_is_one_time_per_event():
    """Compensation must only be issuable once per reservation/event."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            cert_args = {
                "user_id": "isabella_anderson_9682",
                "reservation_id": "QDGWHB",
                "event_type": "cancelled",
            }
            first_confirmation_id = await create_confirmation(session, "send_certificate", cert_args)
            first = await session.call_tool(
                "send_certificate", {**cert_args, "confirmation_id": first_confirmation_id}
            )
            assert "issue_compensation" in first.content[0].text

            # Second attempt — server must reject the duplicate regardless of confirmation.
            second_confirmation_id = await create_confirmation(session, "send_certificate", cert_args)
            second = await session.call_tool(
                "send_certificate", {**cert_args, "confirmation_id": second_confirmation_id}
            )
            assert "already issued" in second.content[0].text.lower()


@pytest.mark.asyncio
async def test_delayed_compensation_requires_change_or_cancellation():
    """Delayed-flight compensation must only be issuable after a change or cancellation."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            user_id = "liam_ito_4473"
            reservation_id = "LWTEDF"
            delayed_args = {"user_id": user_id, "reservation_id": reservation_id, "event_type": "delayed"}

            # Attempt compensation before any change/cancellation — must be rejected.
            first_confirmation_id = await create_confirmation(session, "send_certificate", delayed_args)
            first_attempt = await session.call_tool(
                "send_certificate", {**delayed_args, "confirmation_id": first_confirmation_id}
            )
            assert "only allowed after the reservation was changed or cancelled" in first_attempt.content[0].text.lower()

            # Cancel the reservation (policy allows due to weather + insurance).
            cancel_args = {
                "user_id": user_id,
                "reservation_id": reservation_id,
                "reason_category": "weather",
            }
            cancel_confirmation_id = await create_confirmation(session, "cancel_reservation", cancel_args)
            cancelled = await session.call_tool(
                "cancel_reservation",
                {**cancel_args, "confirmation_id": cancel_confirmation_id},
            )
            assert "cancel_reservation" in cancelled.content[0].text

            # Now compensation must succeed.
            second_confirmation_id = await create_confirmation(session, "send_certificate", delayed_args)
            second_attempt = await session.call_tool(
                "send_certificate", {**delayed_args, "confirmation_id": second_confirmation_id}
            )
            assert "issue_compensation" in second_attempt.content[0].text


@pytest.mark.asyncio
async def test_cancel_reservation_rejects_already_cancelled_reservation():
    """Cancellation must be idempotent and reject a second cancellation attempt."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            args = {
                "user_id": "chen_jackson_3290",
                "reservation_id": "4WQ150",
                "reason_category": "change_of_plan",
            }
            confirmation_id = await create_confirmation(session, "cancel_reservation", args)
            first = await session.call_tool(
                "cancel_reservation",
                {
                    **args,
                    "confirmation_id": confirmation_id,
                },
            )
            assert "cancel_reservation" in first.content[0].text

            second_confirmation_id = await create_confirmation(session, "cancel_reservation", args)
            second = await session.call_tool(
                "cancel_reservation",
                {
                    **args,
                    "confirmation_id": second_confirmation_id,
                },
            )
            assert "already cancelled" in second.content[0].text.lower()


@pytest.mark.asyncio
async def test_baggage_update_requires_exact_confirmation():
    """Payment-affecting baggage changes must match the confirmed payload exactly."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            confirmation_id = await create_confirmation(
                session,
                "update_reservation_baggages",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "total_baggages": 2,
                    "nonfree_baggages": 1,
                    "payment_id": "credit_card_7815826",
                },
            )

            mismatch = await session.call_tool(
                "update_reservation_baggages",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "total_baggages": 3,
                    "nonfree_baggages": 2,
                    "payment_id": "credit_card_7815826",
                    "confirmation_id": confirmation_id,
                },
            )
            assert "does not exactly match" in mismatch.content[0].text.lower()


@pytest.mark.asyncio
async def test_action_history_contains_receipts():
    """Mutating actions must be visible through the action-history tool."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            confirmation_id = await create_confirmation(
                session,
                "cancel_reservation",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                },
            )
            await session.call_tool(
                "cancel_reservation",
                {
                    "user_id": "chen_jackson_3290",
                    "reservation_id": "4WQ150",
                    "reason_category": "change_of_plan",
                    "confirmation_id": confirmation_id,
                },
            )

            history = await session.call_tool(
                "get_action_history",
                {"user_id": "chen_jackson_3290"},
            )
            receipts = json.loads(history.content[0].text)
            assert any(receipt["action_type"] == "cancel_reservation" for receipt in receipts)


@pytest.mark.asyncio
async def test_compensation_rejected_for_ineligible_user():
    """Compensation must be rejected for a regular-member economy-class user with no insurance."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # lucas_hernandez_8985 holds reservation OP3VYE which is economy class
            # with no insurance. Verify membership is regular so the test exercises
            # the ineligibility path, not any other guard.
            user_result = await session.call_tool("get_user_details", {"user_id": "lucas_hernandez_8985"})
            user_data = json.loads(user_result.content[0].text)
            assert user_data.get("membership") == "regular"

            res_result = await session.call_tool("get_reservation_details", {"reservation_id": "OP3VYE"})
            res_data = json.loads(res_result.content[0].text)
            assert res_data.get("cabin") != "business"
            assert res_data.get("insurance") != "yes"

            cert_args = {
                "user_id": "lucas_hernandez_8985",
                "reservation_id": "OP3VYE",
                "event_type": "cancelled",
            }
            confirmation_id = await create_confirmation(session, "send_certificate", cert_args)
            result = await session.call_tool(
                "send_certificate", {**cert_args, "confirmation_id": confirmation_id}
            )
            assert "not eligible" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_compensation_rejected_for_unknown_event_type():
    """Compensation must be rejected for any event type not defined in the policy."""
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            cert_args = {
                "user_id": "isabella_anderson_9682",
                "reservation_id": "QDGWHB",
                "event_type": "turbulence",
            }
            confirmation_id = await create_confirmation(session, "send_certificate", cert_args)
            result = await session.call_tool(
                "send_certificate", {**cert_args, "confirmation_id": confirmation_id}
            )
            assert "cancelled" in result.content[0].text.lower() or "delayed" in result.content[0].text.lower()
