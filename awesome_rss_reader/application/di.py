# mypy: disable-error-code="assignment"
from dependency_injector import containers, providers

from awesome_rss_reader.application.settings import ApplicationSettings, AuthSettings
from awesome_rss_reader.core.usecase.authenticate_user import AuthenticateUserUseCase
from awesome_rss_reader.core.usecase.create_feed import CreateFeedUseCase
from awesome_rss_reader.core.usecase.follow_feed import FollowFeedUseCase
from awesome_rss_reader.core.usecase.list_feed_posts import ListFeedPostsUseCase
from awesome_rss_reader.core.usecase.list_user_feeds import ListUserFollowedFeedsUseCase
from awesome_rss_reader.core.usecase.refresh_feed import RefreshFeedUseCase
from awesome_rss_reader.core.usecase.unfollow_feed import UnfollowFeedUseCase
from awesome_rss_reader.data.noop.users import NoopUserRepository
from awesome_rss_reader.data.postgres.database import (
    PostgresSettings,
    init_async_engine,
)
from awesome_rss_reader.data.postgres.repositories.atomic import PostgresAtomicProvider
from awesome_rss_reader.data.postgres.repositories.feed_posts import PostgresFeedPostRepository
from awesome_rss_reader.data.postgres.repositories.feed_refresh_jobs import (
    PostgresFeedRefreshJobRepository,
)
from awesome_rss_reader.data.postgres.repositories.feeds import PostgresFeedRepository
from awesome_rss_reader.data.postgres.repositories.user_feeds import (
    PostgresUserFeedRepository,
)


class Settings(containers.DeclarativeContainer):
    app = providers.Singleton(ApplicationSettings)
    auth = providers.Singleton(AuthSettings)
    postgres = providers.Singleton(PostgresSettings)


class Database(containers.DeclarativeContainer):
    settings: Settings = providers.DependenciesContainer()

    engine = providers.Singleton(init_async_engine, settings=settings.postgres)


class Repositories(containers.DeclarativeContainer):
    database: Database = providers.DependenciesContainer()

    atomic = providers.Singleton(PostgresAtomicProvider, db=database.engine)
    users = providers.Singleton(NoopUserRepository)
    feeds = providers.Singleton(PostgresFeedRepository, db=database.engine)
    user_feeds = providers.Singleton(PostgresUserFeedRepository, db=database.engine)
    feed_refresh_jobs = providers.Singleton(PostgresFeedRefreshJobRepository, db=database.engine)
    feed_posts = providers.Singleton(PostgresFeedPostRepository, db=database.engine)


class UseCases(containers.DeclarativeContainer):
    settings: Settings = providers.Container(Settings)
    repositories: Repositories = providers.DependenciesContainer()

    authenticate_user = providers.Factory(
        AuthenticateUserUseCase,
        user_repository=repositories.users,
        auth_settings=settings.auth,
    )

    create_feed = providers.Factory(
        CreateFeedUseCase,
        feed_repository=repositories.feeds,
        user_feed_repository=repositories.user_feeds,
        job_repository=repositories.feed_refresh_jobs,
        atomic=repositories.atomic,
    )
    list_followed_feeds = providers.Factory(
        ListUserFollowedFeedsUseCase,
        feed_repository=repositories.feeds,
    )
    follow_feed = providers.Factory(
        FollowFeedUseCase,
        feed_repository=repositories.feeds,
        user_feed_repository=repositories.user_feeds,
    )
    unfollow_feed = providers.Factory(
        UnfollowFeedUseCase,
        feed_repository=repositories.feeds,
        user_feed_repository=repositories.user_feeds,
    )
    refresh_feed = providers.Factory(
        RefreshFeedUseCase,
        feed_repository=repositories.feeds,
        job_repository=repositories.feed_refresh_jobs,
        atomic=repositories.atomic,
    )

    list_feed_posts = providers.Factory(
        ListFeedPostsUseCase,
        post_repository=repositories.feed_posts,
    )


class Container(containers.DeclarativeContainer):
    settings: Settings = providers.Container(Settings)
    database: Database = providers.Container(Database, settings=settings)
    repositories: Repositories = providers.Container(Repositories, database=database)
    use_cases: UseCases = providers.Container(
        UseCases, settings=settings, repositories=repositories
    )


def init() -> Container:
    container = Container()
    container.check_dependencies()
    return container
