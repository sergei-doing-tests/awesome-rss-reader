# ruff: noqa: E501
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
import sqlalchemy as sa
from pytest_localserver.http import ContentServer
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.application.settings import ApplicationSettings
from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobState,
    NewFeedRefreshJob,
)
from awesome_rss_reader.core.usecase.update_feed_content import (
    UpdateFeedContentInput,
    UpdateFeedContentUseCase,
)
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import NewFeedFactory, NewFeedPostFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    FetchOneFixtureT,
    InsertFeedPostsFixtureT,
    InsertFeedsFixtureT,
    InsertRefreshJobsFixtureT,
)

# fmt: off
POST_GARMIN = (
    """
    <item>
      <title>Garmin brengt Venu 3-smartwatches met iets langere accuduur uit voor 500 euro</title>
      <link>https://tweakers.net/nieuws/213068/garmin-brengt-venu-3-smartwatches-met-iets-langere-accuduur-uit-voor-500-euro.html</link>
      <description>Garmin heeft de Venu 3-smartwatchserie uitgebracht. De serie bestaat uit de 45mm-Venu 3 en de 41mm-Venu 3S. </description>
      <author>Hayte Hugo</author>
      <category>Nieuws / Tablets en telefoons / Smartwatches</category>
      <comments>https://tweakers.net/nieuws/213068/garmin-brengt-venu-3-smartwatches-met-iets-langere-accuduur-uit-voor-500-euro.html#reacties</comments>
      <guid isPermaLink="false">https://tweakers.net/nieuws/213068</guid>
      <pubDate>Wed, 30 Aug 2023 12:29:25 GMT</pubDate>
    </item>
    """
)
POST_MIMIMI = (
    """
    <item>
      <title>Duitse studio achter Shadow Tactics- en Desperados III-games Mimimi stopt</title>
      <link>https://tweakers.net/nieuws/213066/duitse-studio-achter-shadow-tactics-en-desperados-iii-games-mimimi-stopt.html</link>
      <description>Mimimi Games houdt op te bestaan. Het bedrijf bracht sinds 2011 meerdere stealth-strategiegames uit, maar de twee oprichters en directeuren zeggen niet genoeg energie meer te hebben om verder te gaan.</description>
      <author>Hayte Hugo</author>
      <category>Nieuws / Gaming / Games</category>
      <comments>https://tweakers.net/nieuws/213066/duitse-studio-achter-shadow-tactics-en-desperados-iii-games-mimimi-stopt.html#reacties</comments>
      <guid isPermaLink="false">https://tweakers.net/nieuws/213066</guid>
      <pubDate>Wed, 30 Aug 2023 10:12:16 GMT</pubDate>
    </item>
    """
)
POST_AUTOHOTKEY = (
    """
    <item>
      <title>AutoHotkey 2.0.6</title>
      <link>https://tweakers.net/downloads/65674/autohotkey-206.html</link>
      <description>Versie 2.0.6 van AutoHotkey is uitgekomen. Dit programma stelt je in staat om vaak gebruikte toetsaanslagen, handelingen en/of knoppencombo's met toetsenbord en muis in een script achter een sneltoets te zetten, zodat de betreffende handeling in één keer wordt uitgevoerd.</description>
      <author>Bart van Klaveren</author>
      <category>Software-update / Software</category>
      <comments>https://tweakers.net/downloads/65674/autohotkey-206.html#reacties</comments>
      <guid isPermaLink="false">https://tweakers.net/downloads/65674</guid>
      <pubDate>Wed, 30 Aug 2023 10:02:26 GMT</pubDate>
    </item>
    """
)
POST_GOOGLE = (
    """
    <item>
      <title>Google maakt AI-assistent Duet beschikbaar voor Workspace-gebruikers</title>
      <link>https://tweakers.net/nieuws/213050/google-maakt-ai-assistent-duet-beschikbaar-voor-workspace-gebruikers.html</link>
      <description>Google maakt de AI-assistent Duet AI beschikbaar voor alle Workspace-gebruikers. De functie was er al een tijdje in bèta. Duet kan onder andere notities maken van vergaderingen, documenten samenvatten en applicatie-specifieke taken uitvoeren op basis van kunstmatige intelligentie.</description>
      <author>Tijs Hofmans</author>
      <category>Nieuws / Computers / Officesoftware en suites</category>
      <comments>https://tweakers.net/nieuws/213050/google-maakt-ai-assistent-duet-beschikbaar-voor-workspace-gebruikers.html#reacties</comments>
      <guid isPermaLink="false">https://tweakers.net/nieuws/213050</guid>
      <pubDate>Tue, 29 Aug 2023 16:23:24 GMT</pubDate>
    </item>
    """
)
POST_DOLBY = (
    """
    <item>
      <title>Dolby Atmos FlexConnect combineert tv-luidsprekers met losse exemplaren</title>
      <link>https://tweakers.net/nieuws/213014/dolby-atmos-flexconnect-combineert-tv-luidsprekers-met-losse-exemplaren.html</link>
      <description>Dolby introduceert zijn Atmos FlexConnect-techniek. Hiermee kunnen de ingebouwde luidsprekers van een tv worden gecombineerd met losse, draadloze luidsprekers voor Atmos-surroundsound. De techniek wordt in eerste instantie toegevoegd aan de 2024-tv's van TCL.</description>
      <author>Daan van Monsjou</author>
      <category>Nieuws / Beeld en geluid / Audio</category>
      <comments>https://tweakers.net/nieuws/213014/dolby-atmos-flexconnect-combineert-tv-luidsprekers-met-losse-exemplaren.html#reacties</comments>
      <guid isPermaLink="false">https://tweakers.net/nieuws/213014</guid>
      <pubDate>Mon, 28 Aug 2023 14:28:02 GMT</pubDate>
    </item>
    """
)
# fmt: on


@pytest.fixture()
def _one_kb_is_enough(container: Container) -> Iterator[None]:
    app_settings = container.settings.app()
    new_app_settings = ApplicationSettings(
        feed_max_size_b=1024,
        **app_settings.model_dump(exclude={"feed_max_size_b"}),
    )
    with container.settings.app.override(new_app_settings):
        yield


@pytest.fixture()
def uc(container: Container, postgres_database: AsyncEngine) -> UpdateFeedContentUseCase:
    return container.use_cases.update_feed_content()


@pytest.fixture()
def rss_feed_servers(
    create_httpservers: Callable[[int], AbstractContextManager[list[ContentServer]]],
) -> Iterator[list[ContentServer]]:
    with create_httpservers(5) as servers:
        yield servers


@pytest.fixture()
def rss_feed_server(
    create_httpservers: Callable[[int], AbstractContextManager[list[ContentServer]]],
) -> Iterator[list[ContentServer]]:
    with create_httpservers(1) as servers:
        yield servers[0]


@pytest_asyncio.fixture()
async def feed(
    rss_feed_server: ContentServer,
    insert_feeds: InsertFeedsFixtureT,
) -> Feed:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(
            url=rss_feed_server.url,
            title="Feed",
            published_at=None,
        ),
    )
    yield feed


@pytest_asyncio.fixture()
async def feed_pending_job(
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    feed: Feed,
) -> FeedRefreshJob:
    job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJob(
            feed_id=feed.id,
            state=FeedRefreshJobState.pending,
            execute_after=now_aware() - timedelta(seconds=1),
            retries=0,
        ),
    )
    return job


@pytest.fixture()
def wrap_rss_content() -> Callable[[str, str], str]:
    def wrapper(channel_title: str, content: str) -> str:
        # fmt: off
        return (
            f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
              <channel>
                <copyright>Copyright 1998 - 2023 DPG Media B.V.</copyright>
                <pubDate>Wed, 30 Aug 2023 13:17:03 GMT</pubDate>
                <lastBuildDate>Wed, 30 Aug 2023 13:17:03 GMT</lastBuildDate>
                <language>nl-nl</language>
                <link>https://tweakers.net/</link>
                <title>{channel_title}</title>
                {content}
               </channel>
            </rss>
            """
        )
        # fmt: on

    return wrapper


async def test_update_feed_content_happy_path(
    db: AsyncEngine,
    uc: UpdateFeedContentUseCase,
    wrap_rss_content: Callable,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    fetchmany: FetchManyFixtureT,
    rss_feed_servers: list[ContentServer],
) -> None:
    now = now_aware()
    some_time_ago = now - timedelta(minutes=5)

    rss1, rss2, rss3, rss4, rss5 = rss_feed_servers

    feed1, feed2, feed3, feed4, feed5 = await insert_feeds(
        NewFeedFactory.build(
            url=rss1.url,
            title="Feed 1",
            published_at=None,
        ),
        NewFeedFactory.build(
            url=rss2.url,
            title="Feed 2",
            published_at=datetime(2023, 8, 29, 10, 0, 0, tzinfo=UTC),
        ),
        NewFeedFactory.build(
            url=rss3.url,
            title="Tweakers [old]",
            published_at=datetime(2023, 8, 29, 12, 29, 25, tzinfo=UTC),
        ),
        NewFeedFactory.build(
            url=rss4.url,
            title="Feed 4",
            published_at=None,
        ),
        NewFeedFactory.build(
            url=rss5.url,
            title="Feed 5",
            published_at=None,
        ),
    )

    job1, job2, job3, job4, job5 = await insert_refresh_jobs(
        NewFeedRefreshJob(
            feed_id=feed1.id,
            state=FeedRefreshJobState.pending,
            execute_after=some_time_ago,
            retries=3,
        ),
        NewFeedRefreshJob(
            feed_id=feed2.id,
            state=FeedRefreshJobState.pending,
            execute_after=some_time_ago,
            retries=1,
        ),
        NewFeedRefreshJob(
            feed_id=feed3.id,
            state=FeedRefreshJobState.pending,
            execute_after=some_time_ago,
            retries=2,
        ),
        NewFeedRefreshJob(
            feed_id=feed4.id,
            state=FeedRefreshJobState.pending,
            execute_after=some_time_ago,
            retries=1,
        ),
        NewFeedRefreshJob(
            feed_id=feed5.id,
            state=FeedRefreshJobState.pending,
            execute_after=now,
            retries=3,
        ),
    )

    # change state_changed_at to make sure job3, job4, job5 are executed first
    async with db.begin() as conn:
        await conn.execute(
            sa.update(mdl.FeedRefreshJob)
            .where(mdl.FeedRefreshJob.c.id.in_([job3.id, job4.id, job5.id]))
            .values(state_changed_at=now - timedelta(minutes=10))
        )

    feed3_garmin_post, *_ = await insert_feed_posts(
        NewFeedPostFactory.build(
            feed_id=feed3.id,
            title="Garmin brengt Venu 3-smartwatches met iets langere accuduur uit voor 500 euro",
            url=(
                "https://tweakers.net/nieuws/213068/garmin-brengt-venu-"
                "3-smartwatches-met-iets-langere-accuduur-uit-voor-500-euro.html"
            ),
            guid="https://tweakers.net/nieuws/213068",
        ),
    )

    rss1.serve_content(
        wrap_rss_content(
            channel_title="Tweakers Alternative",
            content=f"{POST_GARMIN}{POST_AUTOHOTKEY}{POST_MIMIMI}",
        ),
        200,
        headers={"Content-Type": "text/xml; charset=UTF-8"},
    )

    rss2.serve_content(
        wrap_rss_content(
            channel_title="Geeks for geeks",
            content=f"{POST_GOOGLE}{POST_DOLBY}",
        )
    )

    rss3.serve_content(
        wrap_rss_content(
            channel_title="Tweakers",
            content=POST_GARMIN,
        ),
        200,
        headers={"Content-Type": "text/xml; charset=UTF-8"},
    )

    rss4.serve_content("server error", 502)
    rss5.serve_content("Welcome to NGINX!", 200)

    uc_input = UpdateFeedContentInput(batch_size=2)
    await uc.execute(uc_input)

    # job3 is executed first, because it has the oldest state_changed_at
    job3_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == job3.id)
    )
    assert job3_row["state"] == FeedRefreshJobState.complete.value
    assert job3_row["retries"] == 0

    feed3_new_posts = await fetchmany(
        sa.select(mdl.FeedPost).where(
            sa.and_(
                mdl.FeedPost.c.feed_id == feed3.id,
                mdl.FeedPost.c.id != feed3_garmin_post.id,
            )
        )
    )
    assert len(feed3_new_posts) == 0

    feed3_row = await fetchone(sa.select(mdl.Feed).where(mdl.Feed.c.id == feed3.id))
    assert feed3_row["title"] == "Tweakers"
    assert feed3_row["published_at"] == datetime(2023, 8, 30, 12, 29, 25, tzinfo=UTC)

    # job4 was executed too, because it also has the oldest state_changed_at
    job4_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == job4.id)
    )
    assert job4_row["state"] == FeedRefreshJobState.pending.value
    assert job4_row["retries"] == 2
    assert job4_row["execute_after"] > now_aware()

    # another run
    await uc.execute(uc_input)

    # job5 is executed next, also because of state_changed_at
    job5_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == job5.id)
    )
    # because job5 exceeded its retries, it is marked as failed
    assert job5_row["state"] == FeedRefreshJobState.failed.value
    assert job5_row["retries"] == 3
    assert job5_row["execute_after"] == job5.execute_after

    # job1 was executed along with job5, because despite having a newer state_changed_at,
    # it has the lowest id
    job1_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == job1.id)
    )
    assert job1_row["state"] == FeedRefreshJobState.complete.value
    assert job1_row["retries"] == 0
    assert job1_row["execute_after"] == job1.execute_after

    feed1_row = await fetchone(sa.select(mdl.Feed).where(mdl.Feed.c.id == feed1.id))
    assert feed1_row["title"] == "Tweakers Alternative"
    assert feed1_row["published_at"] == datetime(2023, 8, 30, 12, 29, 25, tzinfo=UTC)

    feed1_posts = await fetchmany(
        sa.select(mdl.FeedPost)
        .where(mdl.FeedPost.c.feed_id == feed1.id)
        .order_by(mdl.FeedPost.c.id)
    )
    # different feeds are allowed to have posts with identical guid
    assert len(feed1_posts) == 3
    feed1_post1, feed1_post2, feed1_post3 = feed1_posts

    assert feed1_post1["title"] == "AutoHotkey 2.0.6"
    assert feed1_post1["guid"] == "https://tweakers.net/downloads/65674"
    assert feed1_post1["published_at"] == datetime(2023, 8, 30, 10, 2, 26, tzinfo=UTC)

    assert feed1_post2["title"] == (
        "Duitse studio achter Shadow Tactics- en Desperados III-games Mimimi stopt"
    )
    assert feed1_post2["guid"] == "https://tweakers.net/nieuws/213066"
    assert feed1_post2["published_at"] == datetime(2023, 8, 30, 10, 12, 16, tzinfo=UTC)

    assert feed1_post3["title"] == (
        "Garmin brengt Venu 3-smartwatches met iets langere accuduur uit voor 500 euro"
    )
    assert feed1_post3["guid"] == "https://tweakers.net/nieuws/213068"
    assert feed1_post3["published_at"] == datetime(2023, 8, 30, 12, 29, 25, tzinfo=UTC)

    # another run
    await uc.execute(uc_input)

    # job2 was executed last, because it has the newest state_changed_at
    # and the highest id among the jobs with the same state_changed_at
    job2_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == job2.id)
    )
    assert job2_row["state"] == FeedRefreshJobState.complete.value
    assert job2_row["retries"] == 0
    assert job2_row["execute_after"] == job2.execute_after

    feed2_row = await fetchone(sa.select(mdl.Feed).where(mdl.Feed.c.id == feed2.id))
    assert feed2_row["title"] == "Geeks for geeks"
    assert feed2_row["published_at"] == datetime(2023, 8, 29, 16, 23, 24, tzinfo=UTC)

    feed2_posts = await fetchmany(sa.select(mdl.FeedPost).where(mdl.FeedPost.c.feed_id == feed2.id))
    # the dolby post was skipped because its publication date is older than the feed's
    assert len(feed2_posts) == 1

    feed2_post = feed2_posts[0]
    assert feed2_post["title"] == (
        "Google maakt AI-assistent Duet beschikbaar voor Workspace-gebruikers"
    )
    assert feed2_post["guid"] == "https://tweakers.net/nieuws/213050"
    assert feed2_post["published_at"] == datetime(2023, 8, 29, 16, 23, 24, tzinfo=UTC)


@pytest.mark.usefixtures("_one_kb_is_enough")
async def test_update_feed_content_limit_response_size(
    uc: UpdateFeedContentUseCase,
    wrap_rss_content: Callable,
    rss_feed_server: ContentServer,
    feed_pending_job: FeedRefreshJob,
    fetchone: FetchOneFixtureT,
) -> None:
    rss_feed_server.serve_content(
        wrap_rss_content(
            channel_title="Feed",
            content=f"{POST_GARMIN}{POST_MIMIMI}{POST_AUTOHOTKEY}",
        ),
        200,
        headers={"Content-Type": "text/xml; charset=UTF-8"},
    )

    uc_input = UpdateFeedContentInput(batch_size=50)
    await uc.execute(uc_input)

    db_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == feed_pending_job.id)
    )
    assert db_row["state"] == FeedRefreshJobState.pending.value
    assert db_row["retries"] == 1
    assert db_row["execute_after"] > now_aware()


@pytest.mark.parametrize(
    "response_body, status_code, headers",
    [
        (None, None, None),
        ("Server error", 500, None),
        ("Temporary unavailable", 503, None),
        ("Not Found", 404, None),
        ("Welcome to NGINX!", 200, None),
        # # valid xml, but no rss
        (
            """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        </rss>""",
            200,
            {"Content-Type": "text/xml; charset=UTF-8"},
        ),
        # valid rss, but no channel title
        (
            """<?xml version="1.0" encoding="UTF-8"?>
        <rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
            <channel>
                <link>https://www.makeuseof.com</link>
            </channel>
        </rss>""",
            200,
            {"Content-Type": "text/xml; charset=UTF-8"},
        ),
        # channel has empty title
        (
            """<?xml version="1.0" encoding="UTF-8"?>
        <rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
            <channel>
                <title></title>
                <link>https://www.makeuseof.com</link>
            </channel>
        </rss>""",
            200,
            {"Content-Type": "text/xml; charset=UTF-8"},
        ),
    ],
    ids=[
        "no response",
        "server error",
        "temporary unavailable",
        "not found",
        "nginx welcome page",
        "valid xml, but no rss",
        "valid rss, but no channel title",
        "channel empty tittle",
    ],
)
async def test_update_feed_content_invalid_response(
    uc: UpdateFeedContentUseCase,
    fetchone: FetchOneFixtureT,
    rss_feed_server: ContentServer,
    feed_pending_job: FeedRefreshJob,
    response_body: str,
    status_code: int,
    headers: dict[str, str] | None,
) -> None:
    # dont serve content, emulate no response
    if status_code is not None:
        rss_feed_server.serve_content(response_body, status_code, headers)

    uc_input = UpdateFeedContentInput(batch_size=50)
    await uc.execute(uc_input)

    db_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == feed_pending_job.id)
    )
    assert db_row["state"] == FeedRefreshJobState.pending.value
    assert db_row["retries"] == 1
    assert db_row["execute_after"] > now_aware()


async def test_update_feed_content_remote_url_forbidden(
    uc: UpdateFeedContentUseCase,
    wrap_rss_content: Callable,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    fetchmany: FetchManyFixtureT,
    rss_feed_servers: list[ContentServer],
) -> None:
    # feedparser is known to accept remote url along with raw xml contents
    # we should not allow this
    rss, another_rss, *_ = rss_feed_servers

    rss.serve_content(another_rss.url, 200)
    another_rss.serve_content(
        wrap_rss_content(channel_title="Feed", content=POST_GARMIN),
        200,
        headers={"Content-Type": "text/xml; charset=UTF-8"},
    )

    feed, *_ = await insert_feeds(
        NewFeedFactory.build(
            url=rss.url,
            title="Feed 1",
        ),
    )
    job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJob(
            feed_id=feed.id,
            state=FeedRefreshJobState.pending,
            execute_after=now_aware() - timedelta(minutes=10),
            retries=0,
        ),
    )

    uc_input = UpdateFeedContentInput(batch_size=50)
    await uc.execute(uc_input)

    db_row = await fetchone(sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == job.id))
    assert db_row["state"] == FeedRefreshJobState.pending.value
    assert db_row["retries"] == 1
    assert db_row["execute_after"] > now_aware()

    new_posts = await fetchmany(sa.select(mdl.FeedPost).where(mdl.FeedPost.c.feed_id == feed.id))
    assert len(new_posts) == 0


async def test_update_feed_content_too_early_for_execution(
    uc: UpdateFeedContentUseCase,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    rss_feed_server: ContentServer,
    feed: Feed,
) -> None:
    in_future = now_aware() + timedelta(minutes=10)
    future_job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJob(
            feed_id=feed.id,
            state=FeedRefreshJobState.pending,
            execute_after=in_future,
            retries=0,
        ),
    )

    uc_input = UpdateFeedContentInput(batch_size=50)
    await uc.execute(uc_input)

    db_row = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == future_job.id)
    )
    # no change
    assert db_row["state"] == FeedRefreshJobState.pending.value
    assert db_row["retries"] == 0
    assert db_row["execute_after"] == in_future


@pytest.mark.parametrize(
    "items_content, new_posts",
    [
        # fmt: off
        # no entries, no new posts
        ("", []),
        # base case, all posts are valid
        (
            f"""
            {POST_GARMIN}
            {POST_MIMIMI}
            """,
            [
                {
                    "title": ("Duitse studio achter Shadow Tactics- "
                              "en Desperados III-games Mimimi stopt"),
                    "summary": ("Mimimi Games houdt op te bestaan. Het bedrijf bracht sinds "
                                "2011 meerdere stealth-strategiegames uit, maar de twee oprichters "
                                "en directeuren zeggen niet genoeg energie meer "
                                "te hebben om verder te gaan."),
                    "url": "https://tweakers.net/nieuws/213066/duitse-studio-achter-shadow-tactics-en-desperados-iii-games-mimimi-stopt.html",
                    "guid": "https://tweakers.net/nieuws/213066",
                    "published_at": datetime(2023, 8, 30, 10, 12, 16, tzinfo=UTC),
                },
                {
                    "title": "Garmin brengt Venu 3-smartwatches met iets langere accuduur uit voor 500 euro",
                    "summary": ("Garmin heeft de Venu 3-smartwatchserie uitgebracht. "
                                "De serie bestaat uit de 45mm-Venu 3 en de 41mm-Venu 3S."),
                    "url": "https://tweakers.net/nieuws/213068/garmin-brengt-venu-3-smartwatches-met-iets-langere-accuduur-uit-voor-500-euro.html",
                    "guid": "https://tweakers.net/nieuws/213068",
                    "published_at": datetime(2023, 8, 30, 12, 29, 25, tzinfo=UTC),
                },
            ],
        ),
        # some posts are valid, some not
        (
           f"""
            {POST_GARMIN}
            <!-- no summary, no guid, but still valid -->
            <item>
              <title>Duitse studio achter Shadow Tactics- en Desperados III-games Mimimi stopt</title>
              <link>https://tweakers.net/nieuws/213066/duitse-studio-achter-shadow-tactics-en-desperados-iii-games-mimimi-stopt.html</link>
              <pubDate>Wed, 30 Aug 2023 10:12:16 GMT</pubDate>
            </item>
            <!-- no title, skipped -->
            <item>
              <link>https://tweakers.net/nieuws/213062/nederlandse-provider-ben-kondigt-5g-ondersteuning-aan-voor-1-euro-per-maand.html</link>
              <description>Ben-klanten kunnen sinds deze week 5G gebruiken voor 1 euro per maand extra. Dit netwerk biedt dezelfde snelheden aan als het onlangs geüpgradede 4G Extra Snel-abonnement en vervangt dit abonnement grotendeels. Ben gebruikt het netwerk van T-Mobile.</description>
              <author>Hayte Hugo</author>
              <category>Nieuws / Tablets en telefoons / Mobiele netwerken</category>
              <guid isPermaLink="false">https://tweakers.net/nieuws/213062</guid>
              <pubDate>Wed, 30 Aug 2023 08:37:10 GMT</pubDate>
            </item>
            <!-- no guid, link is used instead -->
            <item>
              <title>WhatsApp brengt macOS-app uit, ondersteunt groepsvideogesprekken</title>
              <link>https://tweakers.net/nieuws/213060/whatsapp-brengt-macos-app-uit-ondersteunt-groepsvideogesprekken.html</link>
              <description>WhatsApp heeft zijn vernieuwde macOS-app uitgebracht. De nieuwere versie moet onder meer sneller werken en extra functies bieden, zoals de mogelijkheid om aan groepsvideogesprekken deel te nemen.</description>
              <author>Hayte Hugo</author>
              <category>Nieuws / Computers / Software</category>
              <comments>https://tweakers.net/nieuws/213060/whatsapp-brengt-macos-app-uit-ondersteunt-groepsvideogesprekken.html#reacties</comments>
              <pubDate>Wed, 30 Aug 2023 07:16:59 GMT</pubDate>
            </item>
            <!-- bad url -->
            <item>
              <title>Mozilla Firefox 117.0</title>
              <link>htt://tweakers.net/downloads/65656/mozilla-firefox-1170.html</link>
              <description>Mozilla heeft versie 117 van zijn webbrowser Firefox uitgebracht.</description>
              <author>Bart van Klaveren</author>
              <category>Software-update / Software</category>
              <comments>https://tweakers.net/downloads/65656/mozilla-firefox-1170.html#reacties</comments>
              <guid isPermaLink="false">https://tweakers.net/downloads/65656</guid>
              <pubDate>Tue, 29 Aug 2023 14:33:01 GMT</pubDate>
            </item>
            <!-- bad pubDate, skipped -->
            <item>
                <title>Apple brengt iOS 15, iPadOS 15, watchOS 8 en tvOS 15 op 20 september uit</title>
                <link>https://tweakers.net/nieuws/213058/apple-brengt-ios-15-ipados-15-watchos-8-en-tvos-15-op-20-september-uit.html</link>
                <description>Apple brengt iOS 15, iPadOS 15, watchOS 8 en tvOS 15 op 20 september uit. Dat heeft het bedrijf bekendgemaakt tijdens zijn iPhone 13-evenement.</description>
                <author>Arnoud Wokke</author>
                <category>Nieuws / Tablets en telefoons / Besturingssystemen</category>
                <comments>https://tweakers.net/nieuws/213058/apple-brengt-ios-15-ipados-15-watchos-8-en-tvos-15-op-20-september-uit.html#reacties</comments>
                <guid isPermaLink="false">https://tweakers.net/nieuws/213058</guid>
                <pubDate>Aug 2023 06:59:00</pubDate>
            </item>
            {POST_AUTOHOTKEY}
            <!-- no title, no summary, no guid, skipped -->
            <item>
                <link>https://tweakers.net/nieuws/213062/nederlandse-provider-ben-kondigt-5g-ondersteuning-aan-voor-1-euro-per-maand.html</link>
                <pubDate>Wed, 30 Aug 2023 08:37:10 GMT</pubDate>
            </item>
            """,
            [
                {
                    "title": "WhatsApp brengt macOS-app uit, ondersteunt groepsvideogesprekken",
                    "summary": (
                        "WhatsApp heeft zijn vernieuwde macOS-app uitgebracht. De nieuwere versie "
                        "moet onder meer sneller werken en extra functies bieden, zoals de "
                        "mogelijkheid om aan groepsvideogesprekken deel te nemen."
                    ),
                    "url": "https://tweakers.net/nieuws/213060/whatsapp-brengt-macos-app-uit-ondersteunt-groepsvideogesprekken.html",
                    "guid": "https://tweakers.net/nieuws/213060/whatsapp-brengt-macos-app-uit-ondersteunt-groepsvideogesprekken.html",
                    "published_at": datetime(2023, 8, 30, 7, 16, 59, tzinfo=UTC),
                },
                {
                    "title": "AutoHotkey 2.0.6",
                    "summary": (
                        "Versie 2.0.6 van AutoHotkey is uitgekomen. Dit programma stelt je in staat om "
                        "vaak gebruikte toetsaanslagen, handelingen en/of knoppencombo's met toetsenbord "
                        "en muis in een script achter een sneltoets te zetten, zodat de betreffende "
                        "handeling in één keer wordt uitgevoerd."
                    ),
                    "url": "https://tweakers.net/downloads/65674/autohotkey-206.html",
                    "guid": "https://tweakers.net/downloads/65674",
                    "published_at": datetime(2023, 8, 30, 10, 2, 26, tzinfo=UTC),
                },
                {
                    "title": (
                        "Duitse studio achter Shadow Tactics- en Desperados III-games Mimimi stopt"
                    ),
                    "summary": None,
                    "url": "https://tweakers.net/nieuws/213066/duitse-studio-achter-shadow-tactics-en-desperados-iii-games-mimimi-stopt.html",
                    "guid":  "https://tweakers.net/nieuws/213066/duitse-studio-achter-shadow-tactics-en-desperados-iii-games-mimimi-stopt.html",
                    "published_at": datetime(2023, 8, 30, 10, 12, 16, tzinfo=UTC),
                },
                {
                    "title": "Garmin brengt Venu 3-smartwatches met iets langere accuduur uit voor 500 euro",
                    "summary": (
                        "Garmin heeft de Venu 3-smartwatchserie uitgebracht. "
                        "De serie bestaat uit de 45mm-Venu 3 en de 41mm-Venu 3S."
                    ),
                    "url": "https://tweakers.net/nieuws/213068/garmin-brengt-venu-3-smartwatches-met-iets-langere-accuduur-uit-voor-500-euro.html",
                    "guid": "https://tweakers.net/nieuws/213068",
                    "published_at": datetime(2023, 8, 30, 12, 29, 25, tzinfo=UTC),
                },
            ],
        ),
        # fmt: on
    ],
    ids=[
        "no entries, no new posts",
        "base case, all posts are valid",
        "some posts are valid, some not",
    ],
)
async def test_update_feed_content_posts_are_parsed_by_one(
    uc: UpdateFeedContentUseCase,
    rss_feed_server: ContentServer,
    feed: Feed,
    feed_pending_job: FeedRefreshJob,
    fetchmany: FetchManyFixtureT,
    wrap_rss_content: Callable,
    items_content: str,
    new_posts: list[dict[str, Any]],
) -> None:
    rss_feed_server.serve_content(
        wrap_rss_content(
            channel_title="Tweakers Mixed RSS Feed",
            content=items_content,
        ),
        200,
        headers={"Content-Type": "text/xml; charset=UTF-8"},
    )

    uc_input = UpdateFeedContentInput(batch_size=50)
    await uc.execute(uc_input)

    db_rows = await fetchmany(
        sa.select(mdl.FeedPost)
        .where(mdl.FeedPost.c.feed_id == feed.id)
        .order_by(mdl.FeedPost.c.id),
    )
    assert len(db_rows) == len(new_posts)

    for db_row, new_post in zip(db_rows, new_posts, strict=True):
        assert db_row["feed_id"] == feed.id
        assert db_row["title"] == new_post["title"]
        assert db_row["summary"] == new_post["summary"]
        assert db_row["url"] == new_post["url"]
        assert db_row["guid"] == new_post["guid"]
        assert db_row["published_at"] == new_post["published_at"]


async def test_update_feed_content_outdated_posts_ignored(
    uc: UpdateFeedContentUseCase,
    wrap_rss_content: Callable,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    rss_feed_server: ContentServer,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(
            url=rss_feed_server.url,
            title="Feed",
            published_at=datetime(2023, 8, 30, 10, 10, 0, tzinfo=UTC),
        ),
    )
    await insert_refresh_jobs(
        NewFeedRefreshJob(
            feed_id=feed.id,
            state=FeedRefreshJobState.pending,
            execute_after=now_aware() - timedelta(seconds=1),
            retries=0,
        ),
    )

    hotkey_post, garmin_post = await insert_feed_posts(
        NewFeedPostFactory.build(
            feed_id=feed.id,
            title="AutoHotkey 2.0.6",
            url="https://tweakers.net/downloads/65674/autohotkey-206.html",
            guid="https://tweakers.net/downloads/65674",
        ),
        # garmin post was published and saved earlier, but appeared in the feed again
        NewFeedPostFactory.build(
            feed_id=feed.id,
            title="Garmin brengt Venu 3-smartwatches met iets langere accuduur uit voor 500 euro",
            url="https://tweakers.net/nieuws/213068/garmin-brengt-venu-3-smartwatches-met-iets-langere-accuduur-uit-voor-500-euro.html",
            guid="https://tweakers.net/nieuws/213068",
        ),
    )

    rss_feed_server.serve_content(
        wrap_rss_content(
            channel_title="Tweakers Mixed RSS Feed",
            content=f"{POST_GARMIN}{POST_AUTOHOTKEY}{POST_MIMIMI}{POST_GOOGLE}",
        ),
        200,
        headers={"Content-Type": "text/xml; charset=UTF-8"},
    )

    uc_input = UpdateFeedContentInput(batch_size=50)
    await uc.execute(uc_input)

    db_rows = await fetchmany(
        sa.select(mdl.FeedPost).where(mdl.FeedPost.c.id.notin_([hotkey_post.id, garmin_post.id]))
    )
    # only 1 post was created,
    # because garmin post was already in the db and,
    # the google post pubdate is older than feed's last recoreded pubdate
    assert len(db_rows) == 1

    new_post = db_rows[0]
    assert new_post["feed_id"] == feed.id
    assert new_post["title"] == (
        "Duitse studio achter Shadow Tactics- en Desperados III-games Mimimi stopt"
    )


async def test_update_feed_content_no_feed_no_jobs(uc: UpdateFeedContentUseCase) -> None:
    uc_input = UpdateFeedContentInput(batch_size=50)
    # no exception
    await uc.execute(uc_input)


async def test_update_feed_content_have_feed_no_jobs(
    uc: UpdateFeedContentUseCase,
    feed: Feed,
) -> None:
    uc_input = UpdateFeedContentInput(batch_size=50)
    # no exception
    await uc.execute(uc_input)
