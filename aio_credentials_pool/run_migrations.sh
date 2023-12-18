#!/bin/bash

set -euxo pipefail

alembic upgrade head

exec "$@"
