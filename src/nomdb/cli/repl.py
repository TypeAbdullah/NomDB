"""
Interactive CLI REPL for NomDB.
Supports colored outputs, history, command formatting, and direct server interaction.
"""

from __future__ import annotations
import argparse
import readline
import shlex
import sys
from typing import Any, List, Optional
from nomdb.client.client import Client
from nomdb.protocol.resp import ErrorResponse, SimpleString
from nomdb.protocol.exceptions import NomDBError

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"


def format_cli_output(val: Any, indent: int = 0) -> str:
    """Format RESP / Python values in the standard redis-cli presentation."""
    pad = "  " * indent

    if val is None:
        return f"{pad}{GRAY}(nil){RESET}"

    if isinstance(val, SimpleString):
        return f"{pad}{val.value}"

    if isinstance(val, bool):
        return f"{pad}(integer) {1 if val else 0}"

    if isinstance(val, int):
        return f"{pad}(integer) {val}"

    if isinstance(val, float):
        formatted = f"{int(val)}" if val.is_integer() else f"{val:g}"
        return f'{pad}"{formatted}"'

    if isinstance(val, bytes):
        try:
            decoded = val.decode("utf-8")
            return f'{pad}"{decoded}"'
        except UnicodeDecodeError:
            return f'{pad}"{repr(val)[2:-1]}"'

    if isinstance(val, str):
        return f'{pad}"{val}"'

    if isinstance(val, (list, tuple)):
        if not val:
            return f"{pad}(empty array)"
        lines = []
        for i, item in enumerate(val, 1):
            formatted_item = format_cli_output(item, indent=0)
            lines.append(f"{pad}{i}) {formatted_item}")
        return "\n".join(lines)

    if isinstance(val, ErrorResponse):
        return f"{RED}(error) {val}{RESET}"

    if isinstance(val, NomDBError):
        return f"{RED}(error) {val}{RESET}"

    if isinstance(val, Exception):
        return f"{RED}(error) {val}{RESET}"

    return f'{pad}"{str(val)}"'


def main() -> None:
    """Run interactive REPL session."""
    parser = argparse.ArgumentParser(description="NomDB Interactive CLI Client")
    parser.add_argument("-h", "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("-p", "--port", type=int, default=6379, help="Server port (default: 6379)")
    parser.add_argument("-a", "--password", default=None, help="Authentication password")
    parser.add_argument("command", nargs="*", help="Command to execute in non-interactive mode")

    args = parser.parse_args()

    client = Client(host=args.host, port=args.port)

    # If non-interactive command supplied
    if args.command:
        try:
            if args.password:
                client.execute_command("AUTH", args.password)
            res = client.execute_command(*args.command)
            print(format_cli_output(res))
        except Exception as e:
            print(f"{RED}(error) {e}{RESET}")
            sys.exit(1)
        finally:
            client.close()
        return

    # Interactive REPL
    print(f"{BOLD}NomDB CLI v1.0.0{RESET}")
    print(f"Connected to {args.host}:{args.port}. Type 'help' or 'quit' to exit.\n")

    if args.password:
        try:
            client.execute_command("AUTH", args.password)
            print(f"{GREEN}Authenticated successfully.{RESET}")
        except Exception as e:
            print(f"{RED}Authentication failed: {e}{RESET}")

    current_db = 0

    while True:
        try:
            prompt_str = f"{args.host}:{args.port}> " if current_db == 0 else f"{args.host}:{args.port}[{current_db}]> "
            user_input = input(prompt_str).strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                break

            tokens = shlex.split(user_input)
            if not tokens:
                continue

            cmd_upper = tokens[0].upper()
            if cmd_upper == "HELP":
                print("Commands: SET, GET, DEL, HSET, HGET, LPUSH, LPOP, SADD, SMEMBERS, ZADD, ZRANGE, INFO, PING, etc.")
                continue

            if cmd_upper == "CLEAR":
                print("\033[H\033[J", end="")
                continue

            try:
                res = client.execute_command(*tokens)
                if cmd_upper == "SELECT" and len(tokens) > 1 and res == "OK":
                    current_db = int(tokens[1])
                print(format_cli_output(res))
            except NomDBError as e:
                print(f"{RED}(error) {e}{RESET}")
            except ConnectionError as ce:
                print(f"{RED}Could not connect to NomDB at {args.host}:{args.port}: {ce}{RESET}")
                break

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")

    client.close()


if __name__ == "__main__":
    main()
