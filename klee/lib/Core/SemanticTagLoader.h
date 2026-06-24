#pragma once

#include "klee/Semantics/SemanticTagBinder.h"

#include <string>
#include <vector>

namespace klee {

class SemanticTagLoader {
public:
  static std::vector<SemanticTag>
  loadFromJson(
      const std::string &path);
};

}