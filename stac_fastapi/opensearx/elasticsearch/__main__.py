import argparse
import json
import pathlib

from .app import create_api
from .dialects import dialects

parser = argparse.ArgumentParser()
parser.add_argument(
    "--credentials",
    type=pathlib.Path,
    help="path to the credentials for the elasticsearch database",
    required=True,
)
parser.add_argument(
    "--use-socks-proxy",
    action="store_true",
    help=" ".join(
        [
            "use a socks proxy to connect to the database.",
            "Read from the https_proxy and http_proxy env variables",
        ]
    ),
)
parser.add_argument(
    "--dialect",
    choices=sorted(dialects),
    default="ifremer",
    help="dialect of the elasticsearch database",
)
parser.add_argument(
    "--dialect-config",
    type=pathlib.Path,
    default=None,
    help="path to the configuration of the dialect (a json file)",
)
parser.add_argument(
    "--host", default="127.0.0.1", help="address of the new stac server"
)
parser.add_argument(
    "--port", default=9588, type=int, help="port of the new stac server"
)
parser.add_argument("--log-level", default="info", help="verbosity of the server")

args = parser.parse_args()
if args.credentials.suffix == ".json":
    credentials = json.loads(args.credentials.read_text())
else:
    credentials = credentials.read_text()

if args.dialect_config is None:
    dialect_config = {}
else:
    if not args.dialect_config.exists():
        raise ValueError(f"path does not exist: {args.dialect_config}")
    elif not args.dialect_config.is_file():
        raise ValueError(f"path is not a file: {args.dialect_config}")
    dialect_config = json.loads(args.dialect_config.read_text())

api = create_api(
    credentials=credentials,
    dialect=args.dialect,
    dialect_config=dialect_config,
    host=args.host,
    port=args.port,
    use_socks_proxy=args.use_socks_proxy,
)
# app is used by uvicorn
app = api.app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "stac_fastapi.opensearx.elasticsearch.__main__:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=True,
    )
