import hashlib
import json
import os

CACHE_DIR="cache"

def key(function_name, trace):

    raw = function_name + json.dumps(trace)

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()

def load(function_name, trace):

    k = key(
        function_name,
        trace)

    path = os.path.join(
        CACHE_DIR,
        k + ".json"
    )

    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)

    return None

def save(
    function_name,
    trace,
    data):

    os.makedirs(
        CACHE_DIR,
        exist_ok=True)

    k=key(
        function_name,
        trace)

    path=os.path.join(
        CACHE_DIR,
        k+".json")

    with open(path,"w") as f:
        json.dump(data,f,indent=2)