# Ingestion Service

Receives events from the browser tracker and writes normalized event streams.

Initial responsibilities:

- expose an event collection endpoint
- validate payloads against `schemas/event.schema.json`
- add server receive timestamps
- redact sensitive fields
- store events by visitor, session, and timestamp

Prototype storage can be JSONL or SQLite before moving to a streaming system.

