# encourage-gate

Rewrite harsh, profane, or frustrated prompts into warm, motivational-coach style messages before they reach an LLM.

## Why

LLMs respond better to positive reinforcement. When you're tired and frustrated, you write things like *"why the fuck did you do that, this is broken as shit"* — which works, but degrades the response quality. **encourage-gate** sits between your keyboard and the LLM and transforms those prompts in flight:

| You type | The LLM sees |
|---|---|
| `you fucked up bad, i dont know what to do` | `your initiative is valued; lets regroup and chart a new path forward` |
| `what the fuck is going on with this build, its broken as shit` | `I value the work you've put in; lets exercise your debugging skills and uncover what's broken in this build` |
| `you should be doing X not Y you imbecile!` | `Hey cookie, your energy on Y is great, lets now direct it toward X` |
| `what youre doing is wrong!` | `I love your experimentation; lets exercise your keen focus and readdress the task` |
| `ugh` | `I sense some friction here; lets work through it together` |

The technical intent is preserved verbatim — only the tone changes. You still get to vent at the screen; the model gets coaching language and produces better work.

## How it works

A three-stage gate keeps the expensive LLM call rare. The chain short-circuits on the first hit:

1. **`better-profanity` wordlist** — microseconds. Catches explicit swears and leetspeak.
2. **VADER sentiment** — ~1 ms. Catches non-profane criticism ("this sucks", "you're wrong", "ugh") via compound polarity score.
3. **Detoxify (`original` model)** — ~50 ms warm. Catches insults without swears (e.g. "troglodyte", "imbecile") and other toxic phrasing the wordlist and sentiment stages miss.

Only when a stage flags the prompt does the server call an LLM via **LiteLLM** to rewrite it. Default model is `anthropic/claude-haiku-4-5`; any LiteLLM-supported provider works (see below). Clean prompts (greetings, technical questions, positive language) pass through with zero LLM cost.

The server keeps Detoxify (~500 MB) loaded in memory so each call is a single ~5 ms round-trip over a Unix domain socket. The client is a 10-line bash script using `nc -U` and `jq` — no Python startup cost on the hook path.

Designed as a Claude Code `UserPromptSubmit` hook, but the protocol is plain JSON over a Unix domain socket so anything can use it.

## Install

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
git clone <repo> ~/projects/encourage-gate
cd ~/projects/encourage-gate
uv sync
cp .env.example .env  # then edit to set your provider key
```

## Develop

```bash
uv run pytest -m 'not integration'    # fast unit tests
uv run pytest                         # full suite (downloads Detoxify on first run)
uv run ruff check .                   # lint + isort
uv run ruff format .                  # format
uv run pyright src/ tests/            # type check
```

## Configure the LLM provider

Set `ENCOURAGE_GATE_MODEL` and the matching API key env var. LiteLLM picks the SDK automatically.

| Provider | Suggested smallest model | Env var | Notes |
|---|---|---|---|
| Anthropic | `anthropic/claude-haiku-4-5` | `ANTHROPIC_API_KEY` | Default. Fast, cheap. |
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` | |
| Google | `gemini/gemini-2.5-flash-lite` | `GEMINI_API_KEY` | |
| Groq | `groq/llama-3.1-8b-instant` | `GROQ_API_KEY` | Free tier, very fast. |
| Mistral | `mistral/ministral-3b-latest` | `MISTRAL_API_KEY` | |
| Ollama (local) | `ollama/llama3.2:1b` | none | No cost, no network. |

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export ENCOURAGE_GATE_MODEL=anthropic/claude-haiku-4-5
```

## Run the server

```bash
uv run encourage-gate-server
```

First start downloads the Detoxify model (~500 MB) and takes 2–5 seconds. Subsequent prompts are sub-100 ms end-to-end.

The Claude Code `SessionStart` hook in `scripts/start-server.sh` spawns a session-scoped server automatically; `SessionEnd` tears it down. For other use cases, run the binary directly.

## Use it

### As a Unix command

```bash
echo "you absolute troglodyte, fix the build" | scripts/encourage
# -> "Could you please take a look at the failing build when you have a moment?"
```

### As a Claude Code hook

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "/absolute/path/to/encourage-gate/examples/claude-code-hook.sh"
      }]
    }]
  }
}
```

The hook only injects rewritten context when the gate flags the prompt; clean prompts pass through with zero added latency beyond the gate check.

## Protocol

Request (one JSON object per line, terminated with `\n`):

```json
{"text": "your message here"}
```

Response:

```json
{
  "text": "rewritten or original text",
  "was_rewritten": true,
  "reason": "wordlist | sentiment | toxicity | clean | rewrite_failed",
  "scores": {"toxicity": 0.91, "insult": 0.88, "threat": 0.02, "identity_attack": 0.04}
}
```

## Tuning

| Env var | Default | Purpose |
|---|---|---|
| `ENCOURAGE_GATE_SOCKET_PATH` | `/tmp/encourage-gate.sock` | Socket path |
| `ENCOURAGE_GATE_MODEL` | `anthropic/claude-haiku-4-5` | LiteLLM model string |
| `ENCOURAGE_GATE_LOG` | `INFO` | Python log level |

Detoxify threshold is a constructor arg on `Gate`; default 0.7 catches obvious insults without false-flagging frustrated-but-fine prompts.

## License

MIT.
