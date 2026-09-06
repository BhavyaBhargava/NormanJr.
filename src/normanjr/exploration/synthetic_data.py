"""Realistic synthetic persona and test data generator for multi-step form exploration."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class SyntheticPersona:
    """A realistic, safe synthetic persona for form filling and user simulation."""
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    postal_code: str
    country: str
    company: str
    card_number: str = "4242424242424242"
    card_exp_month: str = "12"
    card_exp_year: str = "2028"
    card_cvc: str = "123"
    password: str = "NormanTest#2026Safe"
    notes: str = "Automated UX Audit Exploration"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


_FIRST_NAMES = ["Alex", "Jordan", "Morgan", "Taylor", "Sam", "Casey", "Riley", "Robin", "Cameron", "Avery"]
_LAST_NAMES = ["Sterling", "Vance", "Mercer", "Sinclair", "Hayward", "Ellington", "Chen", "Kowalski", "Patel", "Nakamura"]
_CITIES = [("Seattle", "WA", "98101"), ("Austin", "TX", "78701"), ("Boston", "MA", "02108"), ("Denver", "CO", "80202"), ("Chicago", "IL", "60601")]
_COMPANIES = ["Acme Labs", "Nimbus Tech", "Apex Digital", "Horizon Innovations", "Beacon Systems"]


def generate_synthetic_persona(seed: int | None = None) -> SyntheticPersona:
    """Generate a realistic test persona with synthetic names, addresses, and test payment credentials."""
    rng = random.Random(seed)
    first = rng.choice(_FIRST_NAMES)
    last = rng.choice(_LAST_NAMES)
    city, state, zip_code = rng.choice(_CITIES)
    company = rng.choice(_COMPANIES)
    email_user = f"{first.lower()}.{last.lower()}{rng.randint(10, 99)}"

    return SyntheticPersona(
        first_name=first,
        last_name=last,
        email=f"{email_user}@example.test",
        phone=f"+1-555-{rng.randint(100, 999):03d}-{rng.randint(1000, 9999):04d}",
        address=f"{rng.randint(100, 999)} Innovation Way, Suite {rng.randint(100, 500)}",
        city=city,
        state=state,
        postal_code=zip_code,
        country="United States",
        company=company,
    )


def match_synthetic_value(field_name_or_type: str, persona: SyntheticPersona | None = None) -> str:
    """Match form field label or input type to a realistic synthetic value."""
    p = persona or generate_synthetic_persona(42)
    s = field_name_or_type.lower()

    if any(k in s for k in ["email", "e-mail", "mail"]):
        return p.email
    if any(k in s for k in ["phone", "tel", "mobile", "cell"]):
        return p.phone
    if any(k in s for k in ["first name", "firstname", "fname", "given"]):
        return p.first_name
    if any(k in s for k in ["last name", "lastname", "lname", "surname", "family"]):
        return p.last_name
    if any(k in s for k in ["full name", "fullname", "name", "recipient"]):
        return p.full_name
    if any(k in s for k in ["street", "address", "addr"]):
        return p.address
    if any(k in s for k in ["city", "town"]):
        return p.city
    if any(k in s for k in ["state", "province", "region"]):
        return p.state
    if any(k in s for k in ["zip", "postal", "postcode"]):
        return p.postal_code
    if any(k in s for k in ["country"]):
        return p.country
    if any(k in s for k in ["company", "org", "organization", "business"]):
        return p.company
    if any(k in s for k in ["card", "credit", "pan", "account number"]):
        return p.card_number
    if any(k in s for k in ["cvc", "cvv", "security code", "cid"]):
        return p.card_cvc
    if any(k in s for k in ["exp", "expiry", "month"]):
        return f"{p.card_exp_month}/{p.card_exp_year[-2:]}"
    if any(k in s for k in ["pass", "pwd", "secret"]):
        return p.password
    if any(k in s for k in ["comment", "message", "note", "desc", "feedback"]):
        return p.notes

    return "Test input"
