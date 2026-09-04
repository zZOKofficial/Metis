import { API_BASE } from './api';

export interface StreamHandlers<TResponse = any> {
  onDelta?: (text: string) => void;
  onDone?: (response: TResponse) => void;
  onError?: (err: unknown) => void;
}

/**
 * POSTs to a server-sent-events endpoint and dispatches each frame.
 *
 * Frames are `data: {...}\n\n`, with `{"type": "delta", "text": "..."}`
 * while the reply streams in and a final `{"type": "done", "response": {...}}`
 * carrying the full, server-persisted response (agent_actions, synced history).
 */
export async function streamChat<TResponse = any>(
  path: string,
  body: unknown,
  handlers: StreamHandlers<TResponse>
): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok || !res.body) {
      throw new Error(`Stream request failed (${res.status}).`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sepIndex: number;
      while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);
        const dataLine = frame.split('\n').find((line) => line.startsWith('data: '));
        if (!dataLine) continue;

        try {
          const payload = JSON.parse(dataLine.slice(6));
          if (payload.type === 'delta' && typeof payload.text === 'string') {
            handlers.onDelta?.(payload.text);
          } else if (payload.type === 'done') {
            handlers.onDone?.(payload.response);
          }
        } catch {
          // Ignore a malformed frame rather than aborting the whole stream
        }
      }
    }
  } catch (err) {
    handlers.onError?.(err);
  }
}
