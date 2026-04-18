from src.lending.models import Credit, CreditTier, AdverseEvent


def get_credit_tier(score: int) -> CreditTier:
    if score >= 750:
        return CreditTier.EXCELLENT
    elif score >= 700:
        return CreditTier.GOOD
    elif score >= 650:
        return CreditTier.FAIR
    elif score >= 620:
        return CreditTier.MINIMUM
    else:
        return CreditTier.BELOW_MINIMUM


def check_adverse_events(events: list[AdverseEvent]) -> tuple[bool, list[str]]:
    has_blocking = False
    flags = []
    
    for event in events:
        if event.event_type == "bankruptcy_ch7" and event.years_ago <= 4:
            has_blocking = True
            flags.append("recent_ch7")
        elif event.event_type == "bankruptcy_ch13" and event.years_ago <= 2:
            has_blocking = True
            flags.append("recent_ch13")
        elif event.event_type == "foreclosure" and event.years_ago <= 3:
            has_blocking = True
            flags.append("recent_foreclosure")
        elif event.event_type == "collections":
            if event.subtype == "medical" and event.amount < 500:
                pass
            elif event.amount > 500:
                flags.append("large_collections")
    
    return has_blocking, flags


def is_credit_acceptable(credit: Credit) -> tuple[bool, str, list[str]]:
    if credit.score < 620:
        return False, "score_below_minimum", []
    
    has_blocking, flags = check_adverse_events(credit.adverse_events)
    if has_blocking:
        return False, "blocking_adverse_event", flags
    
    if flags:
        return True, "credit_with_flags", flags
    
    return True, "credit_clean", []