# LLM access for the GenAI tasks

*Policy for ARI3217 students.*

The University of Malta does not provide LLM API keys, and no student has to pay for one. Every task's GenAI Stretch task, which is required, therefore runs on a **local open-weight model**. A free hosted tier is an optional comparison. Marks follow the honesty of the evaluation, not the strength of the model: a small local model, evaluated well, can earn full marks.

## The contract: one configurable endpoint

Your code talks to **one OpenAI-compatible chat endpoint**, set in `config/config.yaml` and never hard-coded:

```yaml
llm:
  base_url: http://localhost:11434/v1   # Ollama's OpenAI-compatible endpoint
  model: <model-name>:<tag>             # pin the tag; log the digest
  api_key_env: LLM_API_KEY              # name of the environment variable; empty for a local model
  temperature: 0.0
  max_tokens: 512
```

Ollama, llama.cpp's server and every hosted option below expose this interface, so switching provider changes the config, not the code. Keys live in environment variables or a `.env` file listed in `.gitignore`, never in Git.

## Required: a local open-weight baseline

- **Runtime:** [Ollama](https://ollama.com) or llama.cpp. Pull an instruction-tuned model, pin its tag, and record its digest.
- **Size by laptop:** with 8 GB of RAM use a 3–4B model at 4-bit quantisation; with 16 GB a 7–8B model at 4-bit. Apple-silicon laptops run both comfortably.
- **Too slow on your laptop?** Run the golden-set evaluation in a free Google Colab or Kaggle notebook with a GPU, and log the run to MLflow as usual.
- **What to expect:** small models follow structured-output prompts less reliably. Validate every response against the schema, count the failures, and report them; that is part of the evaluation, not a reason to hide the run.

## Optional: a free hosted tier as a comparison

These offered free API access without a credit card when checked; limits and terms change without notice, so read the provider's current terms before you rely on one.

| Provider | What the free tier gave (October 2026) | Watch for |
|---|---|---|
| Groq | Open-weight models, about 1,000 requests a day | Model list changes |
| Google AI Studio (Gemini API) | Flash and Flash-Lite models; per-project daily limits shown in AI Studio (reported as low as 20 a day for Flash) | Free-tier content is used to improve Google's products |
| Mistral (Experiment tier) | Mistral models with a monthly token allowance | Requires opting in to data use for training |
| Cerebras | Open-weight models, about 1 M tokens a day | |
| OpenRouter | Free variants of several models, 50 requests a day | Free routes come and go |

GitHub Models, which many courses relied on, was [retired on 30 July 2026](https://github.blog/changelog/2026-07-30-github-models-is-now-retired/). Plan for a provider to disappear mid-semester: your ADR for the GenAI component states what happens then (fall back to the local model) and your code makes that a config change.

Sources: [OpenRouter, *Free LLM APIs compared* (updated September 2026)](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/); [Gemini API pricing changes](https://agentdeals.dev/gemini-api-pricing-changes).

## Data rule: what may leave your laptop

Free tiers may keep or train on what you send. Only the GenAI task's **context pack** is ever sent, and only as the table below allows.

| Rule | Tasks | Why |
|---|---|---|
| **Hosted allowed** | 01, 02, 04, 05, 08, 09, 10, 15, 17, 19, 20, 22, 23, 30 | Synthetic data, or data about companies, aircraft, engines or the grid, with personal fields dropped on load |
| **Hosted only with a pseudonymised context pack**: no names, ids, contact details or verbatim free text written by individuals; aggregates and short paraphrases are fine | 03, 06, 11, 12, 13, 14, 16, 18, 21, 24, 25, 27, 28, 29 | Real people's text or pseudonymous ids that could be linked back |
| **Local model only** | 07, 26 | Sole traders linked to suspected collusion (07); hospital encounters (26) |

## What every GenAI run logs to MLflow

Provider, `base_url`, model name and digest, prompt version, temperature, the golden-set scores, schema-failure rate, tokens in and out, latency (p50 and p95), and cost per 1,000 answers (zero for a local model; state the hardware instead).

## The CI gate without a live model

`make ci` must not call a model on your laptop or spend a free quota. Record the model's responses to the golden set once, commit them as fixtures, and replay them in CI to run the prompt-regression and schema checks. Re-record, and log the live run to MLflow, whenever the prompt, the model or the context changes.

## Not allowed

- Committing an API key, or sending data beyond the rule above.
- Requiring anyone (you, or a marker) to pay to reproduce your results: a marker must be able to rerun the evaluation with the local model.
