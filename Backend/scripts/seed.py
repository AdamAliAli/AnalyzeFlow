"""Seed lookup tables, a demo admin, and the Damascus Restaurant case study.

Idempotent: safe to run repeatedly.

    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.case_study import CaseStudy
from app.models.enums import UserRole
from app.models.lookup import BusinessStage, Challenge, Goal, Industry
from app.models.user import User

INDUSTRIES = [
    ("Restaurant", "restaurant", "Food service and hospitality."),
    ("E-commerce", "ecommerce", "Online retail and direct-to-consumer."),
    ("Agency", "agency", "Services sold to other businesses."),
    ("Portfolio", "portfolio", "Personal or studio showcase site."),
    ("Education", "education", "Courses, training and institutions."),
    ("Healthcare", "healthcare", "Clinics, practitioners and health services."),
]

GOALS = [
    ("Increase Sales", "increase_sales", "Convert more visitors into paying customers."),
    ("Generate More Leads", "generate_more_leads", "Collect more qualified enquiries."),
    ("Brand Awareness", "brand_awareness", "Reach more of the right audience."),
    ("Customer Journey", "customer_journey", "Smooth the path from interest to purchase."),
]

CHALLENGES = [
    ("Low Online Visibility", "low_online_visibility", "The business is difficult to discover online."),
    ("Low Sales", "low_sales", "The business is not generating sufficient sales."),
    ("Poor User Experience", "poor_user_experience", "Customers face friction using the product or service."),
    ("Unclear Value Proposition", "unclear_value_proposition", "Customers do not clearly understand the value offered."),
    ("Low Customer Retention", "low_customer_retention", "The business struggles to retain customers over time."),
    ("Low Conversion Rate", "low_conversion_rate", "A low percentage of prospects complete the desired action."),
]

STAGES = [
    ("Idea Stage", "idea_stage", "The business is still at the idea or validation stage."),
    ("Startup", "startup", "The business has started operations and is building traction."),
    ("Small Business", "small_business", "An operating small business serving an established market."),
    ("Growing Business", "growing_business", "A business experiencing growth and expanding operations."),
]

CASE_STUDY = {
    "slug": "damascus-restaurant",
    "title": "Damascus Restaurant",
    "industry_label": "Restaurant",
    "summary": (
        "A family-run Levantine restaurant with strong walk-in trade but almost "
        "no online orders. The website looked fine and still converted nobody."
    ),
    "content": (
        "## The situation\n\n"
        "Damascus Restaurant had a modern-looking single-page website: good "
        "photography, a clear menu, an address. Foot traffic was healthy. "
        "Online orders were close to zero.\n\n"
        "## What the framework surfaced\n\n"
        "Working through the five questions showed the problem was never "
        "design. The site answered *what we serve* but never *what to do "
        "next*. There was no ordering link above the fold, no delivery "
        "information, and the phone number was an image rather than a tap-to-"
        "call link on mobile - where most of the traffic was.\n\n"
        "## What changed\n\n"
        "One primary call to action, a tap-to-call phone number, delivery "
        "hours stated plainly, and a menu page search engines could actually "
        "read.\n\n"
        "## The lesson\n\n"
        "A beautiful site that does not tell visitors what to do next is a "
        "brochure, not a business tool."
    ),
    "client_type": "Family-owned Levantine restaurant serving a local urban area.",
    "user_type": "Nearby residents ordering dinner from a phone, usually after 6pm.",
    "problem": (
        "Hungry people nearby could not order in under a minute, so they "
        "ordered from a competitor who let them."
    ),
    "value_proposition": (
        "Authentic home-style Levantine food, delivered hot, ordered in two taps."
    ),
    "revenue_model": "Direct food sales, split between dine-in and delivery orders.",
    "key_insight": (
        "The website was not underperforming because it looked bad. It was "
        "underperforming because it had no next step."
    ),
    "is_published": True,
}


async def _seed_lookup(db, model, rows) -> None:
    for order, (name, slug, description) in enumerate(rows):
        existing = await db.scalar(select(model).where(model.slug == slug))
        if existing is None:
            db.add(
                model(
                    name=name, slug=slug, description=description, sort_order=order
                )
            )
        else:
            existing.name = name
            existing.description = description
            existing.sort_order = order
            existing.is_active = True
    await db.commit()


async def _seed_admin(db) -> None:
    # Not a .local / .test address: EmailStr rejects reserved TLDs, so a
    # seeded admin on one of those could never actually log in.
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@analyzeflow.dev")
    password = os.getenv("SEED_ADMIN_PASSWORD", "Admin12345")

    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        print(f"  admin already exists: {email}")
        return

    db.add(
        User(
            full_name="AnalyzeFlow Admin",
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
        )
    )
    await db.commit()
    print(f"  admin created: {email} / {password}")
    print("  ^ change this before anything is deployed publicly")


async def _seed_case_study(db) -> None:
    existing = await db.scalar(
        select(CaseStudy).where(CaseStudy.slug == CASE_STUDY["slug"])
    )
    if existing is None:
        db.add(CaseStudy(**CASE_STUDY))
        await db.commit()


async def main() -> None:
    async with AsyncSessionLocal() as db:
        print("Seeding lookups...")
        await _seed_lookup(db, Industry, INDUSTRIES)
        await _seed_lookup(db, Goal, GOALS)
        await _seed_lookup(db, Challenge, CHALLENGES)
        await _seed_lookup(db, BusinessStage, STAGES)

        print("Seeding admin user...")
        await _seed_admin(db)

        print("Seeding case study...")
        await _seed_case_study(db)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
