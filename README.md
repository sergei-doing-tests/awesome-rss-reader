# Awesome RSS reader
[![License: MIT][license-img]][license]
[![Powered by Python][python-img]][python]
[![Code style: black][black-img]][black]
[![Ruff][ruff-img]][ruff]
[![codecov][codecov-img]][codecov]
[![ci][ci-img]][ci]


## Getting started

Firstly, you'll want to set up your own configuration using a .env file:

```shell
cp .env.example .env
```

In the copied `.env` file, set `AUTH_SECRET_KEY` variable to a random string.
To generate a random string, you can use the following command:
```shell
openssl rand -hex 32
````

The development server is set to work with the default variables out of the box.
However, if needed, you can modify these variables later for a more personalized setup.

Run the development server stack:
```shell
docker-compose up
```
This will start the development server on port 8000.

PostgreSQL instance that comes with the development stack uses the port 5432.
This port is exposed on your machine as well.

Apply the migrations:
```shell
docker-compose exec devserver alembic upgrade head
```


Once done, you'll be able to access the development server at `http://localhost:8000`.

⚠️ Important: The database container running with the dev server is **not persistent**.
When you stop the development stack, the data goes away.

💡 If you want your changes to stick around, consider running a separate PostgreSQL instance.
You can then adjust the `POSTGRES_DB_DSN` variable accordingly.

## Testing

⚠️ For the test suite to work, it needs PostgreSQL. Ensure the development stack is up and running.

Running the test suite is as straightforward as:
```shell
pytest
```

## License

Released under the [MIT License](LICENSE.txt).

[license-img]: https://img.shields.io/badge/License-MIT-yellow.svg
[license]: https://opensource.org/licenses/MIT

[python-img]: https://img.shields.io/badge/python-3.11-blue.svg
[python]: https://www.python.org/downloads/release/python-3110/

[black-img]: https://img.shields.io/badge/code%20style-black-000000.svg
[black]: https://github.com/psf/black

[ruff-img]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff]: https://github.com/astral-sh/ruff

[codecov-img]: https://codecov.io/gh/sergei-doing-tests/awesome-rss-reader/branch/main/graph/badge.svg?token=A0JV2BRV23
[codecov]: https://codecov.io/gh/sergei-doing-tests/awesome-rss-reader

[ci-img]: http://github.com/sergei-doing-tests/awesome-rss-reader/actions/workflows/ci.yml/badge.svg?branch=main
[ci]: http://github.com/sergei-doing-tests/awesome-rss-reader/actions/workflows/ci.yml
