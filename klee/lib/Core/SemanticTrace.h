#pragma once

#include "SemanticTypes.h"

namespace klee {

class TraceUtil {
public:

    static int lcs(
        const SemanticTrace& a,
        const SemanticTrace& b);

    static double similarity(
        const SemanticTrace& stateTrace,
        const std::vector<GuidanceTrace>& guides);
};

}