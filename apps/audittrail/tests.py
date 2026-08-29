import pytest

from apps.audittrail.models import AuditEvent

pytestmark = pytest.mark.django_db


def test_audit_events_cannot_be_changed_or_deleted():
    event = AuditEvent.objects.create(
        action="test.created",
        target_type="tests.Target",
        target_id="one",
    )
    event.action = "test.changed"

    with pytest.raises(TypeError, match="immutable"):
        event.save()
    with pytest.raises(TypeError, match="cannot be deleted"):
        event.delete()
    with pytest.raises(TypeError, match="immutable"):
        AuditEvent.objects.filter(pk=event.pk).update(action="test.changed")
    with pytest.raises(TypeError, match="cannot be deleted"):
        AuditEvent.objects.filter(pk=event.pk).delete()
