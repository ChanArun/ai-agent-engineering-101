\# Week 06 Report — A2A Buyer and Seller



Student ID: 25512089



\## 1. Harness, model, and exact commands



I used a custom Python harness backed by GroqCloud.



\- Provider: GroqCloud

\- Model: `openai/gpt-oss-120b`

\- API style: OpenAI-compatible API

\- Base URL: `https://api.groq.com/openai/v1`

\- Temperature: `0`

\- A2A SDK: `a2a-sdk 1.2.2`

\- A2A protocol version: `1.0`

\- Seller transport: JSON-RPC



The harness is implemented in `harness.py`. The seller and buyer both call the harness for negotiation decisions.



The commands recorded in `agent.json` are:



```text

Seller:

python seller.py --port {port}



Buyer:

python buyer.py {url} {item} {budget}

