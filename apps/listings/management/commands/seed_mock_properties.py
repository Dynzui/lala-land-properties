from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.listings.models import Listing, Offer
from apps.listings.services import publish_listing
from apps.properties.models import Development, Location, Property, PropertyType, Variant


class Command(BaseCommand):
    help = "Create or refresh a small, clearly labelled demo property catalogue."

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        owner = user_model.objects.filter(
            role=user_model.Role.OWNER,
            status=user_model.Status.ACTIVE,
        ).first()
        if owner is None:
            raise CommandError("Create an active Owner account before seeding demo listings.")

        locations = self._locations()
        developments = self._developments(locations)
        variants = self._variants(developments)
        properties = self._properties(locations, developments, variants)

        catalogue = [
            {
                "slug": "demo-amara-at-verdant-heights",
                "title": "Amara at Verdant Heights",
                "summary": "A bright three-bedroom family home in a peaceful Bacolod community.",
                "description": (
                    "<p>A welcoming mock family home with open-plan living, practical storage, "
                    "and access to landscaped community spaces.</p>"
                ),
                "variant": variants["amara"],
                "quantity": 4,
                "transaction": Offer.TransactionType.SALE,
                "price": Decimal("4200000"),
                "featured": True,
            },
            {
                "slug": "demo-eliana-at-verdant-heights",
                "title": "Eliana at Verdant Heights",
                "summary": "A spacious four-bedroom model designed for growing families.",
                "description": (
                    "<p>A polished mock listing with flexible living areas, a generous primary "
                    "suite, and room for a home office.</p>"
                ),
                "variant": variants["eliana"],
                "quantity": 2,
                "transaction": Offer.TransactionType.SALE,
                "price": Decimal("5800000"),
            },
            {
                "slug": "demo-north-grove-townhouse",
                "title": "North Grove Townhouse",
                "summary": "A convenient two-bedroom rental close to Talisay essentials.",
                "description": (
                    "<p>A low-maintenance mock townhouse with two bedrooms, parking, and a "
                    "comfortable layout for a small household.</p>"
                ),
                "variant": variants["north_grove"],
                "quantity": 3,
                "transaction": Offer.TransactionType.RENT,
                "price": Decimal("28000"),
                "rent_period": Offer.RentPeriod.MONTHLY,
                "featured": True,
            },
            {
                "slug": "demo-silay-heritage-home",
                "title": "Silay Heritage-Inspired Home",
                "summary": "A character-filled three-bedroom home near the heart of Silay.",
                "description": (
                    "<p>This mock standalone home pairs heritage-inspired details with modern "
                    "family spaces and a private garden.</p>"
                ),
                "property": properties["silay_home"],
                "transaction": Offer.TransactionType.SALE,
                "price": Decimal("6500000"),
                "public_status": Listing.PublicStatus.RESERVED,
            },
            {
                "slug": "demo-bacolod-city-apartment",
                "title": "Bacolod City Apartment",
                "summary": "A furnished one-bedroom rental for easy city living.",
                "description": (
                    "<p>A compact mock apartment with a furnished interior and convenient access "
                    "to shopping, dining, and transport.</p>"
                ),
                "property": properties["city_apartment"],
                "transaction": Offer.TransactionType.RENT,
                "price": Decimal("22000"),
                "rent_period": Offer.RentPeriod.MONTHLY,
            },
            {
                "slug": "demo-serenity-gardens-memorial-lot",
                "title": "Serenity Gardens Memorial Lot",
                "summary": "A thoughtfully located memorial lot in a calm landscaped setting.",
                "description": (
                    "<p>A respectful mock memorial property listing with accessible pathways and "
                    "a quiet garden environment.</p>"
                ),
                "variant": variants["memorial"],
                "quantity": 12,
                "transaction": Offer.TransactionType.SALE,
                "price": Decimal("180000"),
                "price_display": Offer.PriceDisplay.STARTING_AT,
            },
        ]

        for item in catalogue:
            self._listing(owner, item)

        self.stdout.write(self.style.SUCCESS(f"Demo catalogue ready: {len(catalogue)} listings."))

    def _locations(self):
        records = {
            "bacolod": ("", "City of Bacolod", "10.676500", "122.950900"),
            "talisay": ("Negros Occidental", "City of Talisay", "10.736900", "122.966300"),
            "silay": ("Negros Occidental", "City of Silay", "10.800000", "122.977000"),
            "murcia": ("Negros Occidental", "Murcia", "10.605200", "123.041700"),
        }
        result = {}
        for key, (province, city, latitude, longitude) in records.items():
            location, _ = Location.objects.update_or_create(
                public_label=f"{city}, Negros Occidental",
                defaults={
                    "country_code": "PH",
                    "region": "Negros Island Region (NIR)",
                    "province": province,
                    "city_municipality": city,
                    "visibility": Location.Visibility.APPROXIMATE,
                    "public_latitude": Decimal(latitude),
                    "public_longitude": Decimal(longitude),
                },
            )
            result[key] = location
        return result

    def _developments(self, locations):
        records = {
            "verdant": (
                "Demo Verdant Heights",
                "demo-verdant-heights",
                Development.Type.SUBDIVISION,
                locations["bacolod"],
            ),
            "north_grove": (
                "Demo North Grove",
                "demo-north-grove",
                Development.Type.SUBDIVISION,
                locations["talisay"],
            ),
            "serenity": (
                "Demo Serenity Gardens",
                "demo-serenity-gardens",
                Development.Type.MEMORIAL_PARK,
                locations["murcia"],
            ),
        }
        result = {}
        for key, (name, slug, development_type, location) in records.items():
            development, _ = Development.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "development_type": development_type,
                    "location": location,
                    "summary": "Demonstration content for the Lala Land website.",
                    "description": "<p>This is a mock development and not a real offer.</p>",
                    "status": Development.Status.ACTIVE,
                },
            )
            result[key] = development
        return result

    def _variants(self, developments):
        house = PropertyType.objects.get(slug="house-and-lot")
        townhouse = PropertyType.objects.get(slug="townhouse")
        memorial = PropertyType.objects.get(slug="memorial-lot")
        records = {
            "amara": (developments["verdant"], house, "Amara", 3, Decimal("2.0"), 110, 140),
            "eliana": (developments["verdant"], house, "Eliana", 4, Decimal("3.0"), 160, 200),
            "north_grove": (
                developments["north_grove"],
                townhouse,
                "North Grove Two Bedroom",
                2,
                Decimal("1.5"),
                72,
                80,
            ),
            "memorial": (
                developments["serenity"],
                memorial,
                "Heritage Lawn",
                None,
                None,
                None,
                3,
            ),
        }
        result = {}
        for key, (
            development,
            property_type,
            name,
            bedrooms,
            bathrooms,
            floor,
            lot,
        ) in records.items():
            variant, _ = Variant.objects.update_or_create(
                development=development,
                slug=f"demo-{key.replace('_', '-')}",
                defaults={
                    "property_type": property_type,
                    "name": name,
                    "description": "<p>Mock variant used for website testing.</p>",
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "floor_area_sqm": floor,
                    "lot_area_sqm": lot,
                    "memorial_capacity": 2 if key == "memorial" else None,
                    "status": Variant.Status.ACTIVE,
                },
            )
            result[key] = variant
        return result

    def _properties(self, locations, developments, variants):
        house = PropertyType.objects.get(slug="house-and-lot")
        apartment = PropertyType.objects.get(slug="apartment")
        records = {
            "silay_home": {
                "reference_code": "DEMO-SILAY-HOME-001",
                "location": locations["silay"],
                "property_type": house,
                "title_override": "Demo Silay Heritage-Inspired Home",
                "bedrooms": 3,
                "bathrooms": Decimal("2.0"),
                "parking_spaces": 2,
                "floor_area_sqm": 145,
                "lot_area_sqm": 260,
                "inventory_status": Property.InventoryStatus.RESERVED,
            },
            "city_apartment": {
                "reference_code": "DEMO-BACOLOD-APT-001",
                "location": locations["bacolod"],
                "development": developments["verdant"],
                "property_type": apartment,
                "title_override": "Demo Bacolod City Apartment",
                "bedrooms": 1,
                "bathrooms": Decimal("1.0"),
                "floor_area_sqm": 42,
                "furnishing": Property.Furnishing.FURNISHED,
                "inventory_status": Property.InventoryStatus.AVAILABLE,
            },
        }
        result = {}
        for key, values in records.items():
            reference_code = values.pop("reference_code")
            record, _ = Property.objects.update_or_create(
                reference_code=reference_code,
                defaults=values,
            )
            result[key] = record
        return result

    def _listing(self, owner, item):
        target_property = item.get("property")
        target_variant = item.get("variant")
        inventory_mode = (
            Listing.InventoryMode.SINGLE if target_property else Listing.InventoryMode.POOLED
        )
        listing, created = Listing.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "property": target_property,
                "variant": target_variant,
                "title": item["title"],
                "summary": item["summary"],
                "description": item["description"],
                "inventory_mode": inventory_mode,
                "available_quantity": item.get("quantity"),
            },
        )
        listing.property = target_property
        listing.variant = target_variant
        listing.title = item["title"]
        listing.summary = item["summary"]
        listing.description = item["description"]
        listing.inventory_mode = inventory_mode
        listing.available_quantity = item.get("quantity")
        listing.public_status = item.get("public_status", Listing.PublicStatus.AVAILABLE)
        listing.featured = item.get("featured", False)
        listing.save()

        Offer.objects.update_or_create(
            listing=listing,
            active=True,
            defaults={
                "transaction_type": item["transaction"],
                "currency": "PHP",
                "price_display": item.get("price_display", Offer.PriceDisplay.EXACT),
                "price_min": item["price"],
                "price_max": None,
                "rent_period": item.get("rent_period", ""),
            },
        )
        if created or listing.workflow_status != Listing.WorkflowStatus.PUBLISHED:
            publish_listing(actor=owner, listing=listing)
