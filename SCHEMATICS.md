# Quar SDK Schematics

These diagrams describe the current 0.0.3 development architecture. Quar Edit is the reference client, but reusable language services belong to the SDK rather than to a mandatory editor.

## 1. Visual Quar Execution and Compilation

```text
+--------------------------+
|     Visual Quar .vq      |
+------------+-------------+
             |
             v
+--------------------------+
|          Lexer           |
+------------+-------------+
             |
             v
+--------------------------+
|          Parser          |
+------------+-------------+
             |
             v
+--------------------------+
|      Semantic Analysis   |
+------------+-------------+
             |
       +-----+-----+
       |           |
       v           v
+-------------+ +------------------+
| QRVM Path   | | C Code Generator |
+------+------+ +--------+---------+
       |                 |
       v                 v
+-------------+ +------------------+
|    QRVM     | |   Generated C    |
+------+------+ +--------+---------+
       |                 |
       v                 v
+-------------+ +------------------+
| Dev / Test  | | Native Compiler  |
+-------------+ +--------+---------+
                         |
                         v
                +------------------+
                | Native Executable|
                +------------------+
```

QRVM is currently the reference path for the newest language features. Native support is tracked separately.

## 2. Canonical Source and Source Projection

```text
+----------------------------+
| Canonical Visual Quar .vq  |
+-------------+--------------+
              |
              v
+----------------------------+
| Source Profile / Normalize |
| UTF-8 + Unicode NFC        |
+-------------+--------------+
              |
              v
+----------------------------+
| Source Projection Service  |
| tooling/source_projection  |
+------+------+--------------+
       |      |       |
       v      v       v
   English  Italiano  Espanol   ... language packs
       |      |       |
       +------+-------+
              |
              v
+----------------------------+
| Non-destructive View       |
| or explicit export result  |
+----------------------------+
```

The projection service does not own the editor and does not silently overwrite the authoritative source.

## 3. Vocabulary Layers

```text
+--------------------------+
| Source Projection        |
+------------+-------------+
             |
   +---------+----------+
   |         |          |
   v         v          v
+------+ +----------+ +----------+
| Core | | Naming   | | Comments |
| words| | Easy     | | Easy     |
+------+ +----------+ +----------+
   |         |          |
   +---------+----------+
             |
             v
+--------------------------+
| EXACT / COMPOSED /       |
| PARTIAL / UNKNOWN        |
+--------------------------+
```

Core language vocabulary is deterministic. Naming Easy and Comments Easy remain experimental and can evolve independently.

## 4. Quar Edit as an SDK Client

```text
+--------------------------------------------------+
|                    Quar Edit                     |
+------------------------+-------------------------+
                         |
       +-----------------+------------------+
       |                 |                  |
       v                 v                  v
+----------------+ +----------------+ +----------------+
| Editor / Tabs  | | Language       | | Preferences /  |
| Files / Folder | | Profiles       | | UI Localization|
+-------+--------+ +-------+--------+ +----------------+
        |                  |
        |                  v
        |          +----------------+
        |          | Build / Compile|
        |          | Run / Interpret|
        |          +-------+--------+
        |                  |
        |                  v
        |          +----------------+
        |          | External       |
        |          | Toolchains     |
        |          +----------------+
        |
        v
+--------------------------+
| Visual Quar Source View  |
| + Syntax Highlighting    |
+------------+-------------+
             |
             v
+--------------------------+
| SDK Source Projection    |
+--------------------------+
```

QEdit keeps the authoritative working source separate from the display projection. Source View is currently limited to Visual Quar `.vq` documents.

## 5. Editor Independence

```text
                 +----------------------+
                 |      Quar SDK        |
                 | Language Services    |
                 +----------+-----------+
                            |
             +--------------+--------------+
             |              |              |
             v              v              v
        +----------+   +----------+   +----------+
        | Quar Edit|   |   Vim    |   |  Geany   |
        | reference|   | possible |   | possible |
        +----------+   +----------+   +----------+
```

The SDK architecture intentionally avoids making Visual Quar dependent on one editor.

## 6. Quar SDK

```text
+--------------------------------------------------+
|                    Quar SDK                      |
+------------------------+-------------------------+
                         |
   +---------------------+---------------------+
   |                     |                     |
   v                     v                     v
+-----------+      +-------------+      +-------------+
| Quar Edit |      | Visual Quar |      | SDK Tooling |
| UI client |      | Language    |      | Projection  |
+-----+-----+      +------+------+      +------+------+ 
      |                   |                    |
      +-------------------+--------------------+
                          |
                          v
                +--------------------+
                | Modular Development|
                | Flow               |
                +--------------------+
```
