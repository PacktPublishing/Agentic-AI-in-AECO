# Review notes for the authors

Points where the code and the chapter text need reconciling. Each item says
what the code does now.

## Changes to the case study data

1. **Façade cost direction (Chapters 3, 7, 8, 9).** The original `cost_plan.json` made terracotta cheaper than ACP while recording a GBP 341,000 increase, and Chapter 3's text says terracotta increases cost. The cost plan now uses the podium package HOT-POD-FAC-01 at 1,200 m2: ACP GBP 600/m2, terracotta GBP 650/m2 (Chapter 8's R01 rate), an increase of GBP 60,000, rate unconfirmed.
2. **Fire classification of the baseline.** Horizon One Tower has residential storeys above 18 m, so materials in the external wall must achieve Euroclass A2-s1,d0 or A1 (Building Regulations regulation 7(2), England). The ACP baseline is now described as "A2-s1,d0 mineral core". Please reflect this wherever the chapters describe the ACP option, and have the fire engineer review the wording.
3. **Height policy.** The tall-buildings clause now cites London Plan Policy D9, matching Chapter 2. Other clauses remain fictional borough Local Plan policies.
4. **Carbon screening figures.** The Chapter 3 Sustainability Agent now uses Chapter 7's screening figures (50 and 46 kgCO2e/m2, A1-A3, panels and supports) instead of the earlier 95 and 62.

## Text issues found while building the code

5. **Timeline.** Chapter 10 has Level 4 poured by 17 April 2026, but Chapter 2's pre-application report is dated 12 June 2026, the façade substitution is raised on 12 August 2026 (Chapter 3), and Chapter 5 is still selecting the massing. Suggested fix: move Chapters 10 and 12 to April 2027 and Chapter 11 to March 2028. The code keeps the dates as printed until the text changes.
6. **Chapter 5 floor area.** The generated options give B at 41,100 m2 and C at 35,210 m2 GIA against a 55,000-65,000 m2 target in `project_overview.json`. Either the brief or the options need adjusting, and the text should say whether the shortlisted options meet the area brief.
7. **Chapter 7 printed code.** The listing's indentation is broken in the source document (the lines were wrapped when the document was formatted), so it will not run as printed. `ch7/listings.py` is the clean version. `compare_options` in the text reads a global `options`; the repository passes it explicitly.
8. **Chapter 1, Section 1.6.** The section is empty, and the Packt-formatted file still contains the template's JavaScript sample. `ch1/simple_agent.py` is proposed for this section.
9. **Chapter 2, Listing 2.2.** Recent PyMuPDF versions warn that `import fitz` is deprecated; use `import pymupdf`.
10. **Chapter 6.** The specified 1.8 W/m2K exceeds the 1.6 W/m2K limiting value for curtain walling in Approved Document L 2021 Volume 2. `AuditAgent.generate_compliance_log(include_regulatory=True)` adds this as a sixth, High severity row. It is off by default so the output matches the current five-row table.
11. **Identifier prefixes.** Chapter 13 uses H1T for assets; other chapters use HOT. Chapter 14 cites FAC-SPEC-R06 and SUP-*-RETURN; Chapter 9 cites DEMO-QUOTE-*-R1. The code maps them, but a single convention in the text would be cleaner.
12. **Chapter 13 listing.** `retrieve_om_guidance` returns a fixed string. `ch13/fm_triage.py` shows the retrieval it stands for, including the identifier mapping the chapter describes (AHU_19_1 / MEP-AHU-019A).
13. **Chapter 3 graph.** Tiago's comment about parallel execution is implemented: `AECOOrchestrator(..., parallel=True)`. The text could show it alongside the linear version.

## Code changes worth mentioning in the text

- Agents register themselves (`horizon_core.agent_base.AGENT_REGISTRY`) with chapter, reviewer role and data class; Chapter 15 reads this register.
- `AECOOrchestrator(..., pause_for_review=True)` stops before human review and resumes with `record_decision(...)`, the same pattern as Chapter 11.
- Supplier D's note in `procurement/bids.csv` contains a planted prompt injection. Chapter 9's agent withholds it from the model, and it cannot change a score. Chapter 14 could use it as a worked example.
- Evaluation coverage (Chapter 15, control G5) is 57%: agents in Chapters 3 to 5 have no golden cases yet.

## Second pass: final chapters compared with the original drafts

Every final Packt-style chapter was compared word by word with the draft
originally uploaded. Similarity is 95-99%; the differences are the intended
ones (heading case and numbering, Technical requirements and topic lists,
figure captions, code lead-ins replacing "Example:" labels, typo fixes).

Fixed in this pass:

- **Chapter 3.** Two passages were lost when a near-duplicate block was removed during conversion. Both are restored after "The exact fields will vary by workflow": the "A stronger response should not simply say..." paragraph and "The important point is consistency..." sentence.
- **Chapter 1.** Packt template leftovers removed (the "EXTRA STUFF" block, instruction text, JavaScript sample). Topic list and Technical requirements added. Section 1.6 now has the `ch1/simple_agent.py` listing, its output and a short explanation (new text, please review). Typo "Before we are looking at" corrected. Figure 1.1 captioned "The anatomy of an AECO agent".
- **Chapter 4.** Packt instruction text in Technical requirements replaced with real requirements. First topic aligned with heading 4.1.
- **Chapter 5.** Figure 5.1 captioned. Topic "From brief to testable options" removed (no such section). Technical requirements aligned with the code; Rhino.Compute and Speckle kept as optional.
- **Chapter 6.** Topic list and Technical requirements, previously copied from Chapter 5, replaced with Chapter 6's own.
- **Chapter 7.** The three listings, broken in the original draft, replaced with correctly indented versions. Only tokens from the original code are used, the output matches the text (50,000 and 46,000 kgCO2e, -8%), and lines fit the Packt page.
- **Repository.** `ch7`, `ch8` and `ch9/listings.py` are now verbatim copies of the printed code; `ch1/simple_agent.py` is the Section 1.6 listing. `tests/test_listings.py` runs them all.

Still needs an author decision:

- **Chapter 3 cost direction.** Listing 3.2 says terracotta increases cost, but the worked output ("Cost impact: Potential saving, subject to quantity confirmation"), the conflict example ("Cost supports Option B due to estimated capital saving") and Step 6 ("the Cost Agent may report a saving, while the Sustainability Agent reports a carbon increase") say the opposite, and Chapter 7 finds terracotta about 8% lower in carbon. Suggested wording: "Cost impact: Cost increase of about GBP 60,000, subject to supplier rate confirmation"; "Cost flags Option B for commercial review because of the higher rate"; "the Cost Agent may report an increase, while the Sustainability Agent reports a carbon reduction that still lacks a product EPD". The opening "may first appear as a simple cost saving idea" would then read "may first appear as a simple appearance and durability improvement".
- **Chapter 4 structure.** Seven topics are listed but only two numbered sections exist (4.1 and 4.2, with subsections). Either number the subsections or shorten the topic list.
- **Figure 1.1 resolution.** 601 x 459 pixels, below print quality; Packt will ask for a higher-resolution original.
- **Figure 5.1.** Option D leaves the flow after the structural check without an outcome; the text says D is flagged for daylight.
- **Printed file paths (Chapters 2, 8, 10).** The listings read files from the current folder or a "data" folder. Suggest one sentence in each Technical requirements section: "Run the listings from the repository with `python -m chN.listings`."
- **Em dashes** remain in Chapters 4 (1), 5 (18), 6 (19) and 13 (4); not changed without the authors' agreement.


## Third pass: latest chapter files (31 October 2026)

Converted from the authors' latest files. See `change.md` in the final
package for every non-formatting change. Code changes in this pass:

- **Chapter 6.** New listings in `ch6/listings/`. The regulatory limit check is now part of the standard compliance log (six rows, three high severity), and when the newest façade value breaches the limit the Audit Agent no longer recommends aligning the drawing and model to it.
- **Chapter 15.** `ch15/enterprise.py` rewritten to follow the chapter: the four use-case characteristics plus a measure of value, the scale/redesign/retest/stop decision on pilot results, the seven workflow questions, the eight orchestrator skills and the four-stage 12-month route. New `enterprise/pilot_results.csv`.
- **Chapter 1.** The Section 1.6 listing uses US spelling, matching the chapter.

Resolved from the earlier notes: item 10 (Chapter 6 regulatory row) is now in the chapter text and on by default.

## Fourth pass: Chapters 4 and 5 (31 October 2026)

- Chapter 5 expanded, with new listings in `ch5/book_listings/`.
- Resolved item 6 (Chapter 5 floor areas): the generator double-counted the podium storeys and used footprints too small for the site. With realistic footprints, Option B meets the 55,000 m2 target (55,200 m2) and the chapter now discusses the area shortfall of Options C and E.
- Validation now checks height and setback separately. Option A breaches height, setback and daylight.
- Item 5 (timeline): see `dates_proposal.md` in the final package. Not yet applied.
