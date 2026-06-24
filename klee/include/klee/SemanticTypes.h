#pragma once

#include <string>
#include <vector>
#include <map>

namespace klee {

struct SemanticTag {
    std::string name;
};

struct SemanticTrace {
    std::vector<std::string> tags;
};

struct GuidanceTrace {
    int rank;
    std::string objective;
    SemanticTrace trace;
};

struct FunctionGuidance {
    std::string functionName;

    std::map<uint64_t,std::string> bbTagMap;

    std::vector<GuidanceTrace> guidanceTraces;
};

}