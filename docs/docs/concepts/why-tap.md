---
title: Why TAP
sidebar_position: 1
---

# Why TAP

A request to a language-model API today is an all-or-nothing transaction.
The consumer commits to paying for whatever the model produces; the
producer commits to delivering the model's output. Pricing is denominated
per token, but the **unit of commercial agreement is the response**. By the
time a consumer can evaluate output quality, they have already paid for
the tokens that produced it.

This works adequately when output quality is high and predictable. It
works poorly under three conditions that are routine in production agent
workflows:

## 1. Wasted output

A non-trivial fraction of LLM responses are not useful. The model
misunderstands the prompt, drifts off-topic, hallucinates, violates a
structural requirement (returning prose when JSON was requested),
exceeds a length budget, or produces disallowed content.

As an illustrative back-of-the-envelope: a workflow that calls a
frontier model 1,000 times per day at $0.02 average cost per response,
with a 5% reject rate, wastes $10/day per workflow before counting the
cost of any retries; at 10% it is $20. The point isn't the specific
figure — those depend on the model, prompt mix, and reject rate of the
particular workload — but that the consumer cannot detect the failure
until the response has fully arrived and been parsed.

A consumer that could halt generation at the moment the failure becomes
apparent — token 200 of a planned 2,000-token response, when the model
first goes off-topic — would pay 10% of the original cost and return the
rest of the budget to a useful retry.

## 2. Trust asymmetry

Today's pay-after-delivery model assumes the producer trusts the consumer.
This is enforced operationally by API keys, pre-funded accounts, and KYC.
In closed ecosystems where every consumer has an account, this works.

It breaks for **autonomous agents**. An agent making a one-shot request to
a service it has never used before cannot pre-fund. An agent operating
across many small services cannot maintain accounts at each.

## 3. The shape of the problem

Both wasted output and trust asymmetry stem from the same structural
mismatch: payment is committed at one point in time (request submission
or response completion), but value flows continuously across the response.
The commitment is coarser than the flow. To resolve both problems at
once, **the commitment cadence must match the flow cadence** — value and
payment must move together, token by token.

This is what TAP provides. The next page describes how.
