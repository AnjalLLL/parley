"""`voxwire` command line: run the server or talk to one."""
import argparse
import json

from voxwire import VoxwireClient, __version__


def main(argv=None):
    parser = argparse.ArgumentParser(prog="voxwire", description="Real-time voice AI calls over WebRTC.")
    parser.add_argument("--version", action="version", version=f"voxwire {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve", help="run the Voxwire signaling/agent server")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    for name in ("health", "session"):
        p = sub.add_parser(name, help=f"{name} against a running server")
        p.add_argument("--url", default="http://localhost:8000")
        p.add_argument("--api-key")
        if name == "session":
            p.add_argument("--prompt", help="system prompt for the AI")

    args = parser.parse_args(argv)
    if args.cmd == "serve":
        import uvicorn  # server extra; imported lazily so the client stays light

        uvicorn.run("voxwire.app:app", host=args.host, port=args.port, reload=args.reload)
        return
    client = VoxwireClient(args.url, api_key=args.api_key)
    out = client.health() if args.cmd == "health" else client.create_session(args.prompt)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
