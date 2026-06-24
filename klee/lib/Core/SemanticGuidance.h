#pragma once

#include <string>

namespace klee {

/// Client used by KLEE to communicate with the
/// Python Semantic Guidance Constructor server.
///
/// Paper mapping:
///
/// KLEE
///   -> SemanticGuidanceClient
///   -> Python Server (port 12345)
///       -> Tag Creation
///       -> Objective Construction
///       -> Trace Encoding
///
class SemanticGuidanceClient {
public:

  /// Generic request interface.
  static std::string request(
      const std::string &jsonRequest);

  /// Lookup semantic guidance cache.
  ///
  /// cache key:
  ///     serialize(STcur) + "::" + function_name
  static std::string lookupGuidance(
      const std::string &cacheKey);

  /// Build semantic guidance.
  ///
  /// Triggered when:
  ///     function entered
  ///     &&
  ///     cache miss
  static std::string buildGuidance(
      const std::string &functionName,
      const std::string &sourceCode,
      const std::string &callContext,
      const std::string &manual,
      const std::string &inputSpec,
      bool useRAG = false,
      const std::string &knowledgeDir = "");

private:

  static std::string sendRequest(
      const std::string &payload);

  static std::string receiveResponse(
      int socketFd);
};

} // namespace klee