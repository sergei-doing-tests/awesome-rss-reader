import sqlalchemy as sa

metadata = sa.MetaData()


Feed = sa.Table(
    "feed",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("url", sa.Text, nullable=False),
    sa.Column("title", sa.Text, nullable=True),
    sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.UniqueConstraint("url", name="feed_url_key"),
)


FeedPost = sa.Table(
    "feed_post",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("feed_id", sa.Integer, nullable=False, index=True),
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("summary", sa.Text, nullable=True),
    sa.Column("url", sa.Text, nullable=False),
    sa.Column("guid", sa.Text, nullable=False),
    sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], name="feed_post_feed_id_fkey"),
    sa.UniqueConstraint("feed_id", "guid", name="feed_post_feed_id_guid_key"),
)


UserFeed = sa.Table(
    "user_feed",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("user_uid", sa.UUID, nullable=False),
    sa.Column("feed_id", sa.Integer, nullable=False),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], name="user_feed_feed_id_fkey"),
    sa.UniqueConstraint("user_uid", "feed_id", name="user_feed_user_uid_feed_id_key"),
)

UserPost = sa.Table(
    "user_post",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("user_uid", sa.UUID, nullable=False),
    sa.Column("post_id", sa.Integer, nullable=False),
    sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["post_id"], ["feed_post.id"], name="user_post_post_id_fkey"),
    sa.UniqueConstraint("user_uid", "post_id", name="user_post_user_uid_post_id_key"),
)


FeedRefreshJob = sa.Table(
    "feed_refresh_job",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("feed_id", sa.Integer, nullable=False),
    sa.Column("state", sa.Integer, nullable=False),
    sa.Column(
        "state_changed_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("execute_after", sa.DateTime(timezone=True), nullable=False),
    sa.Column("retries", sa.Integer, nullable=False, server_default="0"),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], name="feed_refresh_job_feed_id_fkey"),
    sa.UniqueConstraint("feed_id", name="feed_refresh_job_feed_id_key"),
)
