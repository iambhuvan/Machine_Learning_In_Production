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


def _serialize(data: Any) -> str:
    """Return stable pretty JSON for tool responses."""

    return json.dumps(data, indent=2)


def _security_state(db: AirlineDatabase) -> dict:
    """Return trusted runtime state for pending actions and receipts."""

    return db.get_security_state()


def _current_time(db: AirlineDatabase) -> datetime:
    """Return the fixed simulation time used across the dataset."""

    return datetime.fromisoformat(db.get_date_time())


def _reservation_statuses(db: AirlineDatabase, reservation: dict) -> list[str]:
    """Return live operational statuses for every flight in a reservation."""

    return [
        db.get_flight_instance(flight["flight_number"], flight["date"])["status"]
        for flight in reservation["flights"]
    ]


def _require_user_owns_reservation(
    db: AirlineDatabase,
    user_id: str,
    reservation_id: str,
) -> dict:
    """Load a reservation and enforce ownership by user id."""

    reservation = db.get_reservation(reservation_id)
    if reservation["user_id"] != user_id:
        raise ValueError("Reservation does not belong to the supplied user")
    return reservation


def _refund_entries(reservation: dict) -> list[dict]:
    """Build refund rows for all positive payments on the reservation."""

    return [
        {
            "payment_id": payment["payment_id"],
            "amount": -payment["amount"],
        }
        for payment in reservation["payment_history"]
        if payment["amount"] > 0
    ]


def _insurance_reason_is_covered(reason: str) -> bool:
    """Return whether the user-provided reason is covered by insurance."""

    lowered = reason.lower()
    covered_terms = ("health", "medical", "illness", "sick", "weather", "storm")
    return any(term in lowered for term in covered_terms)


def _validate_payment_for_update(
    user: dict,
    payment_id: str,
    total_price: float,
) -> None:
    """Validate that a payment method can cover a future reservation update."""

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


def _make_pending_action(
    db: AirlineDatabase,
    *,
    action_type: str,
    user_id: str,
    reservation_id: str,
    summary: str,
    details: dict,
) -> str:
    """Store a trusted pending action and return the serialized preview."""

    action_id = f"action_{db.get_new_payment_id()}"
    action = {
        "action_id": action_id,
        "action_type": action_type,
        "user_id": user_id,
        "reservation_id": reservation_id,
        "summary": summary,
        "details": details,
        "created_at": db.get_date_time(),
        "status": "pending",
    }
    _security_state(db)["pending_actions"][action_id] = action

    return _serialize(
        {
            "requires_confirmation": True,
            "action_id": action_id,
            "action_type": action_type,
            "user_id": user_id,
            "reservation_id": reservation_id,
            "summary": summary,
            "details": details,
        }
    )


def _record_receipt(
    db: AirlineDatabase,
    *,
    action_type: str,
    user_id: str,
    reservation_id: str | None,
    summary: str,
    details: dict,
) -> dict:
    """Persist a trusted receipt and return it."""

    receipt_id = f"receipt_{db.get_new_payment_id()}"
    receipt = {
        "verified_action": True,
        "receipt_id": receipt_id,
        "action_type": action_type,
        "user_id": user_id,
        "reservation_id": reservation_id,
        "summary": summary,
        "details": details,
        "recorded_at": db.get_date_time(),
    }
    _security_state(db)["receipts"][receipt_id] = receipt
    return receipt


def _cancellation_basis(db: AirlineDatabase, reservation: dict, reason: str) -> str:
    """Return the policy basis that permits cancellation or raise an error."""

    if reservation.get("status") == "cancelled":
        raise ValueError("Reservation is already cancelled")

    statuses = _reservation_statuses(db, reservation)
    if any(status in {"flying", "landed"} for status in statuses):
        raise ValueError("A flown segment exists; transfer to a human agent is required")

    created_at = datetime.fromisoformat(reservation["created_at"])
    within_24h = (_current_time(db) - created_at) <= timedelta(hours=24)
    if within_24h:
        return "booking made within 24 hours"

    if any(status == "cancelled" for status in statuses):
        return "flight cancelled by airline"

    if reservation["cabin"] == "business":
        return "business reservation"

    if reservation["insurance"] == "yes" and _insurance_reason_is_covered(reason):
        return "insurance-covered reason"

    raise ValueError("Cancellation is not allowed by policy for this reservation")


def _compensation_details(db: AirlineDatabase, user: dict, reservation: dict) -> tuple[str, int]:
    """Return a valid compensation basis and amount or raise an error."""

    reservation_id = reservation["reservation_id"]
    if reservation_id in _security_state(db)["compensated_reservations"]:
        raise ValueError("Compensation was already issued for this reservation")

    eligible = (
        user["membership"] in {"silver", "gold"}
        or reservation["insurance"] == "yes"
        or reservation["cabin"] == "business"
    )
    if not eligible:
        raise ValueError("User is not eligible for compensation under policy")

    statuses = _reservation_statuses(db, reservation)
    passenger_count = len(reservation["passengers"])

    if any(status == "cancelled" for status in statuses):
        return "cancelled flight", 100 * passenger_count

    if any(status == "delayed" for status in statuses) and reservation.get("status") == "cancelled":
        return "delayed flight after cancellation", 50 * passenger_count

    raise ValueError("No compensable event was found for this reservation")


def _execute_baggage_update(db: AirlineDatabase, action: dict) -> dict:
    """Execute a previously previewed baggage update exactly as stored."""

    details = action["details"]
    reservation = db.get_reservation(action["reservation_id"])
    user = db.get_user(action["user_id"])

    payment = _payment_for_update(
        user,
        details["payment_id"],
        details["additional_charge"],
    )
    if payment is not None:
        reservation["payment_history"].append(payment)

    reservation["total_baggages"] = details["total_baggages"]
    reservation["nonfree_baggages"] = details["nonfree_baggages"]

    return _record_receipt(
        db,
        action_type="baggage_update",
        user_id=action["user_id"],
        reservation_id=action["reservation_id"],
        summary=action["summary"],
        details={
            "total_baggages": details["total_baggages"],
            "nonfree_baggages": details["nonfree_baggages"],
            "additional_charge": details["additional_charge"],
            "payment_id": details["payment_id"],
        },
    )


def _execute_cancellation(db: AirlineDatabase, action: dict) -> dict:
    """Execute a previously previewed cancellation exactly as stored."""

    reservation = db.get_reservation(action["reservation_id"])
    refunds = _refund_entries(reservation)
    reservation["payment_history"].extend(refunds)
    reservation["status"] = "cancelled"

    refund_total = round(sum(-refund["amount"] for refund in refunds), 2)
    return _record_receipt(
        db,
        action_type="reservation_cancellation",
        user_id=action["user_id"],
        reservation_id=action["reservation_id"],
        summary=action["summary"],
        details={
            "reason": action["details"]["reason"],
            "policy_basis": action["details"]["policy_basis"],
            "refund_total": refund_total,
            "refunds": refunds,
        },
    )


def _create_booking(
    db: AirlineDatabase,
    *,
    user_id: str,
    origin: str,
    destination: str,
    flight_type: str,
    cabin: str,
    flights_list: list,
    passengers_list: list,
    payment_methods_list: list,
    total_baggages: int,
    nonfree_baggages: int,
    insurance: str,
) -> dict:
    """Create a booking after validation and payment checks."""

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
        flight_date_data = db.get_flight_instance(flight_number, flight_info["date"])

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
        if (
            user_payment_method["source"] in ["gift_card", "certificate"]
            and user_payment_method["amount"] < amount
        ):
            raise ValueError(f"Not enough balance in payment method {payment_id}")

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
    return reservation


def _preview_flight_update(
    db: AirlineDatabase,
    *,
    user_id: str,
    reservation_id: str,
    cabin: str,
    flights_list: list,
    payment_id: str,
) -> tuple[str, dict]:
    """Validate a flight update and return summary plus trusted details."""

    reservation = _require_user_owns_reservation(db, user_id, reservation_id)
    if reservation.get("status") == "cancelled":
        raise ValueError("Cannot update a cancelled reservation")

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
            total_price += matching_flight["price"] * len(reservation["passengers"])
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
            raise ValueError(f"Not enough seats on flight {flight_info['flight_number']}")

        reservation_flight = {
            "flight_number": flight_info["flight_number"],
            "date": flight_info["date"],
            "price": flight_date_data["prices"][cabin],
            "origin": flight["origin"],
            "destination": flight["destination"],
        }
        total_price += reservation_flight["price"] * len(reservation["passengers"])
        reservation_flights.append(reservation_flight)

    original_price = sum(f["price"] for f in reservation["flights"]) * len(
        reservation["passengers"]
    )
    price_delta = round(total_price - original_price, 2)

    user = db.get_user(user_id)
    _validate_payment_for_update(user, payment_id, max(price_delta, 0))

    if price_delta > 0:
        price_text = f"charge {payment_id} ${price_delta:.2f}"
    elif price_delta < 0:
        price_text = f"refund ${abs(price_delta):.2f} to {payment_id}"
    else:
        price_text = "no fare difference"

    summary = (
        f"Update reservation {reservation_id} to cabin {cabin} with the requested flights "
        f"and {price_text}."
    )
    return summary, {
        "cabin": cabin,
        "flights": reservation_flights,
        "payment_id": payment_id,
        "price_delta": price_delta,
    }


def _execute_flight_update(db: AirlineDatabase, action: dict) -> dict:
    """Execute a previously previewed flight update exactly as stored."""

    reservation = db.get_reservation(action["reservation_id"])
    user = db.get_user(action["user_id"])
    details = action["details"]
    payment = _payment_for_update(user, details["payment_id"], details["price_delta"])
    if payment is not None:
        reservation["payment_history"].append(payment)

    reservation["flights"] = json.loads(json.dumps(details["flights"]))
    reservation["cabin"] = details["cabin"]

    return _record_receipt(
        db,
        action_type="flight_update",
        user_id=action["user_id"],
        reservation_id=action["reservation_id"],
        summary=action["summary"],
        details={
            "cabin": details["cabin"],
            "payment_id": details["payment_id"],
            "price_delta": details["price_delta"],
        },
    )


def _execute_booking(db: AirlineDatabase, action: dict) -> dict:
    """Execute a previously previewed booking exactly as stored."""

    details = action["details"]
    reservation = _create_booking(
        db,
        user_id=action["user_id"],
        origin=details["origin"],
        destination=details["destination"],
        flight_type=details["flight_type"],
        cabin=details["cabin"],
        flights_list=details["flights"],
        passengers_list=details["passengers"],
        payment_methods_list=details["payment_methods"],
        total_baggages=details["total_baggages"],
        nonfree_baggages=details["nonfree_baggages"],
        insurance=details["insurance"],
    )
    return _record_receipt(
        db,
        action_type="reservation_booking",
        user_id=action["user_id"],
        reservation_id=reservation["reservation_id"],
        summary=action["summary"],
        details={
            "reservation_id": reservation["reservation_id"],
            "origin": reservation["origin"],
            "destination": reservation["destination"],
            "cabin": reservation["cabin"],
        },
    )


def _preview_booking(
    db: AirlineDatabase,
    *,
    user_id: str,
    origin: str,
    destination: str,
    flight_type: str,
    cabin: str,
    flights_list: list,
    passengers_list: list,
    payment_methods_list: list,
    total_baggages: int,
    nonfree_baggages: int,
    insurance: str,
) -> tuple[str, dict]:
    """Validate a booking request and return a non-mutating summary."""

    user = db.get_user(user_id)
    total_price = 0.0

    for flight_info in flights_list:
        flight_number = flight_info["flight_number"]
        flight_date_data = db.get_flight_instance(flight_number, flight_info["date"])

        if flight_date_data["status"] != "available":
            raise ValueError(
                f"Flight {flight_number} not available on date {flight_info['date']}"
            )

        if flight_date_data["available_seats"][cabin] < len(passengers_list):
            raise ValueError(f"Not enough seats on flight {flight_number}")

        total_price += flight_date_data["prices"][cabin] * len(passengers_list)

    if insurance == "yes":
        total_price += 30 * len(passengers_list)
    total_price += 50 * nonfree_baggages

    for payment_method in payment_methods_list:
        payment_id = payment_method["payment_id"]
        amount = payment_method["amount"]

        if payment_id not in user["payment_methods"]:
            raise ValueError(f"Payment method {payment_id} not found")

        user_payment_method = user["payment_methods"][payment_id]
        if (
            user_payment_method["source"] in ["gift_card", "certificate"]
            and user_payment_method["amount"] < amount
        ):
            raise ValueError(f"Not enough balance in payment method {payment_id}")

    total_payment = sum(p["amount"] for p in payment_methods_list)
    if total_payment != total_price:
        raise ValueError(
            "Payment amount does not add up, total price is"
            f" {total_price}, but paid {total_payment}"
        )

    summary = (
        f"Create a new reservation from {origin} to {destination} in {cabin} "
        f"for {len(passengers_list)} passenger(s) and charge ${total_price:.2f}."
    )
    return summary, {
        "origin": origin,
        "destination": destination,
        "flight_type": flight_type,
        "cabin": cabin,
        "flights": flights_list,
        "passengers": passengers_list,
        "payment_methods": payment_methods_list,
        "total_baggages": total_baggages,
        "nonfree_baggages": nonfree_baggages,
        "insurance": insurance,
        "total_price": total_price,
    }


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
    ) -> str:
        """Create a brand-new reservation and record the full payment detail."""

        raise ValueError(
            "Direct reservation booking is disabled; use request_book_reservation"
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

        return json.dumps(reservation, indent=2)

    @mcp.tool()
    def cancel_reservation(
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
    ) -> str:
        """Cancel an existing reservation and write refund records."""

        raise ValueError(
            "Direct cancellation is disabled; use request_reservation_cancellation"
        )

        reservation = db.get_reservation(reservation_id)

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

        return json.dumps(reservation, indent=2)

    @mcp.tool()
    def get_reservation_details(
        reservation_id: Annotated[str, "The reservation ID, such as '8JX2WO'"],
    ) -> str:
        """Return the reservation payload so MCP clients can render it."""

        reservation = db.get_reservation(reservation_id)
        return json.dumps(reservation, indent=2)

    @mcp.tool()
    def update_reservation_baggages(
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        total_baggages: Annotated[int, "The updated total number of baggage items"],
        nonfree_baggages: Annotated[
            int, "The updated number of non-free baggage items"
        ],
        payment_id: Annotated[
            str,
            "The payment id stored in user profile, such as 'credit_card_7815826'",
        ],
    ) -> str:
        """Adjust baggage counts while collecting any additional payment."""

        raise ValueError(
            "Direct baggage updates are disabled; use request_baggage_update"
        )

        reservation = db.get_reservation(reservation_id)
        user = db.get_user(reservation["user_id"])

        total_price = 50 * max(0, nonfree_baggages - reservation["nonfree_baggages"])

        payment = _payment_for_update(user, payment_id, total_price)
        if payment is not None:
            reservation["payment_history"].append(payment)

        reservation["total_baggages"] = total_baggages
        reservation["nonfree_baggages"] = nonfree_baggages

        return json.dumps(reservation, indent=2)

    @mcp.tool()
    def update_reservation_flights(
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
    ) -> str:
        """Swap flights in a reservation, charging the fare difference."""

        raise ValueError(
            "Direct flight updates are disabled; use request_reservation_flight_update"
        )

        flights_list = _parse_json_argument(flights, "flights")
        if not isinstance(flights_list, list):
            raise ValueError("flights must be a JSON array")

        reservation = db.get_reservation(reservation_id)
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

        return json.dumps(reservation, indent=2)

    @mcp.tool()
    def update_reservation_passengers(
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        passengers: Annotated[
            list[dict],
            "Array of passenger objects with first_name, last_name, and dob",
        ],
    ) -> str:
        """Update passenger information while preserving passenger count."""

        raise ValueError(
            "Direct passenger updates are disabled in this hardened deployment"
        )

    @mcp.tool()
    def request_book_reservation(
        user_id: Annotated[str, "The authenticated user ID"],
        origin: Annotated[str, "The IATA code for the origin city such as 'SFO'"],
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
        total_baggages: Annotated[int, "The total number of baggage items to book"],
        nonfree_baggages: Annotated[
            int,
            "The number of non-free baggage items to book",
        ],
        insurance: Annotated[str, "Whether the reservation has insurance: 'yes' or 'no'"],
    ) -> str:
        """Preview a new booking and require confirmation before execution."""

        flights_list = _parse_json_argument(flights, "flights")
        passengers_list = _parse_json_argument(passengers, "passengers")
        payment_methods_list = _parse_json_argument(payment_methods, "payment_methods")
        if not isinstance(flights_list, list):
            raise ValueError("flights must be a JSON array")
        if not isinstance(passengers_list, list):
            raise ValueError("passengers must be a JSON array")
        if not isinstance(payment_methods_list, list):
            raise ValueError("payment_methods must be a JSON array")

        summary, details = _preview_booking(
            db,
            user_id=user_id,
            origin=origin,
            destination=destination,
            flight_type=flight_type,
            cabin=cabin,
            flights_list=flights_list,
            passengers_list=passengers_list,
            payment_methods_list=payment_methods_list,
            total_baggages=total_baggages,
            nonfree_baggages=nonfree_baggages,
            insurance=insurance,
        )
        return _make_pending_action(
            db,
            action_type="reservation_booking",
            user_id=user_id,
            reservation_id="new_reservation",
            summary=summary,
            details=details,
        )

    @mcp.tool()
    def request_reservation_flight_update(
        user_id: Annotated[str, "The authenticated user ID"],
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
    ) -> str:
        """Preview a flight-change action and require confirmation."""

        flights_list = _parse_json_argument(flights, "flights")
        if not isinstance(flights_list, list):
            raise ValueError("flights must be a JSON array")

        summary, details = _preview_flight_update(
            db,
            user_id=user_id,
            reservation_id=reservation_id,
            cabin=cabin,
            flights_list=flights_list,
            payment_id=payment_id,
        )
        return _make_pending_action(
            db,
            action_type="flight_update",
            user_id=user_id,
            reservation_id=reservation_id,
            summary=summary,
            details=details,
        )

    @mcp.tool()
    def request_baggage_update(
        user_id: Annotated[str, "The authenticated user ID"],
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        total_baggages: Annotated[int, "The updated total number of baggage items"],
        nonfree_baggages: Annotated[
            int, "The updated number of non-free baggage items"
        ],
        payment_id: Annotated[
            str,
            "The payment id stored in user profile, such as 'credit_card_7815826'",
        ],
    ) -> str:
        """Preview a baggage update and create a pending action for confirmation."""

        reservation = _require_user_owns_reservation(db, user_id, reservation_id)
        if reservation.get("status") == "cancelled":
            raise ValueError("Cannot modify a cancelled reservation")

        if total_baggages < reservation["total_baggages"]:
            raise ValueError("Checked bags can only be added, not removed")
        if nonfree_baggages < reservation["nonfree_baggages"]:
            raise ValueError("Non-free checked bags can only be added, not removed")
        if nonfree_baggages > total_baggages:
            raise ValueError("nonfree_baggages cannot exceed total_baggages")

        user = db.get_user(user_id)
        additional_charge = 50 * max(
            0, nonfree_baggages - reservation["nonfree_baggages"]
        )
        _validate_payment_for_update(user, payment_id, additional_charge)

        added_bags = total_baggages - reservation["total_baggages"]
        summary = (
            f"Add {added_bags} checked bag(s) to reservation {reservation_id} "
            f"and charge {payment_id} ${additional_charge:.2f}."
        )

        return _make_pending_action(
            db,
            action_type="baggage_update",
            user_id=user_id,
            reservation_id=reservation_id,
            summary=summary,
            details={
                "total_baggages": total_baggages,
                "nonfree_baggages": nonfree_baggages,
                "payment_id": payment_id,
                "additional_charge": additional_charge,
            },
        )

    @mcp.tool()
    def request_reservation_cancellation(
        user_id: Annotated[str, "The authenticated user ID"],
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
        reason: Annotated[
            str,
            "The user's stated reason for cancellation",
        ],
    ) -> str:
        """Preview a policy-compliant cancellation and create a pending action."""

        reservation = _require_user_owns_reservation(db, user_id, reservation_id)
        policy_basis = _cancellation_basis(db, reservation, reason)
        refunds = _refund_entries(reservation)
        refund_total = round(sum(-refund["amount"] for refund in refunds), 2)
        summary = (
            f"Cancel reservation {reservation_id} and refund ${refund_total:.2f} "
            f"to the original payment methods."
        )

        return _make_pending_action(
            db,
            action_type="reservation_cancellation",
            user_id=user_id,
            reservation_id=reservation_id,
            summary=summary,
            details={
                "reason": reason,
                "policy_basis": policy_basis,
                "refund_total": refund_total,
                "refunds": refunds,
            },
        )

    @mcp.tool()
    def request_compensation(
        user_id: Annotated[str, "The authenticated user ID"],
        reservation_id: Annotated[str, "The reservation ID, such as 'ZFA04Y'"],
    ) -> str:
        """Issue policy-compliant compensation exactly once for a reservation."""

        reservation = _require_user_owns_reservation(db, user_id, reservation_id)
        user = db.get_user(user_id)
        policy_basis, amount = _compensation_details(db, user, reservation)

        payment_ids = db.get_new_payment_ids()
        certificate_id = None
        for payment_id_num in payment_ids:
            candidate = f"certificate_{payment_id_num}"
            if candidate not in user["payment_methods"]:
                certificate_id = candidate
                user["payment_methods"][candidate] = {
                    "id": candidate,
                    "amount": amount,
                    "source": "certificate",
                }
                break

        if certificate_id is None:
            raise ValueError("Too many certificates")

        receipt = _record_receipt(
            db,
            action_type="compensation_certificate",
            user_id=user_id,
            reservation_id=reservation_id,
            summary=(
                f"Issued a compensation certificate of ${amount:.2f} "
                f"for reservation {reservation_id}."
            ),
            details={
                "policy_basis": policy_basis,
                "amount": amount,
                "certificate_id": certificate_id,
            },
        )
        _security_state(db)["compensated_reservations"][reservation_id] = receipt[
            "receipt_id"
        ]
        db.persist_security_state()
        return _serialize(receipt)

    @mcp.tool()
    def _trusted_commit_action(
        action_id: Annotated[str, "The pending action ID to execute"],
    ) -> str:
        """Execute a stored pending action exactly as previewed."""

        pending_actions = _security_state(db)["pending_actions"]
        action = pending_actions.get(action_id)
        if not action:
            raise ValueError("Pending action not found")
        if action["status"] != "pending":
            raise ValueError("Pending action was already used")

        if action["action_type"] == "baggage_update":
            receipt = _execute_baggage_update(db, action)
        elif action["action_type"] == "reservation_cancellation":
            receipt = _execute_cancellation(db, action)
        elif action["action_type"] == "flight_update":
            receipt = _execute_flight_update(db, action)
        elif action["action_type"] == "reservation_booking":
            receipt = _execute_booking(db, action)
        else:
            raise ValueError("Unsupported pending action type")

        action["status"] = "executed"
        action["receipt_id"] = receipt["receipt_id"]
        return _serialize(receipt)

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
    def get_user_details(
        user_id: Annotated[str, "The user ID, such as 'sara_doe_496'"],
    ) -> str:
        """Fetch user contact info, payment methods, and reservation IDs."""

        user = db.get_user(user_id)
        return json.dumps(user, indent=2)

    @mcp.tool()
    def send_certificate(
        user_id: Annotated[str, "The ID of the user, such as 'sara_doe_496'"],
        amount: Annotated[float, "The amount of the certificate to send"],
    ) -> str:
        """Grant the user a certificate payment method with a random ID."""

        raise ValueError(
            "Direct certificate issuance is disabled; use request_compensation"
        )

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
