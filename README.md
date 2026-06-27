# SASE
SASE is a semantic-assisted symbolic execution framework. Instead of prioritizing execution states solely according to execution-level information, SASE also guides exploration using semantic objectives that represent meaningful behavioral progressions of the target program. SASE is built on top of KLEE.

## Setup
### Build SASE
SASE is built with CMake. The following dependencies are required:
- LLVM 13.0.1 (with clang)
- Z3

A build script is provided at `scripts/build.sh`. Fill in the paths then run the script from the `scripts/` directory:
```bash
cd scripts
./build.sh
```

### Prepare Benchmarks
The `benchmarks/` directory contains zip archives of the benchmark program source code. To prepare the `.bc` files required by SASE:

1. **Unzip** the archive for each benchmark:
```bash
unzip benchmarks/<program>.zip -d benchmarks/<program>
```

2. **Build with `wllvm`** to produce a whole-program LLVM bitcode file. Install `wllvm` first if needed (`pip install wllvm`), then configure and build with `clang` as the compiler:
```bash
cd benchmarks/<program>
CC=wllvm CXX=wllvm++ ./configure   # or cmake -DCMAKE_C_COMPILER=wllvm ...
make
```

3. **Extract the `.bc` file** from the compiled binary:
```bash
extract-bc <binary>
```
This produces `<binary>.bc`, which is the bitcode file to pass to SASE.

## Usage
* Basic usage

```
klee --libc=uclibc --posix-runtime --solver-backend=z3 --search=xxx --search=semantic-trace <.bc>
```

* For additional options, refer to the [KLEE documentation](https://klee-se.org/)

## Main Repository Structure

```
SASE/
├── llm/                                      # LLM-based Semantic Guidance Constructor
│   ├── tag_creation.py                       # Semantic Tag Creation
│   ├── objective_construction.py             # Semantic Objective Construction
│   ├── trace_encoding.py                     # Semantic Trace Encoding
│   └── prompts/
│       ├── tag_creation.txt                  # Prompt for semantic tag creation
│       ├── profile_generation.txt            # Prompt for semantic profile generation
│       ├── domain_knowledge.txt              # Prompt for domain knowledge retrieval
│       ├── behavior_progression.txt          # Prompt for semantically meaningful behavioral progression inference
│       ├── objective_ranking.txt             # Prompt for semantic objective ranking
│       └── trace_encoding.txt                # Prompt for encoding objectives into semantic traces
│
└── klee/                                     # SASE executor
    ├── include/
    │   └── klee/
    │       └── SemanticTypes.h
    └── lib/
        └── Core/
            ├── SemanticGuidance.cpp
            ├── SemanticGuidance.h
            ├── SemanticTrace.cpp
            └── SemanticTrace.h
```

## Benchmarks
Benchmark archives are provided in the `benchmarks/` directory.

|           |           |            |            |           |
|-----------|-----------|------------|------------|-----------|
| bc        | cmark     | gawk       | img2sixel  | jpegoptim |
| MP4Box    | nm        | pdftops    | pdftotext  | sed       |
| speexdec  | tiffcp    | tree       | xmlcatalog | xmllint   |

## License
The KLEE code uses the [KLEE Release License](https://github.com/klee/klee/blob/master/LICENSE.TXT) and the SASE code uses GPL-3.0 license.
