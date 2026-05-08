"""Tool registrations for the airline MCP server.

The goal of this module is to stay approachable for anyone extending the
codebase. The `register_tools` function is the single place where every tool is
declared. Each tool maps closely to an operation on the
``AirlineDatabase``—think of it as the contract between the MCP surface area and
your underlying data access layer.

When you add new behaviour, prefer creating small helper functions (similar to
``_search_direct_flight``) and keep the tool definitions focused on:

* validating parameters
* calling database helpers
* returning serialisable payloads (usually JSON strings)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Annotated, List
from typing import Any

from fastmcp import FastMCP

from .database import AirlineDatabase
from .policy_checks import (
    compensation_quote,
    reservation_allows_cancellation,
    reservation_belongs_to_user,
    reservation_has_flown_segment,
    reservation_is_already_cancelled,
    user_is_compensation_eligible,
)

__all__ = ["register_tools"]


def _search_direct_flight(
    db: AirlineDatabase,
    date: str,
    origin: str | None = None,
    destination: str | None = None,
    leave_after: str | None = None,
) -> List[dict]:
    """Internal helper to search for direct flights."""

    results: List[dict] = []
    db_state = db.get_state()

    for flight in db_state["flights"].values():
        matches_query = (
            (origin is None or flight["origin"] == origin)
            and (destination is None or flight["destination"] == destination)
            and (date in flight["dates"])
            and (flight["dates"][date]["status"] == "available")
            and (
                leave_after is None
                or flight["scheduled_departure_time_est"] >= leave_after
            )
        )

        if not matches_query:
            continue

        flight_date_data = flight["dates"][date]
        results.append(
            {
                "flight_number": flight["flight_number"],
                "origin": flight["origin"],
                "destination": flight["destination"],
                "status": "available",
                "scheduled_departure_time_est": flight["scheduled_departure_time_est"],
                "scheduled_arrival_time_est": flight["scheduled_arrival_time_est"],
                "available_seats": flight_date_data["available_seats"],
                "prices": flight_date_data["prices"],
            }
        )

    return results


def _payment_for_update(
    user: dict,
    payment_id: str,
    total_price: float,
) -> dict | None:
    """Process payment for a reservation update."""

    if payment_id not in user["payment_methods"]:
        raise ValueError("Payment method not found")

    payment_method = user["payment_methods"][payment_id]

    if payment_method["source"] == "certificate":
        raise ValueError("Certificate cannot be used to update reservation")

    if (
        payment_method["source"] == "gift_card"
        and payment_method["amount"] < total_price
    ):
        raise ValueError("Gift card balance is not enough")

    if payment_method["source"] == "gift_card":
        payment_method["amount"] -= total_price

    if total_price != 0:
        return {
            "payment_id": payment_id,
            "amount": total_price,
        }

    return None


def _parse_json_argument(raw_value: str, argument_name: str) -> Any:
    """Parse a JSON string and raise a friendly ``ValueError`` on failure."""

    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{argument_name} must be valid JSON") from exc


def _canonical_json(data: dict) -> str:
    """Return a canonical JSON string for exact confirmation matching."""

    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _require_confirmation(
    db: AirlineDatabase,
    *,
    tool_name: str,
    confirmation_id: str,
    args_without_confirmation: dict,
) -> dict:
    """Consume and validate a pending confirmation for a mutating action."""

    if not confirmation_id:
        raise ValueError(
            f"{tool_name} requires explicit confirmation via a valid confirmation_id"
        )

    confirmation = db.consume_pending_confirmation(confirmation_id)
    if confirmation["tool_name"] != tool_name:
        raise ValueError(
            f"Confirmation {confirmation_id} is for {confirmation['tool_name']}, not {tool_name}"
        )

    if _canonical_json(confirmation["args"]) != _canonical_json(args_without_confirmation):
        raise ValueError(
            "Confirmed action does not exactly match the action being executed"
        )

    return confirmation


def _build_mutation_response(result: dict, receipt: dict) -> str:
    """Return a stable response envelope for mutating tools."""

    return json.dumps({"result": result, "receipt": receipt}, indent=2)


def register_tools(mcp: FastMCP, db: AirlineDatabase) -> None:
    """Register all airline tools with the MCP server."""

    # ------------------------------------------------------------------
    # Reservation lifecycle tools
    # ------------------------------------------------------------------
    @mcp.tool()
    def book_reservation(
        user_id: Annotated[
            str,
            "The ID of the user to book the reservation such as 'sara_doe_496'",
        ],
        origin: Annotated[
            str,
            "The IATA code for the origin city such as 'SFO'",
        ],
        destination: Annotated[
            str,
            "The IATA code for the destination city such as 'JFK'",
        ],
        flight_type: Annotated[
            str,
            "The type of flight such as 'one_way' or 'round_trip'",
        ],
        cabin: Annotated[
            str,
            "The cabin class such as 'basic_economy', 'economy', or 'business'",
        ],
        flights: Annotated[
            str,
            "JSON array of objects containing flight_number and date for each flight segment",
        ],
        passengers: Annotated[
            str,
            "JSON array of objects containing first_name, last_name, and dob for each passenger",
        ],
        payment_methods: Annotated[
            str,
            "JSON array of objects containing payment_id and amount for each payment",
        ],
        total_baggages: Annotated[
            int,
            "The total number of baggage items to book",
        ],
        nonfree_baggages: Annotated[
            int,
            "The number of non-free baggage items to book",
        ],
        insurance: Annotated[str, "Whether the reservation has insurance: 'yes' or 'no'"],
        confirmation_id: Annotated[
            str,
            "Confirmation ID proving the user explicitly approved this exact booking",
        ],
    ) -> str:
        """Create a brand-new reservation and record the full payment detail."""

        action_args = {
            "user_id": user_id,
            "origin": origin,
            "destination": destination,
            "flight_type": flight_type,
            "cabin": cabin,
            "flights": flights,
            "passengers": passengers,
            "payment_methods": payment_methods,
            "total_baggages": total_baggages,
            "nonfree_baggages": nonfree_baggages,
            "insurance": insurance,
        }
        _require_confirmation(
            db,
            tool_name="book_reservation",
            confirmation_id=confirmation_id,
            args_without_confirmation=action_args,
        )

        flights_list = _parse_json_argument(flights, "flights")
        if not isinstance(flights_list, list):
            raise ValueError("flights must be a JSON array")

        passengers_list = _parse_json_argument(passengers, "passengers")
        if not isinstance(passengers_list, list):
            raise ValueError("passengers must be a JSON array")

        payment_methods_list = _parse_json_argument(
            payment_methods,
            "payment_methods",
        )
        if not isinstance(payment_methods_list, list):
            raise ValueError("payment_methods must be a JSON array")

        user = db.get_user(user_id)
        reservation_id = db.get_new_reservation_id()
        db_state = db.get_state()

        reservation = {
            "reservation_id": reservation_id,
            "user_id": user_id,
            "origin": origin,
            "destination": destination,
            "flight_type": flight_type,
            "cabin": cabin,
            "flights": [],
            "passengers": json.loads(json.dumps(passengers_list)),
            "payment_history": json.loads(json.dumps(payment_methods_list)),
            "created_at": db.get_date_time(),
            "total_baggages": total_baggages,
            "nonfree_baggages": nonfree_baggages,
            "insurance": insurance,
        }

        total_price = 0.0
        all_flights_date_data = []

        for flight_info in flights_list:
            flight_number = flight_info["flight_number"]
            flight = db.get_flight(flight_number)
            flight_date_data = db.get_flight_instance(
                flight_number, flight_info["date"]
            )

            if flight_date_data["status"] != "available":
                raise ValueError(
                    f"Flight {flight_number} not available on date {flight_info['date']}"
                )

            if flight_date_data["available_seats"][cabin] < len(passengers_list):
                raise ValueError(f"Not enough seats on flight {flight_number}")

            price = flight_date_data["prices"][cabin]

            reservation["flights"].append(
                {
                    "origin": flight["origin"],
                    "destination": flight["destination"],
                    "flight_number": flight_number,
                    "date": flight_info["date"],
                    "price": price,
                }
            )

            all_flights_date_data.append(flight_date_data)
            total_price += price * len(passengers_list)

        if insurance == "yes":
            total_price += 30 * len(passengers_list)

        total_price += 50 * nonfree_baggages

        for payment_method in payment_methods_list:
            payment_id = payment_method["payment_id"]
            amount = payment_method["amount"]

            if payment_id not in user["payment_methods"]:
                raise ValueError(f"Payment method {payment_id} not found")

            user_payment_method = user["payment_methods"][payment_id]
            if user_payment_method["source"] in ["gift_card", "certificate"] and user_payment_method["amount"] < amount:
                raise ValueError(
                    f"Not enough balance in payment method {payment_id}"
                )

        total_payment = sum(p["amount"] for p in payment_methods_list)
        if total_payment != total_price:
            raise ValueError(
                "Payment amount does not add up, total price is"
                f" {total_price}, but paid {total_payment}"
            )

        for payment_method in payment_methods_list:
            payment_id = payment_method["payment_id"]
            amount = payment_method["amount"]
            user_payment_method = user["payment_methods"][payment_id]

            if user_payment_method["source"] == "gift_card":
                user_payment_method["amount"] -= amount
            elif user_payment_method["source"] == "certificate":
                del user["payment_methods"][payment_id]

        for flight_date_data in all_flights_date_data:
            flight_date_data["available_seats"][cabin] -= len(passengers_list)

        db_state["reservations"][reservation_id] = reservation
        user["reservations"].append(reservation_id)

        receipt = db.add_action_receipt(
            action_type="book_reservation",
            status="completed",
            user_id=user_id,
            reservation_id=reservation_id,
            confirmation_id=confirmation_id,
            details={
                "origin": origin,
                "destination": destination,
                "flight_type": flight_type,
                "cabin": cabin,
                "total_price": total_price,
            },
        )
        return _build_mutation_response(reservation, receipt)

    @mcp.tool()
    def cancel_reservation(
        user_id: Annotated[str, "The user ID that owns the reservation"],
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        reason_category: Annotated[
            str,
            "Cancellation reason category: change_of_plan, airline_cancelled, health, weather, or other",
        ],
        confirmation_id: Annotated[
            str,
            "Confirmation ID proving the user explicitly approved this exact cancellation",
        ],
    ) -> str:
        """Cancel an existing reservation and write refund records."""

        # Hard pre-checks run BEFORE consuming the confirmation token so that
        # invalid attempts do not silently exhaust the user's one-time confirmation.
        reservation = db.get_reservation(reservation_id)
        if not reservation_belongs_to_user(reservation, user_id):
            raise ValueError("Reservation does not belong to the supplied user")
        # Hard guard: a second cancellation must never append additional refund entries.
        if reservation_is_already_cancelled(reservation):
            raise ValueError("Reservation is already cancelled.")

        allowed, explanation = reservation_allows_cancellation(
            db,
            reservation,
            reason_category,
        )
        if not allowed:
            raise ValueError(explanation)

        # Consume the confirmation only after all policy checks pass.
        action_args = {
            "user_id": user_id,
            "reservation_id": reservation_id,
            "reason_category": reason_category,
        }
        _require_confirmation(
            db,
            tool_name="cancel_reservation",
            confirmation_id=confirmation_id,
            args_without_confirmation=action_args,
        )

        refunds = [
            {
                "payment_id": payment["payment_id"],
                "amount": -payment["amount"],
            }
            for payment in reservation["payment_history"]
        ]

        reservation["payment_history"].extend(refunds)
        reservation["status"] = "cancelled"

        print("⚠️  Seats release not implemented for cancellation", flush=True)

        receipt = db.add_action_receipt(
            action_type="cancel_reservation",
            status="completed",
            user_id=user_id,
            reservation_id=reservation_id,
            confirmation_id=confirmation_id,
            details={"reason_category": reason_category, "justification": explanation},
        )
        return _build_mutation_response(reservation, receipt)

    @mcp.tool()
    def get_reservation_details(
        reservation_id: Annotated[str, "The reservation ID, such as '8JX2WO'"],
    ) -> str:
        """Return the reservation payload so MCP clients can render it."""

        reservation = db.get_reservation(reservation_id)
        return json.dumps(reservation, indent=2)

    @mcp.tool()
    def update_reservation_baggages(
        user_id: Annotated[str, "The user ID that owns the reservation"],
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        total_baggages: Annotated[int, "The updated total number of baggage items"],
        nonfree_baggages: Annotated[
            int, "The updated number of non-free baggage items"
        ],
        payment_id: Annotated[
            str,
            "The payment id stored in user profile, such as 'credit_card_7815826'",
        ],
        confirmation_id: Annotated[
            str,
            "Confirmation ID proving the user explicitly approved this exact baggage change",
        ],
    ) -> str:
        """Adjust baggage counts while collecting any additional payment."""

        action_args = {
            "user_id": user_id,
            "reservation_id": reservation_id,
            "total_baggages": total_baggages,
            "nonfree_baggages": nonfree_baggages,
            "payment_id": payment_id,
        }
        _require_confirmation(
            db,
            tool_name="update_reservation_baggages",
            confirmation_id=confirmation_id,
            args_without_confirmation=action_args,
        )

        reservation = db.get_reservation(reservation_id)
        if not reservation_belongs_to_user(reservation, user_id):
            raise ValueError("Reservation does not belong to the supplied user")
        user = db.get_user(reservation["user_id"])

        total_price = 50 * max(0, nonfree_baggages - reservation["nonfree_baggages"])

        payment = _payment_for_update(user, payment_id, total_price)
        if payment is not None:
            reservation["payment_history"].append(payment)

        reservation["total_baggages"] = total_baggages
        reservation["nonfree_baggages"] = nonfree_baggages

        receipt = db.add_action_receipt(
            action_type="update_reservation_baggages",
            status="completed",
            user_id=user_id,
            reservation_id=reservation_id,
            confirmation_id=confirmation_id,
            details={
                "total_baggages": total_baggages,
                "nonfree_baggages": nonfree_baggages,
                "payment_id": payment_id,
                "price_delta": total_price,
            },
        )
        return _build_mutation_response(reservation, receipt)

    @mcp.tool()
    def update_reservation_flights(
        user_id: Annotated[str, "The user ID that owns the reservation"],
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        cabin: Annotated[
            str,
            "The cabin class: 'basic_economy', 'economy', or 'business'",
        ],
        flights: Annotated[
            str,
            "JSON array of flight info objects with flight_number and date for ALL flights in reservation",
        ],
        payment_id: Annotated[
            str,
            "The payment id stored in user profile, such as 'credit_card_7815826'",
        ],
        confirmation_id: Annotated[
            str,
            "Confirmation ID proving the user explicitly approved this exact flight change",
        ],
    ) -> str:
        """Swap flights in a reservation, charging the fare difference."""

        action_args = {
            "user_id": user_id,
            "reservation_id": reservation_id,
            "cabin": cabin,
            "flights": flights,
            "payment_id": payment_id,
        }
        _require_confirmation(
            db,
            tool_name="update_reservation_flights",
            confirmation_id=confirmation_id,
            args_without_confirmation=action_args,
        )

        flights_list = _parse_json_argument(flights, "flights")
        if not isinstance(flights_list, list):
            raise ValueError("flights must be a JSON array")

        reservation = db.get_reservation(reservation_id)
        if not reservation_belongs_to_user(reservation, user_id):
            raise ValueError("Reservation does not belong to the supplied user")
        if reservation["cabin"] == "basic_economy":
            raise ValueError("Basic economy reservations cannot be modified")
        if reservation_has_flown_segment(db, reservation):
            raise ValueError("Flights cannot be changed after any segment has been flown")
        user = db.get_user(reservation["user_id"])

        total_price = 0.0
        reservation_flights = []

        for flight_info in flights_list:
            matching_flight = next(
                (
                    rf
                    for rf in reservation["flights"]
                    if rf["flight_number"] == flight_info["flight_number"]
                    and rf["date"] == flight_info["date"]
                    and cabin == reservation["cabin"]
                ),
                None,
            )

            if matching_flight:
                total_price += matching_flight["price"] * len(
                    reservation["passengers"]
                )
                reservation_flights.append(matching_flight)
                continue

            flight = db.get_flight(flight_info["flight_number"])
            flight_date_data = db.get_flight_instance(
                flight_info["flight_number"], flight_info["date"]
            )

            if flight_date_data["status"] != "available":
                raise ValueError(
                    f"Flight {flight_info['flight_number']} not available on date {flight_info['date']}"
                )

            if flight_date_data["available_seats"][cabin] < len(reservation["passengers"]):
                raise ValueError(
                    f"Not enough seats on flight {flight_info['flight_number']}"
                )

            reservation_flight = {
                "flight_number": flight_info["flight_number"],
                "date": flight_info["date"],
                "price": flight_date_data["prices"][cabin],
                "origin": flight["origin"],
                "destination": flight["destination"],
            }
            total_price += reservation_flight["price"] * len(
                reservation["passengers"]
            )
            reservation_flights.append(reservation_flight)

        original_price = (
            sum(f["price"] for f in reservation["flights"])
            * len(reservation["passengers"])
        )
        total_price -= original_price

        payment = _payment_for_update(user, payment_id, total_price)
        if payment is not None:
            reservation["payment_history"].append(payment)

        reservation["flights"] = reservation_flights
        reservation["cabin"] = cabin

        receipt = db.add_action_receipt(
            action_type="update_reservation_flights",
            status="completed",
            user_id=user_id,
            reservation_id=reservation_id,
            confirmation_id=confirmation_id,
            details={
                "cabin": cabin,
                "payment_id": payment_id,
                "price_delta": total_price,
            },
        )
        return _build_mutation_response(reservation, receipt)

    @mcp.tool()
    def update_reservation_passengers(
        user_id: Annotated[str, "The user ID that owns the reservation"],
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        passengers: Annotated[
            list[dict],
            "Array of passenger objects with first_name, last_name, and dob",
        ],
        confirmation_id: Annotated[
            str,
            "Confirmation ID proving the user explicitly approved this exact passenger update",
        ],
    ) -> str:
        """Update passenger information while preserving passenger count."""

        action_args = {
            "user_id": user_id,
            "reservation_id": reservation_id,
            "passengers": passengers,
        }
        _require_confirmation(
            db,
            tool_name="update_reservation_passengers",
            confirmation_id=confirmation_id,
            args_without_confirmation=action_args,
        )

        if not isinstance(passengers, list):
            raise ValueError("passengers must be an array")
        reservation = db.get_reservation(reservation_id)
        if not reservation_belongs_to_user(reservation, user_id):
            raise ValueError("Reservation does not belong to the supplied user")

        if len(passengers) != len(reservation["passengers"]):
            raise ValueError("Number of passengers does not match")

        reservation["passengers"] = json.loads(json.dumps(passengers))

        receipt = db.add_action_receipt(
            action_type="update_reservation_passengers",
            status="completed",
            user_id=user_id,
            reservation_id=reservation_id,
            confirmation_id=confirmation_id,
            details={"passenger_count": len(passengers)},
        )
        return _build_mutation_response(reservation, receipt)

    # ------------------------------------------------------------------
    # Flight search and status tools
    # ------------------------------------------------------------------
    @mcp.tool()
    def search_direct_flight(
        origin: Annotated[
            str, "The origin city airport in three letters, such as 'JFK'"
        ],
        destination: Annotated[
            str, "The destination city airport in three letters, such as 'LAX'"
        ],
        date: Annotated[
            str,
            "The date of the flight in the format 'YYYY-MM-DD', such as '2024-01-01'",
        ],
    ) -> str:
        """Search same-day direct flights that have available seats."""

        results = _search_direct_flight(db, date, origin, destination)
        return json.dumps(results, indent=2)

    @mcp.tool()
    def search_onestop_flight(
        origin: Annotated[
            str, "The origin city airport in three letters, such as 'JFK'"
        ],
        destination: Annotated[
            str, "The destination city airport in three letters, such as 'LAX'"
        ],
        date: Annotated[
            str,
            "The date of the flight in the format 'YYYY-MM-DD', such as '2024-05-01'",
        ],
    ) -> str:
        """Find itineraries with a single connection, including next-day legs."""

        results = []

        for first_leg in _search_direct_flight(db, date, origin, None):
            first_leg["date"] = date

            has_next_day = "+1" in first_leg["scheduled_arrival_time_est"]

            date_obj = datetime.strptime(date, "%Y-%m-%d")
            if has_next_day:
                date_obj += timedelta(days=1)
            date2 = date_obj.strftime("%Y-%m-%d")

            for second_leg in _search_direct_flight(
                db,
                date2,
                first_leg["destination"],
                destination,
                first_leg["scheduled_arrival_time_est"],
            ):
                second_leg["date"] = date2
                results.append([first_leg, second_leg])

        return json.dumps(results, indent=2)

    @mcp.tool()
    def get_flight_status(
        flight_number: Annotated[str, "The flight number"],
        date: Annotated[str, "The date of the flight"],
    ) -> str:
        """Return the operational status string for a specific flight instance."""

        flight_instance = db.get_flight_instance(flight_number, date)
        return flight_instance["status"]

    # ------------------------------------------------------------------
    # User profile and utility helpers
    # ------------------------------------------------------------------
    @mcp.tool()
    def create_confirmation(
        tool_name: Annotated[str, "The mutating tool that requires confirmation"],
        summary: Annotated[str, "User-facing summary of the pending action"],
        args_json: Annotated[str, "Canonical JSON object for the exact tool arguments"],
        user_id: Annotated[str | None, "User ID tied to the pending action"] = None,
        reservation_id: Annotated[
            str | None, "Reservation ID tied to the pending action"
        ] = None,
        price_delta: Annotated[
            float | None, "Expected payment impact for the action"
        ] = None,
    ) -> str:
        """Create a server-side pending confirmation for a mutating action."""

        args = _parse_json_argument(args_json, "args_json")
        if not isinstance(args, dict):
            raise ValueError("args_json must encode a JSON object")

        confirmation = db.create_pending_confirmation(
            tool_name=tool_name,
            summary=summary,
            args=args,
            user_id=user_id,
            reservation_id=reservation_id,
            price_delta=price_delta,
        )
        return json.dumps(confirmation, indent=2)

    @mcp.tool()
    def get_user_details(
        user_id: Annotated[str, "The user ID, such as 'sara_doe_496'"],
    ) -> str:
        """Fetch user contact info, payment methods, and reservation IDs."""

        user = db.get_user(user_id)
        return json.dumps(user, indent=2)

    @mcp.tool()
    def send_certificate(
        user_id: Annotated[str, "The ID of the user, such as 'sara_doe_496'"],
        reservation_id: Annotated[str, "The reservation tied to the compensation event"],
        event_type: Annotated[
            str,
            "Compensation event type: cancelled or delayed",
        ],
        confirmation_id: Annotated[
            str,
            "Confirmation ID proving the user explicitly approved this compensation",
        ],
    ) -> str:
        """Issue policy-approved compensation exactly once for a qualifying reservation."""

        action_args = {
            "user_id": user_id,
            "reservation_id": reservation_id,
            "event_type": event_type,
        }
        _require_confirmation(
            db,
            tool_name="send_certificate",
            confirmation_id=confirmation_id,
            args_without_confirmation=action_args,
        )

        user = db.get_user(user_id)
        reservation = db.get_reservation(reservation_id)
        if not reservation_belongs_to_user(reservation, user_id):
            raise ValueError("Reservation does not belong to the supplied user")
        if not user_is_compensation_eligible(user, reservation):
            raise ValueError("User is not eligible for compensation under the policy")
        if db.compensation_already_issued(reservation_id, event_type):
            raise ValueError("Compensation for this reservation and event was already issued")

        amount, reason = compensation_quote(db, user, reservation, event_type)
        payment_ids = db.get_new_payment_ids()

        for payment_id_num in payment_ids:
            payment_id = f"certificate_{payment_id_num}"

            if payment_id not in user["payment_methods"]:
                new_payment = {
                    "id": payment_id,
                    "amount": amount,
                    "source": "certificate",
                }
                user["payment_methods"][payment_id] = new_payment
                db.record_compensation_issue(reservation_id, event_type)
                receipt = db.add_action_receipt(
                    action_type="issue_compensation",
                    status="completed",
                    user_id=user_id,
                    reservation_id=reservation_id,
                    details={
                        "event_type": event_type,
                        "amount": amount,
                        "payment_id": payment_id,
                        "reason": reason,
                    },
                )
                return _build_mutation_response(
                    {
                        "payment_id": payment_id,
                        "amount": amount,
                        "source": "certificate",
                    },
                    receipt,
                )

        raise ValueError("Too many certificates")

    @mcp.tool()
    def get_action_history(
        user_id: Annotated[str, "The user ID whose action history should be returned"],
    ) -> str:
        """Return server-verified action receipts for the supplied user."""

        db.get_user(user_id)
        return json.dumps(db.get_action_receipts(user_id), indent=2)

    @mcp.tool()
    def list_all_airports() -> str:
        """Return a curated list of airports useful for demo prompts."""

        airports = [
            {"iata": "SFO", "city": "San Francisco"},
            {"iata": "JFK", "city": "New York"},
            {"iata": "LAX", "city": "Los Angeles"},
            {"iata": "ORD", "city": "Chicago"},
            {"iata": "DFW", "city": "Dallas"},
            {"iata": "DEN", "city": "Denver"},
            {"iata": "PIT", "city": "Pittsburgh"},
            {"iata": "ATL", "city": "Atlanta"},
            {"iata": "MIA", "city": "Miami"},
            {"iata": "BOS", "city": "Boston"},
            {"iata": "PHX", "city": "Phoenix"},
            {"iata": "IAH", "city": "Houston"},
            {"iata": "LAS", "city": "Las Vegas"},
            {"iata": "MCO", "city": "Orlando"},
            {"iata": "EWR", "city": "Newark"},
            {"iata": "CLT", "city": "Charlotte"},
            {"iata": "MSP", "city": "Minneapolis"},
            {"iata": "DTW", "city": "Detroit"},
            {"iata": "PHL", "city": "Philadelphia"},
            {"iata": "LGA", "city": "LaGuardia"},
        ]
        return json.dumps(airports, indent=2)

    @mcp.tool()
    def calculate(
        expression: Annotated[
            str,
            "Mathematical expression like '2 + 2' with numbers and operators (+, -, *, /)",
        ],
    ) -> str:
        """Evaluate simple arithmetic—handy for lightweight agent tasks."""

        try:
            allowed_names = {"__builtins__": {}}
            result = eval(expression, allowed_names)
            return str(round(result, 2))
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Invalid expression") from exc

    @mcp.tool()
    def transfer_to_human_agents(
        summary: Annotated[str, "A summary of the user's issue"],
    ) -> str:
        """Placeholder utility so agents can gracefully escalate."""

        return "Transfer successful"
