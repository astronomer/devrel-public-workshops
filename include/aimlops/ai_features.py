_TRIP_OCCASIONS = ["celebration", "family", "business", "budget", "adventure", "other"]
_LEVELS = ["low", "medium", "high"]


def synthetic_ai_features(bookings: list[dict]) -> list[dict]:
    # Deterministic stand-in AI features for historical bookings, so we don't run the
    # token-expensive extraction agent over the whole back-catalogue during the workshop.
    records = []
    for b in bookings:
        bid = b["booking_id"]
        flipped = (bid * 23) % 10 == 0
        budget_signal = _LEVELS[(bid * 29) % 3] if flipped else _LEVELS[(bid * 17) % 3]
        records.append(
            {
                "booking_id": bid,
                "trip_occasion": _TRIP_OCCASIONS[(bid * 3) % 6],
                "enthusiasm": _LEVELS[(bid * 7) % 3],
                "budget_signal": budget_signal,
            }
        )
    return records
