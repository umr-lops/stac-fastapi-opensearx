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
    "--dialect",
    choices=sorted(dialects),
    default="ifremer",
    help="dialect of the elasticsearch database",
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

api = create_api(
    credentials=credentials, dialect=args.dialect, host=args.host, port=args.port
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
