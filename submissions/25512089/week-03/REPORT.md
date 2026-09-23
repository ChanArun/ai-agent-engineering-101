# Week 03 Contract Net Report

## 1. Setup

This experiment implements a Contract Net protocol with one manager and three LLM contractors: calculator, writer, and coder.

Provider: OpenRouter  
Model: nvidia/nemotron-3.5-lightning:free  
Temperature: 0.0  
Tasks: 6 tasks from tasks.json  
Conditions: baseline, homogeneous, and overconfident

For each task, the manager announces the task to all three contractors. Each contractor makes one LLM call and returns a bid. The manager then awards the task to the contractor with the highest valid confidence score.

The task set was committed before the experiment runs.

## 2. Current Results

| Condition | Completed valid runs | Observation |
|---|---:|---|
| Baseline | 3 | Most bids were unparseable after strict JSON parsing |
| Homogeneous | 2 | Both runs produced 18 unparseable bids |
| Overconfident | 0 | Not yet completed |

For the post-fix baseline runs, run 3 recorded 17 unparseable bids, run 10 recorded 17, and run 11 recorded 18. This caused most or all tasks to remain unassigned.

For the homogeneous condition, runs 12 and 13 both recorded 18 unparseable bids out of 18 bid attempts. In both runs, all six tasks were unassigned.

Several earlier baseline runs failed because of authentication and OpenRouter free-tier daily rate limits. These failed runs were preserved in results.csv and logs instead of being deleted.

## 3. Comparison with Smith (1980)

| Aspect | Smith (1980) | This experiment |
|---|---|---|
| Participants | Distributed problem-solving nodes | One manager and three LLM contractors |
| Task announcement | Manager announces work | Manager sends each task to all contractors |
| Bid generation | Nodes evaluate their suitability | LLM contractors estimate whether they should bid |
| Award | Manager selects a contractor | Manager selects the highest valid confidence bid |
| Communication cost | Negotiation messages | Announcements, bids, and awards |
| Failure mode | Coordination or allocation failure | Unparseable bids, no awards, misawards, and API failures |

## 4. Interpretation

The main observation so far is that the selected free OpenRouter model frequently does not follow the requested JSON-only bid format. When the parser was made strict, reasoning text was treated as an unparseable bid instead of being incorrectly accepted.

This behavior strongly affected allocation performance. In the baseline and homogeneous runs, many or all tasks remained unassigned because the manager could not obtain valid bids.

The homogeneous condition has not yet reached three completed runs, and the overconfident condition has not yet been run. Therefore, the comparison across all three conditions is still incomplete. The final interpretation will be updated after the remaining runs are collected.
