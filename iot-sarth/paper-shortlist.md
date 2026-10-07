# IoT Mini-Project: Paper Shortlist

Selection filter (from the course PDF): paper published 2023 or later, not a survey or review, implementable with
Raspberry Pi / Arduino / ESP32 / open-source tools (simulation allowed), reproducible results, room for a minor extension.
Team-specific filter: protocol-heavy IoT with dynamic behaviour, ML kept light, not a "train a model on a dataset" project.

Ranked (details below):

| # | Paper | Protocol layer | ML used | Code public | Venue / date | Demo style |
|---|-------|----------------|---------|-------------|--------------|------------|
| 1 | DAIS-MQTT | Application (MQTT) | UCB-style decision tree (bandit/MCTS flavour) | No | Sensors 26(11):3564, Jun 2026 | RPi brokers + ESP32 publishers |
| 2 | ACTOR | Network (RPL, IEEE 802.15.4) | UCB / Discounted UCB bandit | Yes (per paper) | Sensors 24(7):2330, Apr 2024 | Contiki-NG + Cooja |
| 3 | LP-MAB | LPWAN (LoRaWAN ADR) | EXP3 + Successive Elimination bandit | Yes (per paper) | Sensors 23(4):2363, Feb 2023 | FLoRa / OMNeT++ (+ optional ESP32 LoRa) |

## 1. DAIS-MQTT
- Title: DAIS-MQTT: A Distributed MQTT Communication Method Based on Intelligent QoS Routing and Hierarchical Collaboration
- DOI: 10.3390/s26113564 (PMC13259186). Published 3 June 2026.
- Idea: static MQTT QoS and a single broker do not adapt to network change. DAIS-MQTT uses a hierarchy of Root, Bridge and Leaf
  broker agents, a topic-to-broker routing table, and an "intelligent QoS routing" (IQR) decision tree that picks the broker and
  QoS level (0/1/2) per topic. State is synchronised with PINGREQ/PINGRESP.
- Reward as reported: R(s,a) = alpha*(K/d) + beta*p - gamma*cq with alpha=0.5, beta=0.3, gamma=0.2.
- Reported results (500 publishers, medium network): about 118 ms vs 250+ ms delay, peak about 9,480 msg/s, delay -29.9%,
  throughput +28.2%, 98.7% delivery under unreliable links. QoS mix shifts with network scale (small nets mostly QoS 0, large nets QoS 1/2).
- Paper's setup: 9 Python broker nodes on one PC, Clumsy for latency/loss (10-50 ms/0-1%, 50-200 ms/1-5%, 200-500 ms/5-15%),
  20 topics, 80% 128 B + 20% 1 KB messages, 50-500 publishers, 600 s runs.
- Our build: Mosquitto bridges or paho-based brokers on RPis/containers, ESP32 publishers, `tc netem` in place of Clumsy.
  Baselines: single Mosquitto, static multi-broker topology (TOD-MQTT optional).
- Extension ideas: Thompson sampling or contextual bandit instead of tree search; broker-failure injection with recovery time;
  ESP32 energy per message by QoS.
- Risks: no public code, no released baselines. Algorithm details beyond the paper must be inferred. Read the full paper first.

## 2. ACTOR
- Title: ACTOR: Adaptive Control of Transmission Power in RPL
- DOI: 10.3390/s24072330 (PMC11014365). Published 6 April 2024.
- Idea: RPL normally transmits at maximum power. ACTOR runs a bandit per neighbour over 8 transmission-power levels (UCB, plus a
  Discounted-UCB variant for non-stationary links). It keeps a per-parent, per-power ETX table, advertises the maximum ETX in DIO,
  has children signal their minimum power demand, and initialises from RSSI.
- Evaluation: Contiki-NG + Cooja Sky motes, 7 scenarios (A-G: 10 to 100 nodes, sparse, dense, 3-cluster, congested at 60 pkt/min,
  5x5 grid, grid with one mobile node), 10 min, at least 5 runs. Metrics: PDR, end-to-end delay, TX power, DIO/DAO overhead,
  parent switches, retransmissions. The paper also ran 40 nRF5340 boards (not required for us).
- Reported: 20-40% PDR gain in dense scenarios, up to 10 dBm power reduction, fewer parent switches, about 50% better delay and energy.
- Baselines: RPL at max power, Transmission Power Probing (TPP), XRPL.
- Code: the paper states "We publish the code as open-source (https://github.com/iliar-rabet/ACTOR, accessed on 3 April 2024)".
  The repo was NOT opened in this session; check it is live and which baselines it contains.
- Extension ideas: Thompson sampling or change-detection (CUSUM/SIC) instead of discounting; evaluate on the mobile-node scenario.
- Risks: needs C in Contiki-NG; simulation-only demo; TPP/XRPL baselines may need implementing.

## 3. LP-MAB
- Title: LP-MAB: Improving the Energy Efficiency of LoRaWAN Using a Reinforcement-Learning-Based Adaptive Configuration Algorithm
- DOI: 10.3390/s23042363 (PMC9964982). Published 20 February 2023. Authors: Teymuri, Serati, Anagnostopoulos, Rasti.
- Idea: the LoRaWAN network server configures each end device's SF {7-12}, TX power {2,5,8,11,14} dBm, carrier frequency
  {868.1, 868.4, 868.7} MHz and coding rate using EXP3 combined with Successive Elimination. ACK reception is the feedback, and
  a multi-reward strategy pays more for low-power successes.
- Evaluation: FLoRa on OMNeT++, 100-700 EDs, 1-10 gateways, 20-byte packets, 125 kHz, 12 simulated days (120 in one scenario),
  20 runs. Metrics: PDR and energy consumption (EC = total energy / PDR). Baselines: ADR-MAX, ADR-AVG, No-ADR, ADR-Lite.
- Code: the paper states "The FLoRa-based framework for simulating LP-MAB is available at https://github.com/reza-serati/LP-MAB".
  The repo was NOT opened in this session; verify it is live.
- Extension ideas: add change detection for non-stationary channels (see the 2025-26 Schwarz-Information-Criterion LoRa bandit
  preprints, arXiv 2512.22089 and 2608.00409); an ESP32 + SX127x ACK-based field test.
- Risks: simulation-only unless hardware is added; LoRaWAN is not on the faculty example list, so the title needs approval;
  OMNeT++/FLoRa version compatibility; long simulations.

## Backups (not in the top 3, with the reason)
- prCoAP, arXiv 2607.18273: CoAP retransmission timeout predicted by linear SVR plus a Random Forest drop classifier. Very on-topic,
  but a preprint submitted to WFIoT 2026 (may not count as "published") and no code.
- NanoEdgeGuard, arXiv 2607.27858 (EuCNC/6G Summit 2026): RPi MQTT gateway + 2 ESP32, closed-loop kernel traffic control. Perfect
  hardware match, but the paper has no ML (you would add it as the extension) and reports early results only.
- Q-RPL, Sensors 2024 (10.3390/s24154818): RPL + Q-learning, strong results, but no code and a custom OMNeT++ RPL, so the heaviest to reproduce.
- Energy-Efficient Dynamic RTO for CoAP, Sensors 2026 (10.3390/s26123960): good CoAP content but no ML.

## Avoid
- Surveys and reviews (the RPL attacks survey on the faculty slide is a review, so it is not allowed).
- Dataset-only intrusion-detection papers (the type that was rejected before).
- Kafka-centric work (DMSCO) and 5G MEC testbeds (HeteroEdge), which need server-class hardware.

## Flags on the faculty PDF
- Khan et al., Sensors vol. 21 no. 21, DOI 10.3390/s21217016 is a 2021 paper (the DOI itself contains "s21"), although the slide says 2023.
  The "FIT-IoT ... Applied Sciences vol. 11 no. 11" paper is also a 2021 paper. Check the real year before choosing from those lists.

## Caveats on this research
- Paper details above were read through a web-fetch summariser, not manually. Re-read each full paper before registering.
- GitHub links are quoted from the papers; they were not opened here.
- Dates and venues are as reported on the PMC/arXiv pages on 2026-10-07.
