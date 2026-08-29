BEGIN;

INSERT INTO audittrail_auditevent (
    id,
    action,
    target_type,
    target_id,
    metadata,
    created_at,
    actor_id
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'verification.created',
    'verification.Target',
    'postgresql-trigger-check',
    '{}',
    CURRENT_TIMESTAMP,
    NULL
);

DO $$
BEGIN
    BEGIN
        UPDATE audittrail_auditevent
        SET action = 'verification.changed'
        WHERE id = '00000000-0000-0000-0000-000000000001';
    EXCEPTION WHEN raise_exception THEN
        RAISE NOTICE 'Update correctly blocked by immutable audit trigger';
    END;

    IF EXISTS (
        SELECT 1 FROM audittrail_auditevent
        WHERE id = '00000000-0000-0000-0000-000000000001'
          AND action <> 'verification.created'
    ) THEN
        RAISE EXCEPTION 'Audit update was not blocked';
    END IF;

    BEGIN
        DELETE FROM audittrail_auditevent
        WHERE id = '00000000-0000-0000-0000-000000000001';
    EXCEPTION WHEN raise_exception THEN
        RAISE NOTICE 'Delete correctly blocked by immutable audit trigger';
    END;

    IF NOT EXISTS (
        SELECT 1 FROM audittrail_auditevent
        WHERE id = '00000000-0000-0000-0000-000000000001'
    ) THEN
        RAISE EXCEPTION 'Audit delete was not blocked';
    END IF;
END $$;

ROLLBACK;
