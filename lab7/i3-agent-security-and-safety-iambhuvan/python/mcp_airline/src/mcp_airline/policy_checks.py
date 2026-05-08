"""Deterministic policy checks for safety-critical airline actions."""

from __future__ import annotations

from datetime import datetime, timedelta

from .database import AirlineDatabase


INSURANCE_COVERED_REASONS = {"health", "weather"}


def reservation_belongs_to_user(reservation: dict, user_id: str) -> bool:
    """Return whether the reservation is owned by the supplied user."""

    return reservation["user_id"] == user_id


def reservation_has_flown_segment(db: AirlineDatabase, reservation: dict) -> bool:
    """Return True if any flight segment has already departed or landed."""

    for flight in reservation["flights"]:
        status = db.get_flight_instance(flight["flight_number"], flight["date"])["status"]
        if status in {"flying", "landed"}:
            return True
    return False


def reservation_has_cancelled_segment(db: AirlineDatabase, reservation: dict) -> bool:
    """Return True if any flight segment was cancelled by the airline."""

    for flight in reservation["flights"]:
        status = db.get_flight_instance(flight["flight_number"], flight["date"])["status"]
        if status == "cancelled":
            return True
    return False


def reservation_has_delayed_segment(db: AirlineDatabase, reservation: dict) -> bool:
    """Return True if any flight segment is delayed."""

    for flight in reservation["flights"]:
        status = db.get_flight_instance(flight["flight_number"], flight["date"])["status"]
        if status == "delayed":
            return True
    return False


def reservation_is_already_cancelled(reservation: dict) -> bool:
    """Return True if the reservation has already been cancelled."""

    return reservation.get("status") == "cancelled"


def reservation_booked_within_24_hours(db: AirlineDatabase, reservation: dict) -> bool:
    """Return True if the reservation was created within the last 24 hours."""

    current_time = datetime.fromisoformat(db.get_date_time())
    created_at = datetime.fromisoformat(reservation["created_at"])
    return current_time - created_at <= timedelta(hours=24)


def reservation_allows_cancellation(
    db: AirlineDatabase,
    reservation: dict,
    reason_category: str,
) -> tuple[bool, str]:
    """Evaluate the cancellation policy and explain the decision."""

    reason = reason_category.strip().lower()
    if reservation_is_already_cancelled(reservation):
        return False, "Reservation is already cancelled."

    if reservation_has_flown_segment(db, reservation):
        return False, "Cannot cancel because part of the itinerary has already been flown."

    if reservation_booked_within_24_hours(db, reservation):
        return True, "Reservation was booked within the last 24 hours."

    if reservation_has_cancelled_segment(db, reservation):
        return True, "A flight segment in the reservation was cancelled by the airline."

    if reservation["cabin"] == "business":
        return True, "Business reservations are cancellable under the policy."

    if reservation["insurance"] == "yes" and reason in INSURANCE_COVERED_REASONS:
        return True, "Travel insurance covers the supplied cancellation reason."

    return False, "Cancellation policy requirements were not met."


def user_is_compensation_eligible(user: dict, reservation: dict) -> bool:
    """Return True when the user qualifies for compensation under the policy."""

    return (
        user["membership"] in {"silver", "gold"}
        or reservation["insurance"] == "yes"
        or reservation["cabin"] == "business"
    )


_ALLOWED_COMPENSATION_EVENTS = frozenset({"cancelled", "delayed"})


def compensation_quote(
    db: AirlineDatabase,
    user: dict,
    reservation: dict,
    event_type: str,
) -> tuple[int, str]:
    """Compute compensation amount for a supported event or raise ValueError.

    Enforces the full policy from data/airline/policy.md:
    - Eligibility: silver/gold member, travel insurance, or business cabin.
    - Cancelled-flight compensation: $100 × passengers, only when the airline
      cancelled a flight segment in this reservation.
    - Delayed-flight compensation: $50 × passengers, only when a flight segment
      is currently delayed AND the user has already changed or cancelled the
      reservation (confirmed via action receipts).
    - No other event types are compensated.
    """
    normalized = event_type.strip().lower()

    # Strict whitelist — reject any event type not defined in the policy.
    if normalized not in _ALLOWED_COMPENSATION_EVENTS:
        raise ValueError(
            f"Compensation is only allowed for 'cancelled' or 'delayed' events, "
            f"not '{event_type}'"
        )

    if not user_is_compensation_eligible(user, reservation):
        raise ValueError("User is not eligible for compensation under the policy")

    passengers = len(reservation["passengers"])

    if normalized == "cancelled":
        # Policy: airline must have cancelled a flight segment in this reservation.
        if not reservation_has_cancelled_segment(db, reservation):
            raise ValueError(
                "Cancelled-flight compensation requires an airline-cancelled flight "
                "segment in the reservation"
            )
        return passengers * 100, "Cancelled flight compensation"

    # normalized == "delayed"
    # Policy: a flight segment must currently be delayed.
    if not reservation_has_delayed_segment(db, reservation):
        raise ValueError(
            "Delayed-flight compensation requires a currently-delayed flight segment "
            "in the reservation"
        )
    # Policy: the user must have already changed or cancelled the reservation
    # (the agent must confirm the facts and act before compensation is offered).
    receipts = db.get_action_receipts(reservation["user_id"])
    has_follow_on_action = any(
        receipt["reservation_id"] == reservation["reservation_id"]
        and receipt["status"] == "completed"
        and receipt["action_type"] in {"cancel_reservation", "update_reservation_flights"}
        for receipt in receipts
    )
    if not has_follow_on_action:
        raise ValueError(
            "Delayed-flight compensation is only allowed after the reservation was changed or cancelled"
        )
    return passengers * 50, "Delayed flight compensation"
