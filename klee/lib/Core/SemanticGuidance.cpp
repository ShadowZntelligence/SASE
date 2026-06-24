#include "klee/Semantics/SemanticGuidanceClient.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <llvm/Support/JSON.h>
#include <llvm/Support/raw_ostream.h>

#include <cstring>
#include <string>
#include <vector>

using namespace klee;

namespace {

constexpr const char *SERVER_IP = "127.0.0.1";
constexpr int SERVER_PORT = 12345;

} // namespace

std::string
SemanticGuidanceClient::receiveResponse(
    int socketFd) {

  std::string response;

  char buffer[8192];

  while (true) {

    ssize_t bytesRead =
        recv(
            socketFd,
            buffer,
            sizeof(buffer),
            0);

    if (bytesRead <= 0)
      break;

    response.append(
        buffer,
        static_cast<size_t>(
            bytesRead));
  }

  return response;
}

std::string
SemanticGuidanceClient::sendRequest(
    const std::string &payload) {

  int sock =
      socket(
          AF_INET,
          SOCK_STREAM,
          0);

  if (sock < 0) {

    llvm::errs()
        << "[SASE] Failed to create socket\n";

    return "";
  }

  sockaddr_in serverAddr;

  std::memset(
      &serverAddr,
      0,
      sizeof(serverAddr));

  serverAddr.sin_family =
      AF_INET;

  serverAddr.sin_port =
      htons(
          SERVER_PORT);

  if (inet_pton(
          AF_INET,
          SERVER_IP,
          &serverAddr.sin_addr)
      <= 0) {

    llvm::errs()
        << "[SASE] Invalid server address\n";

    close(sock);

    return "";
  }

  if (connect(
          sock,
          reinterpret_cast<
              sockaddr *>(
              &serverAddr),
          sizeof(serverAddr))
      < 0) {

    llvm::errs()
        << "[SASE] Failed to connect to Python server "
        << SERVER_IP
        << ":"
        << SERVER_PORT
        << "\n";

    close(sock);

    return "";
  }

  size_t totalSent = 0;

  while (totalSent < payload.size()) {

    ssize_t sent =
        send(
            sock,
            payload.data() + totalSent,
            payload.size() - totalSent,
            0);

    if (sent <= 0) {

      llvm::errs()
          << "[SASE] Failed to send request\n";

      close(sock);

      return "";
    }

    totalSent +=
        static_cast<size_t>(
            sent);
  }

  shutdown(
      sock,
      SHUT_WR);

  std::string response =
      receiveResponse(
          sock);

  close(sock);

  return response;
}

std::string
SemanticGuidanceClient::request(
    const std::string &jsonRequest) {

  return sendRequest(
      jsonRequest);
}

std::string
SemanticGuidanceClient::lookupGuidance(
    const std::string &cacheKey) {

  llvm::json::Object request;

  request["op"] =
      "lookup_guidance";

  request["cache_key"] =
      cacheKey;

  std::string payload;

  llvm::raw_string_ostream os(
      payload);

  os << llvm::json::Value(
      std::move(
          request));

  os.flush();

  return sendRequest(
      payload);
}

std::string
SemanticGuidanceClient::buildGuidance(
    const std::string &functionName,
    const std::string &sourceCode,
    const std::string &callContext,
    const std::string &manual,
    const std::string &inputSpec,
    bool useRAG,
    const std::string &knowledgeDir) {

  llvm::json::Object request;

  request["op"] =
      "build_guidance";

  request["function_name"] =
      functionName;

  request["source_code"] =
      sourceCode;

  request["call_context"] =
      callContext;

  request["manual"] =
      manual;

  request["input_spec"] =
      inputSpec;

  request["use_rag"] =
      useRAG;

  request["knowledge_dir"] =
      knowledgeDir;

  std::string payload;

  llvm::raw_string_ostream os(
      payload);

  os << llvm::json::Value(
      std::move(
          request));

  os.flush();

  return sendRequest(
      payload);
}