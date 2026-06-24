#pragma once

#include <map>
#include <string>
#include <vector>

namespace llvm {

class Function;
class BasicBlock;

}

namespace klee {

struct SemanticTag {
  std::string tag;
  unsigned line;
  unsigned column;

  SemanticTag(
      const std::string &t,
      unsigned l,
      unsigned c)
      : tag(t),
        line(l),
        column(c) {}
};

class SemanticTagBinder {
public:
  static std::map<
      llvm::BasicBlock *,
      std::string>
  bind(
      llvm::Function *F,
      const std::vector<SemanticTag> &tags);
};

}