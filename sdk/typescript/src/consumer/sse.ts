/**
 * Minimal Server-Sent Events parser over a `fetch` Response body.
 *
 * Producers send `data: <payload>\n\n` frames; payload is either an
 * arbitrary JSON object with a `text` field (one token chunk) or the
 * sentinel string `"[DONE]"` marking stream end. We yield each text chunk;
 * the sentinel surfaces as `{ finished: true, text: "" }`.
 */

export interface SseEvent {
  readonly text: string;
  readonly finished: boolean;
}

export async function* iterSse(response: Response): AsyncIterableIterator<SseEvent> {
  if (!response.body) {
    throw new Error("response has no body");
  }

  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .getReader();

  let buffer = "";
  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;

      let sep = buffer.indexOf("\n\n");
      while (sep !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);

        const event = parseFrame(frame);
        if (event) yield event;
        if (event?.finished) return;

        sep = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): SseEvent | null {
  const lines = frame.split("\n");
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;

  const payload = dataLines.join("\n");
  if (payload === "[DONE]") {
    return { text: "", finished: true };
  }
  try {
    const parsed = JSON.parse(payload) as { text?: string };
    return { text: parsed.text ?? "", finished: false };
  } catch {
    // Producer sent a non-JSON data line; treat as plain text.
    return { text: payload, finished: false };
  }
}
