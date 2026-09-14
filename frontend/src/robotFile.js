// Shared helper for reading a robot JSON file picked via an
// <input type="file">. Throws on malformed JSON so callers can show
// a clear parse error before ever touching the network.
export async function readRobotFile(file) {
  const text = await file.text();
  return JSON.parse(text);
}
