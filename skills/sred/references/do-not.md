# Do-not patterns (judgment)

Patterns a reviewer has to judge, distilled from real claims, audits, adversarial reviews and an accountant's edits before filing. Use them while drafting (Phase 4) and give them to the red-team (Phase 5).

- Word and phrase patterns a script can catch live in `do-not-patterns.toml`, and `check.py narrative` enforces them.
- Rules the `sred-audit` rubric already covers are not repeated here: business framing, vague uncertainties, missing hypotheses, success-only narratives, feature descriptions as advancements, marketing language, orphans.
- Each entry: what not to do, then what to do instead.

## Line 242: uncertainties

- **242-01** Don't open with a dense technical sentence and no context. → One or two sentences on what the company does (third person), then the prior baseline, then the uncertainties.
- **242-03** Don't leave the baseline vague for a continuing project. → Name what prior years established, with figures, and say which finding produced each new uncertainty. For a new project, name the completed work it builds on.
- **242-04** Don't frame "the vendor's documentation didn't cover it" as the uncertainty. → "No established method in the available knowledge base addressed …", and list the documentation, community resources and published patterns reviewed as evidence the search was exhausted.
- **242-05** Don't claim a general problem is unsolved when solutions exist. → Scope it to the combination: "Published work addressed A and B separately but established no method for A under B."
- **242-06** Don't present your own system's quirks (legacy data quality, your architecture's assumptions, configuration) as technological uncertainty. → Reframe as the field-level question, or drop it.
- **242-07** Don't put results in Line 242. → What was unknown at the outset. A brief baseline test of standard methods is fine ("a review of published methods and 40 trials with the standard approach produced …").
- **242-08** Don't say "standard practice was insufficient" without naming it. → Standard method, then the conditions, then why its outcome was unknown under them.
- **242-09** Don't lead with an abstract theory that unifies everything. → Specific uncertainties first; one closing sentence for the shared class if needed.
- **242-10** Don't strip every named technology for the sake of generality. → Name the systems whose interaction created the uncertainty in 242 and 244; generalize in 246.

## Line 244: work performed

- **244-01** Don't write an incident log or defect catalogue. → Each thread as hypothesis, method, result, conclusion. A falsified hypothesis is fine: "We hypothesized a single cause; analysis of the failure logs showed two independent causes."
- **244-03** Don't stop at the observation. → Close each experiment with what it established.
- **244-04** Don't spend words on supporting infrastructure. → One bridge sentence ("building on the prior finding that …, we re-architected …"); details belong in working papers.
- **244-05** Don't include routine tooling, configuration churn, bug fixes or standard integration. → Only work that tested a hypothesis tied to a 242 uncertainty.
- **244-06** Don't close with retrospective commentary on what the work meant. → End with the evidence retained.
- **244-07** Don't include untested ideas or future work. → Delete; it belongs in next year's notes.
- **244-08** Don't open a paragraph with an umbrella label. → "To investigate [the uncertainty by name], we …"
- **244-09** Don't organize topically when the form asks for chronological order. → A technical progression of hypotheses and tests per uncertainty; dates only where they mark a turn.
- **244-10** Don't narrate planning chatter as experimentation. → A technical paraphrase of the decision and its reason.
- **244-11** Don't describe comparisons without variables, run counts or repetitions when the record has them. → "Across 230 trials we varied A, B and C …". Don't invent a clinical-trial standard either (see R-02).

## Line 246: advancements

- **246-02** Don't claim known best practices, configuration findings or textbook techniques. → Only what standard practice did not predict; the rest stays in 244 as record.
- **246-03** Don't scope the finding to your own system ("for our architecture"). → A class of systems: "for vision systems that …".
- **246-04** Don't universalize beyond what was tested. → "For systems that [conditions], within [tested bounds] …".
- **246-05** Don't phrase findings as vendor-specific discoveries. → The class-level statement plus its trigger condition; vendor names stay in 242 and 244.
- **246-06** Don't restate the uncertainty as the advancement. → The specific finding, e.g. "conditioning the sampler on part class outperformed a single prior at high occlusion".
- **246-07** Don't omit why the finding was new. → One clause naming the sources that did not establish it at the outset.
- **246-08** Don't overstate novelty ("first", "never before documented"). → "Not established in [named sources] for [class]".
- **246-09** Don't drop negative or boundary findings. → Knowing why an approach fails, and where, is an advancement.
- **246-10** Don't present measured operating parameters as the advancement. → They are evidence; claim the principle they established.
- **246-11** Don't replace sharp quantitative boundaries with abstractions. → Keep the threshold, rate or comparison that bounds the finding.
- **246-12** Don't claim an isolated defect fix. → Record it in 244; claim the failure-mode class if one was characterized.

## Section A

- **A-01** Don't rename a continuing project. → Keep the filed title; describe this year's scope in 242. A genuinely new direction is a new project.
- **A-02** Don't use a new title or the first-claim box to escape continuation. → Decide 208 or 210 deliberately; a first claim needs a disjoint uncertainty set.
- **A-03** Don't set the start date by the fiscal calendar, or on a record that doesn't show the hypothesis. → The earliest evidenced hypothesis or recognized uncertainty. A continuation keeps its original start date.
- **A-04** Don't cite a start-date record for content it doesn't contain. → Cite the record that holds the hypothesis; describe others as corroboration.
- **A-05** Don't leave a completion date that umbrellas later years, or a stale one. → The evidenced end, or the reason work continues.
- **A-06** Don't let the Section C evidence boxes contradict the narrative. → Tick every evidence type the narrative relies on and that is retained.
- **A-07** Don't change the field code between years without a technological reason.

## Across the three lines

- **X-02** Don't vary terms for the same thing across lines. → Identical phrases; a bridge sentence when a tool changes.
- **X-03** Don't group unrelated lines of inquiry into one project without one shared technological advancement. → One advancement per project, or split. Tag evidence by stream so each can stand alone.
- **X-04** Don't treat anyone's edited return, the accountant's included, as final. → Re-run `check.py narrative` and the traceability check after every editing pass.

## Prior years

- **P-01** Don't re-claim knowledge claimed before under new wording or a new application. → A per-project table: prior knowledge, new question, do not re-claim.
- **P-02** Don't describe continuing problems without explaining why a new uncertainty arose despite the prior finding. → Frame it as a consequence of implementing that finding.
- **P-03** Don't rely on a new input, application or label as the only difference. → Show the new technological question and why prior knowledge could not answer it.
- **P-04** Don't claim the prior project's tail work, or support work that predates the new uncertainty. → Exclude it and say so in the coverage map.
- **P-05** Don't restructure projects year to year without a short written rationale.
- **P-06** Don't argue demarcation on calendar grounds alone. → Compare uncertainty sets against every prior filing and keep a dated inception chain.
- **P-07** Don't ignore earlier backlog items on the same idea. → Say why an unstarted idea does not move the start date.

## Evidence and facts

- **E-01** Don't write numbers from memory or from earlier drafts; an audit that repeats a number does not verify it. → Every figure traces to a raw record through the evidence table.
- **E-02** Don't cite a record whose content doesn't support the fact. → Verify content, not just that the key exists.
- **E-03** Don't treat AI-generated meeting notes or summaries as primary evidence. → Re-derive from raw data; summaries are `weight=summary`.
- **E-04** Don't present a literature review done afterwards as proof of what was known at the outset. → Check publication dates, search beyond one source, and keep dated, contemporaneous records of what the team consulted.
- **E-05** Don't treat the existence of a commit or ticket as proof of eligible work. → Classify by content.
- **E-06** Don't overstate experimental status ("validated", "controlled comparison", "parity") unless the record shows it. → Say what was and was not tested.
- **E-07** Don't imply every hypothesis was written down at the time if some are reconstructed. → Word the narrative to match.
- **E-08** Don't write figures that can be misread (a status code read as a count).

## AI and machine-learning work

- **AI-01** Don't frame the work as prompt writing, prompt variations or phrasing iterations. → The system-level uncertainty: interactions among components that no documentation predicted.
- **AI-02** Don't claim tool adoption, model selection or standard fine-tuning as the advancement. → What the experiments established about control, validation and bounds.
- **AI-03** Don't make "models are non-deterministic" or generic hallucination the uncertainty. → The specific unresolved control problem.
- **AI-04** Don't claim the model vendor's advancement. → Your own system-level knowledge.
- **AI-05** Don't claim copy quality, persuasion or conversion as the result. → Technical properties: conformance rates, failure-mode classes.
- **AI-06** Don't present an agent grading its own output as validation. → An independent or deterministic check against external evidence.
- **AI-07** Don't present budget caps, monitoring or CI as research. → Frame a measured resource-governance uncertainty, or exclude it.
- **AI-08** Don't use bot-authored comments or agent output as evidence of human investigation, or count AI execution time as labour.

## Financial consistency with the narrative

- **F-01** Don't apply one SR&ED % to everyone; executives are usually lower. → Per-person % from the time basis, with a basis for each override.
- **F-02** Don't convert commits, tickets, messages or weeks of activity directly into hours. → The evidence-day time basis proposes shares; paid hours come from payroll.
- **F-03** Don't allocate the same time to two projects, or count excluded work.
- **F-04** Don't leave contractor status, arm's-length treatment or names inconsistent between the narrative, Lines 267–269 and the labour summary.
- **F-05** Don't claim support work wholesale. → Support must directly serve an experiment and its share must match the narrative.
- **F-06** Don't cost people outside their service period, or people the claimant excluded.
- **F-07** Don't cost review-only time without records.
- **F-08** Don't leave work-location statements or program limits unverified. → Check payroll and current legislation.

## Considered and rejected: don't over-correct

Adversarial reviews raise these; each was rejected or narrowed on review.

- **R-01** "Deny every activity that isn't the core experiment." Engineering, programming, data collection and testing that directly support the experiment are SR&ED. Frame them with their acceptance criteria.
- **R-02** "Require blinded comparisons and sample sizes." The test is systematic investigation, not a clinical trial. Show variables and counts where they exist.
- **R-03** "It's parameter tuning, deny it." When the claimed advancement is the principle, keep the parameters as evidence and claim the principle.
- **R-04** "An umbrella project means denial." The remedy is re-delineation, not denial; stream-tag evidence so projects can be separated.
- **R-05** "A short gap between projects means an artificial boundary." Projects are delineated by uncertainty sets. Document the demarcation; don't move dates to create distance.
- **R-06** "The real start is the first large experiment." Investigation starts at hypothesis formation, provided the cited record shows it.
- **R-07** "One bad citation impeaches the evidence." Verify every row instead of discarding the map.
- **R-08** "The literature search must predate each uncertainty." The form asks for the knowledge base at the outset; keep contemporaneous records, but a later review is not disqualifying.
- **R-09** "Every documented failure is debugging." Knowing why an approach fails can be an advancement; frame failures as tested hypotheses.
- **R-10** A domain noun ("marketing", "pricing") describing what the system works on is not business framing.
- **R-11** A soft word in a continuing project's filed title is not a reason to rename it (A-01 wins).
- **R-12** Scanner hits need context: "no applicable solution", "building on", "supported", quoted bad outputs used as test evidence, prior-year "developed" are fine.
- **R-13** Two related technical areas in one project can stand if one shared advancement is articulated; don't split by reflex.
- **R-14** Don't change a filed timeline just because a reviewer finds it broad; consistency with prior filings matters.
- **R-15** A line exactly at its word limit is legal; headroom is advice.
- **R-16** First or third person are both acceptable; be consistent within a line.

## Calibration from filed claims

A preparer tolerating a pattern doesn't prove CRA approves of it, so these remain flags, not rules:

- Filed text has exceeded the word limits while fitting a 50/100/50 line budget. Target the word limits; confirm the preparer's software.
- "Migration" vocabulary, short supporting-work descriptions in 244, a one-sentence 244 opener, "applying", and "undocumented interactions" framing have all appeared in filed claims. Treat them as medium or low flags, not prohibitions.
- Business framing in 242/246 has appeared in older filed claims; it is still a high flag.
