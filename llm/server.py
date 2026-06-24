import json
import socket
import threading
from pathlib import Path

from tag_creation import create_tags_and_extract
from objective_construction import construct_objectives
from trace_encoding import encode_traces


HOST = "127.0.0.1"
PORT = 12345

CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def recv_json(conn):
    data = b""

    while True:
        chunk = conn.recv(4096)

        if not chunk:
            break

        data += chunk

        try:
            return json.loads(
                data.decode("utf-8")
            )
        except json.JSONDecodeError:
            continue

    raise RuntimeError(
        "Invalid request"
    )


def send_json(conn, obj):
    conn.sendall(
        json.dumps(
            obj,
            ensure_ascii=False
        ).encode("utf-8")
    )


def handle_build_guidance(req):
    """
    Full SASE pipeline.

    Paper:

        Tag Creation
              ↓
        Objective Construction
              ↓
        Trace Encoding
              ↓
        Guidance Cache
    """

    function_name = req["function_name"]

    source_code = req["source_code"]

    call_context = req.get(
        "call_context",
        ""
    )

    manual = req.get(
        "manual",
        ""
    )

    input_spec = req.get(
        "input_spec",
        ""
    )

    use_rag = req.get(
        "use_rag",
        False
    )

    knowledge_dir = req.get(
        "knowledge_dir"
    )

    #
    # Stage 1
    # Semantic Tag Creation
    #

    tag_result = create_tags_and_extract(
        function_name=function_name,
        source_code=source_code,
        call_context=call_context,
    )

    semantic_tags = [
        x["tag"]
        for x in tag_result["tags"]
    ]

    #
    # Stage 2
    # Objective Construction
    #

    objective_result = construct_objectives(
        function_name=function_name,
        source_code=source_code,
        call_context=call_context,
        semantic_tags=semantic_tags,
        manual=manual,
        input_spec=input_spec,
        use_rag=use_rag,
        knowledge_dir=knowledge_dir,
    )

    #
    # Stage 3
    # Trace Encoding
    #

    encoded_result = encode_traces(
        semantic_tags=semantic_tags,
        semantic_profile=objective_result[
            "semantic_profile"
        ],
        objectives=objective_result[
            "objectives"
        ],
    )

    #
    # Cache
    #

    cache_file = (
        CACHE_DIR
        / f"{function_name}.guidance.json"
    )

    with open(
        cache_file,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "function_name":
                    function_name,

                "annotated_source":
                    tag_result[
                        "annotated_code"
                    ],

                "semantic_tags":
                    tag_result[
                        "tags"
                    ],

                "semantic_profile":
                    objective_result[
                        "semantic_profile"
                    ],

                "guidance_traces":
                    encoded_result[
                        "guidance_traces"
                    ],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return {
        "status": "ok",

        "function_name":
            function_name,

        "annotated_source":
            tag_result[
                "annotated_code"
            ],

        "semantic_tags":
            tag_result[
                "tags"
            ],

        "semantic_profile":
            objective_result[
                "semantic_profile"
            ],

        "guidance_traces":
            encoded_result[
                "guidance_traces"
            ],

        "cache_file":
            str(cache_file),
    }


def handle_lookup(req):
    """
    Guidance cache lookup.
    """

    function_name = req[
        "function_name"
    ]

    cache_file = (
        CACHE_DIR
        / f"{function_name}.guidance.json"
    )

    if not cache_file.exists():
        return {
            "status": "miss"
        }

    return {
        "status": "hit",
        "data": json.loads(
            cache_file.read_text(
                encoding="utf-8"
            )
        ),
    }


def dispatch(req):
    op = req["op"]

    if op == "build_guidance":
        return handle_build_guidance(req)

    if op == "lookup_guidance":
        return handle_lookup(req)

    return {
        "status": "error",
        "message": f"Unknown op {op}"
    }


def worker(conn):
    try:

        request = recv_json(conn)

        response = dispatch(
            request
        )

        send_json(
            conn,
            response
        )

    except Exception as e:

        send_json(
            conn,
            {
                "status": "error",
                "message": str(e),
            }
        )

    finally:
        conn.close()


def main():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(
        (HOST, PORT)
    )

    server.listen(32)

    print(
        f"SASE LLM Server listening on {HOST}:{PORT}"
    )

    while True:

        conn, _ = server.accept()

        threading.Thread(
            target=worker,
            args=(conn,),
            daemon=True,
        ).start()


if __name__ == "__main__":
    main()