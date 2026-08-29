from collections.abc import Mapping

from .models import User


class Capability:
    STAFF_MANAGE = "staff.manage"
    LISTING_MANAGE = "listing.manage"
    LISTING_PUBLISH = "listing.publish"
    INQUIRY_MANAGE = "inquiry.manage"
    ARTICLE_MANAGE = "article.manage"
    GLOBAL_CONTENT_MANAGE = "global_content.manage"
    PRIVATE_LOCATION_VIEW = "private_location.view"
    PHONE_NUMBER_VIEW = "phone_number.view"
    CUSTOMER_DATA_EXPORT = "customer_data.export"
    AUDIT_EXPORT = "audit.export"
    TECHNICAL_MAINTAIN = "technical.maintain"


ROLE_CAPABILITIES: Mapping[str, frozenset[str]] = {
    User.Role.OWNER: frozenset(
        {
            Capability.STAFF_MANAGE,
            Capability.LISTING_MANAGE,
            Capability.LISTING_PUBLISH,
            Capability.INQUIRY_MANAGE,
            Capability.ARTICLE_MANAGE,
            Capability.GLOBAL_CONTENT_MANAGE,
            Capability.PRIVATE_LOCATION_VIEW,
            Capability.PHONE_NUMBER_VIEW,
            Capability.CUSTOMER_DATA_EXPORT,
            Capability.AUDIT_EXPORT,
            Capability.TECHNICAL_MAINTAIN,
        }
    ),
    User.Role.ADMIN: frozenset(
        {
            Capability.LISTING_MANAGE,
            Capability.LISTING_PUBLISH,
            Capability.INQUIRY_MANAGE,
            Capability.ARTICLE_MANAGE,
        }
    ),
    User.Role.MAINTAINER: frozenset({Capability.TECHNICAL_MAINTAIN}),
    User.Role.CUSTOMER: frozenset(),
}


def user_has_capability(user: User, capability: str) -> bool:
    if not user.is_authenticated or user.status != User.Status.ACTIVE:
        return False
    return capability in ROLE_CAPABILITIES.get(user.role, frozenset())
