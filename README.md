# ForgeWorks AI

A ONE Light Analytics manufacturing and energy operating demonstration. ForgeWorks Manufacturing is a fictional Lagos packaging plant. The application connects completed-shift output, maintenance records, usable material stock and metered grid/generator energy.

## Run

Use Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Scenario mode works without an API key. For Live AI, configure `GEMINI_API_KEY` or `GOOGLE_API_KEY` as an environment variable or in the app's private Streamlit Secrets settings. Never put a key in this repository. The default model is `gemini-3.5-flash-lite`; `GEMINI_MODEL` can override it.

## Standalone deployment

Repository: `forgeworks-ai-demo`. Branch: `main`. Main file: `streamlit_app.py`. Suggested Streamlit subdomain: `forgeworks-ai-demo` (subject to availability). Deploy independently of CedarStone and RelayPoint. Add the private key in this app's own settings after deployment.

## Explore

1. Read Plant overview: 51,800 produced minus 1,302 rejects leaves 50,498 good units, against 56,000 planned. Good-output attainment is 90.2%; gross attainment is 92.5%.
2. Ask the agent for material risks or energy intensity. Inspect its tool evidence. Two materials have usable cover below their recorded supplier lead time.
3. Open Action Lab as plant manager or maintenance coordinator. Prepare a work-order draft for `FW-A03`, review it and explicitly confirm. The audit records the new `FW-WO-003`. Repeating an open work order is rejected.
4. Switch to production supervisor: financial rates and costs are unavailable. Switching role or mode clears the conversation and pending proposal.

## Definitions

Data covers six completed eight-hour shifts on 8–9 October 2026. The fixed business clock is 10 October 2026, 09:00 WAT. The same shift IDs appear in energy and production. The fixture has four assets, four materials and two initial work orders.

- Good units = produced minus rejected. Attainment is output / target; it is not OEE.
- Reject rate = rejected / produced. Production exceptions are below gross target or above 3% rejects.
- Downtime is the sum of recorded line minutes, not a plant-wide elapsed outage.
- Usable stock excludes quarantined quantities. Cover = usable stock / daily use. A risk is cover below the recorded supplier lead time. Purchase orders do not count as received stock.
- Energy = metered grid kWh + metered generator kWh. Diesel litres are used for cost only and are not converted to kWh.
- Energy cost = grid kWh × fictional rate + diesel litres × fictional price. The total is ₦1,687,500 over 5,950 kWh; cost per good unit is ₦33.42. Maintenance, depreciation and other costs are excluded.

## Action and data boundaries

All records are synthetic demonstration data, not client results or achieved savings. The tool layer enforces demo-role permissions; the role selector is not production authentication. Work-order drafts are session-only. Confirmation revalidates the role, revision, asset and duplicate status; tampered or stale proposals are rejected. The model has read/proposal tools and no commit tool. There are no machine commands, purchases, messages, production release or external maintenance integrations. Reset discards changes. Recorded notes are not verified causes or technical diagnoses.

Live provider responses require a separately configured key and must be checked on the deployed app. Automated checks exercise deterministic scenarios and mock provider wiring, not the external provider.

## Verify

```sh
python -m unittest test_operations.py
python test_agent.py
python test_app.py
```

Checks cover reconciliation, quarantine, matching energy periods, cost permissions, non-mutating proposals, explicit confirmation, duplicate rejection, stale/tampered proposals, audit records, role isolation and application reset.
