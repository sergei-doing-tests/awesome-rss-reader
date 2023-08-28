# ruff: noqa: INP001
"""initial

Revision ID: 0001
Revises:
Create Date: 2023-08-28 19:01:22.359778

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "feed",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="feed_url_key"),
    )
    op.create_table(
        "feed_post",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("guid", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], name="feed_post_feed_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_id", "guid", name="feed_post_feed_id_guid_key"),
    )
    op.create_index(op.f("ix_feed_post_feed_id"), "feed_post", ["feed_id"], unique=False)
    op.create_table(
        "feed_refresh_job",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.Integer(), nullable=False),
        sa.Column("execute_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retries", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], name="feed_refresh_job_feed_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_id", name="feed_refresh_job_feed_id_key"),
    )
    op.create_table(
        "user_feed",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_uid", sa.UUID(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], name="user_feed_feed_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_uid", "feed_id", name="user_feed_user_uid_feed_id_key"),
    )
    op.create_table(
        "user_post",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_uid", sa.UUID(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["feed_post.id"], name="user_post_post_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_uid", "post_id", name="user_post_user_uid_post_id_key"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("user_post")
    op.drop_table("user_feed")
    op.drop_table("feed_refresh_job")
    op.drop_index(op.f("ix_feed_post_feed_id"), table_name="feed_post")
    op.drop_table("feed_post")
    op.drop_table("feed")
    # ### end Alembic commands ###
