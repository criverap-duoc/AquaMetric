"""initial schema in the aquametric schema

Revision ID: 20261024_0001
Revises:
Create Date: 2026-10-24

Written by hand on purpose: `CREATE SCHEMA` has to run before autogenerate could compare
anything, and the constraint names must match `app/models` byte for byte (ADR-008/009).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261024_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "aquametric"


def upgrade() -> None:
    """Create the schema and the five phase-A tables."""
    op.execute("CREATE SCHEMA IF NOT EXISTS aquametric")

    op.create_table(
        "site",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("water_body_type", sa.String(length=20), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "water_body_type IN "
            "('river', 'lake', 'estuary', 'groundwater', 'effluent', 'drinking')",
            name=op.f("ck_site_valid_water_body_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site")),
        sa.UniqueConstraint("code", name=op.f("uq_site_code")),
        schema=SCHEMA,
    )

    op.create_table(
        "sample",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("matrix", sa.String(length=20), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lab_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "status IN ('collected', 'in_transit', 'received', 'analyzed', 'rejected')",
            name=op.f("ck_sample_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            [f"{SCHEMA}.site.id"],
            name=op.f("fk_sample_site_id_site"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sample")),
        schema=SCHEMA,
    )

    op.create_table(
        "observation",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=True),
        sa.Column("parameter_code", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("unit_code", sa.String(length=16), nullable=False),
        sa.Column("qualifier", sa.String(length=1), nullable=True),
        sa.Column("loq", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("method", sa.String(length=255), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("qc_flag", sa.String(length=10), server_default=sa.text("'ok'"), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.CheckConstraint("qualifier IN ('<', '>')", name=op.f("ck_observation_valid_qualifier")),
        sa.CheckConstraint(
            "qc_flag IN ('ok', 'suspect', 'failed')",
            name=op.f("ck_observation_valid_qc_flag"),
        ),
        sa.CheckConstraint(
            "source IN ('lab', 'field', 'sensor')",
            name=op.f("ck_observation_valid_source"),
        ),
        # Censored rows keep the LOQ and no value: never 0, never LOQ/2 (ADR-003).
        sa.CheckConstraint(
            "(value IS NULL AND qualifier = '<' AND loq IS NOT NULL) "
            "OR (value IS NOT NULL AND qualifier IS NULL)",
            name=op.f("ck_observation_censored_coherence"),
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            [f"{SCHEMA}.site.id"],
            name=op.f("fk_observation_site_id_site"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            [f"{SCHEMA}.sample.id"],
            name=op.f("fk_observation_sample_id_sample"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_observation")),
        # Short name because the convention-generated one exceeds PostgreSQL's 63 bytes.
        sa.UniqueConstraint(
            "site_id",
            "parameter_code",
            "analyzed_at",
            "sample_id",
            "source",
            name=op.f("uq_obs_natural_key"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_obs_site_param_time",
        "observation",
        ["site_id", "parameter_code", "analyzed_at"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "ingest_idempotency",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "status IN ('success', 'failure')",
            name=op.f("ck_ingest_idempotency_valid_status"),
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_ingest_idempotency")),
        schema=SCHEMA,
    )

    op.create_table(
        "spc_baseline",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("parameter_code", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=10), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("n_points", sa.Integer(), nullable=False),
        sa.Column("data_range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("center_line", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("ucl", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("lcl", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("catalog_version", sa.String(length=20), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "phase IN ('phase_i', 'phase_ii')",
            name=op.f("ck_spc_baseline_valid_phase"),
        ),
        sa.CheckConstraint(
            "method IN ('imr', 'xbar_r')",
            name=op.f("ck_spc_baseline_valid_method"),
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            [f"{SCHEMA}.site.id"],
            name=op.f("fk_spc_baseline_site_id_site"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_spc_baseline")),
        sa.UniqueConstraint(
            "site_id",
            "parameter_code",
            "phase",
            name=op.f("uq_baseline_site_param_phase"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop the schema and everything in it.

    Alembic deletes its version row *after* this function returns, in the same transaction, so
    the schema and an empty `alembic_version` are recreated here: without them that bookkeeping
    fails with `UndefinedTable`. Removing the schema for good stays a manual DBA step.
    """
    op.drop_index("ix_obs_site_param_time", table_name="observation", schema=SCHEMA)
    op.drop_table("spc_baseline", schema=SCHEMA)
    op.drop_table("ingest_idempotency", schema=SCHEMA)
    op.drop_table("observation", schema=SCHEMA)
    op.drop_table("sample", schema=SCHEMA)
    op.drop_table("site", schema=SCHEMA)
    op.execute("DROP SCHEMA IF EXISTS aquametric CASCADE")
    op.execute("CREATE SCHEMA IF NOT EXISTS aquametric")
    op.execute(
        "CREATE TABLE aquametric.alembic_version ("
        "version_num VARCHAR(32) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    )
    # Must stay equal to the `revision` value above: Alembic deletes exactly this row next.
    op.execute("INSERT INTO aquametric.alembic_version (version_num) VALUES ('20261024_0001')")
