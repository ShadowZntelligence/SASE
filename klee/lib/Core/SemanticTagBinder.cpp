#include "SemanticTagBinder.h"

#include <algorithm>
#include <map>
#include <string>
#include <vector>

#include <llvm/IR/BasicBlock.h>
#include <llvm/IR/DebugInfoMetadata.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/Instruction.h>

using namespace klee;

namespace {

static bool locationBefore(
    llvm::Instruction *inst,
    unsigned line,
    unsigned column) {

  auto dl = inst->getDebugLoc();

  if (!dl)
    return false;

  if (dl.getLine() < line)
    return true;

  if (dl.getLine() == line &&
      dl.getCol() < column)
    return true;

  return false;
}

static bool locationAfter(
    llvm::Instruction *inst,
    unsigned line,
    unsigned column) {

  auto dl = inst->getDebugLoc();

  if (!dl)
    return false;

  if (dl.getLine() > line)
    return true;

  if (dl.getLine() == line &&
      dl.getCol() > column)
    return true;

  return false;
}

static bool isEarlier(
    llvm::Instruction *lhs,
    llvm::Instruction *rhs) {

  auto dl1 = lhs->getDebugLoc();
  auto dl2 = rhs->getDebugLoc();

  if (dl1.getLine() < dl2.getLine())
    return true;

  if (dl1.getLine() > dl2.getLine())
    return false;

  return dl1.getCol() < dl2.getCol();
}

static bool isLater(
    llvm::Instruction *lhs,
    llvm::Instruction *rhs) {

  auto dl1 = lhs->getDebugLoc();
  auto dl2 = rhs->getDebugLoc();

  if (dl1.getLine() > dl2.getLine())
    return true;

  if (dl1.getLine() < dl2.getLine())
    return false;

  return dl1.getCol() > dl2.getCol();
}

static llvm::Instruction *
findAnchorBefore(
    llvm::Function *F,
    unsigned line,
    unsigned column) {

  llvm::Instruction *best = nullptr;

  for (auto &BB : *F) {
    for (auto &I : BB) {

      if (!locationBefore(
              &I,
              line,
              column))
        continue;

      if (!best) {
        best = &I;
        continue;
      }

      if (isLater(&I, best))
        best = &I;
    }
  }

  return best;
}

static llvm::Instruction *
findAnchorAfter(
    llvm::Function *F,
    unsigned line,
    unsigned column) {

  llvm::Instruction *best = nullptr;

  for (auto &BB : *F) {
    for (auto &I : BB) {

      if (!locationAfter(
              &I,
              line,
              column))
        continue;

      if (!best) {
        best = &I;
        continue;
      }

      if (isEarlier(&I, best))
        best = &I;
    }
  }

  return best;
}

static std::string mergeTags(
    const std::vector<std::string> &tags) {

  if (tags.empty())
    return "";

  if (tags.size() == 1)
    return tags[0];

  std::string result;

  for (size_t i = 0; i < tags.size(); ++i) {

    if (i)
      result += " | ";

    result += tags[i];
  }

  return result;
}

} // namespace

std::map<
    llvm::BasicBlock *,
    std::string>
SemanticTagBinder::bind(
    llvm::Function *F,
    const std::vector<SemanticTag> &tags) {

  std::map<
      llvm::BasicBlock *,
      std::vector<std::string>>
      bbTags;

  for (const auto &tag : tags) {

    llvm::Instruction *before =
        findAnchorBefore(
            F,
            tag.line,
            tag.column);

    llvm::Instruction *after =
        findAnchorAfter(
            F,
            tag.line,
            tag.column);

    if (!before)
      continue;

    if (!after)
      continue;

    llvm::BasicBlock *targetBB = nullptr;

    if (before->getParent() ==
        after->getParent()) {

      targetBB =
          before->getParent();

    } else {

      targetBB =
          after->getParent();
    }

    bbTags[targetBB]
        .push_back(tag.tag);
  }

  std::map<
      llvm::BasicBlock *,
      std::string>
      result;

  for (auto &entry : bbTags) {

    result[entry.first] =
        mergeTags(entry.second);
  }

  return result;
}