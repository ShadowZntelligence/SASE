#include "SemanticTagLoader.h"

#include <fstream>
#include <sstream>

#include <llvm/Support/JSON.h>

using namespace klee;

std::vector<SemanticTag>
SemanticTagLoader::loadFromJson(
    const std::string &path) {

  std::vector<SemanticTag> result;

  std::ifstream ifs(path);

  if (!ifs.is_open())
    return result;

  std::stringstream ss;
  ss << ifs.rdbuf();

  auto parsed =
      llvm::json::parse(
          ss.str());

  if (!parsed)
    return result;

  auto *root =
      parsed->getAsObject();

  if (!root)
    return result;

  auto *tags =
      root->getArray("tags");

  if (!tags)
    return result;

  for (auto &item : *tags) {

    auto *obj =
        item.getAsObject();

    if (!obj)
      continue;

    auto tag =
        obj->getString("tag");

    auto line =
        obj->getInteger("line");

    auto column =
        obj->getInteger("column");

    if (!tag || !line)
      continue;

    result.emplace_back(
        tag->str(),
        static_cast<unsigned>(*line),
        column
            ? static_cast<unsigned>(*column)
            : 1);
  }

  return result;
}