---
name: sred-audit
description: Audit and refine SR&ED (Scientific Research and Experimental Development) written submissions for Form T661 Lines 242, 244, and 246. Use when preparing, reviewing, or finalizing SR&ED claim narratives to ensure CRA compliance and maximize claim strength. Triggers on SR&ED, SRED, T661, scientific research, experimental development, tax credit claim, Line 242, Line 244, Line 246, technological uncertainty, technological advancement.
---

# SR&ED Written Submission Audit Skill

## Purpose
This skill guides Claude in auditing SR&ED (Scientific Research and Experimental Development) written submissions for Form T661 Lines 242, 244, and 246. Apply this skill whenever preparing, reviewing, or refining SR&ED claim narratives.

## When to Use This Skill

- After drafting any SR&ED written submission
- When reviewing existing SR&ED claims for improvement
- Before finalizing SR&ED narratives for submission
- When the user requests SR&ED writing assistance

## Audit Process

### Step 1: Draft Review Context
Before auditing, confirm you have:

- The project title/description
- Line 242 text (Scientific or Technological Uncertainties)
- Line 244 text (Work Performed)
- Line 246 text (Advancements Achieved)

If any section is missing, request it from the user before proceeding.

---

## Line 242: Scientific or Technological Uncertainties

### Required Elements
Each uncertainty statement MUST:

- State what was NOT KNOWN at project outset
- Be technological/scientific (not business, commercial, or operational)
- Reference why existing knowledge was insufficient
- Be specific and bounded with identifiable parameters

### Audit Checklist
- [ ] Uncertainty framed as knowledge gap, not business problem
- [ ] Explains WHY standard practice/existing knowledge was inadequate
- [ ] Specific technical parameters or constraints identified
- [ ] No business language as core driver (cost, market, customer needs)
- [ ] References state of knowledge at project START
- [ ] A qualified professional could understand exactly what needed resolution

### Red Flags - Rewrite If Present

| If You Find | Problem | Rewrite To |
|-------------|---------|------------|
| "We didn't know if it would work" | Too vague | Specify WHAT technical aspect was uncertain |
| "No off-the-shelf solution existed" | Not uncertainty | Explain WHY creating solution involved technical uncertainty |
| "We needed to reduce costs" | Business objective | Technical challenges of achieving efficiency |
| "The client required..." | Business driver | Technical barriers to meeting specifications |
| "We had never done this before" | Company-specific | Uncertainty that existed in the field broadly |
| "To meet market demands" | Commercial framing | Technical constraints that created uncertainty |

### Strong Uncertainty Patterns
Use these structures:

```
"It was uncertain whether [specific technical approach] could achieve
[measurable parameter] under [specific constraints] because [technical reason
standard methods were insufficient]."

"No established techniques existed to [specific technical objective] while
maintaining [constraint A] and [constraint B] simultaneously."

"Standard methodologies for [domain] could not predict [specific outcome]
when [novel conditions] were introduced, creating uncertainty about [specific
technical question]."
```

---

## Line 244: Work Performed to Resolve Uncertainties

### Required Elements
Work descriptions MUST:

- Demonstrate systematic investigation (hypothesis -> test -> analyze -> iterate)
- Directly connect to each uncertainty in Line 242
- Include specific technical details (methods, tools, parameters, iterations)
- Document both successes AND failures

### Audit Checklist
- [ ] Structured, methodical approach evident
- [ ] Hypothesis formulation and testing shown
- [ ] Each activity links to a specific Line 242 uncertainty
- [ ] Specific methodologies, tools, and techniques named
- [ ] Quantitative details included (parameters, configurations, iterations)
- [ ] Failed approaches documented alongside successful ones
- [ ] Technical depth sufficient for R&D nature to be clear
- [ ] Experimentation variables clearly identified

### Red Flags - Rewrite If Present

| If You Find | Problem | Rewrite To |
|-------------|---------|------------|
| "We developed..." without detail | No systematic investigation | Add hypothesis, methodology, testing, iterations |
| Only successful outcomes | Missing experimentation evidence | Include failed approaches and what was learned |
| Generic development terms | Could be routine work | Specific technical challenges and how addressed |
| No reference to Line 242 | Disconnected narrative | Explicitly link activities to uncertainties |
| "We used agile/scrum" | Process, not technical work | WHAT was technically investigated |
| Timeline-focused narrative | Administrative content | Technical progression and findings |
| "We implemented..." | Sounds like execution | "We investigated...", "We tested...", "We experimented..." |

### Strong Work Description Structure
For EACH uncertainty, include:

```
1. HYPOTHESIS: "We theorized that [approach] might resolve [uncertainty] because..."

2. METHODOLOGY: "To test this, we [specific technical approach] using [tools/techniques]..."

3. EXPERIMENTATION: "We conducted [number] iterations testing [variables], including:
   - [Specific test/configuration A] which [result]
   - [Specific test/configuration B] which [result]..."

4. ANALYSIS: "Results indicated that [findings]. Specifically, we learned that..."

5. ITERATION: "Based on these findings, we [next approach] to further investigate..."
```

---

## Line 246: Scientific or Technological Advancements

### Required Elements
Advancement statements MUST:

- Describe NEW KNOWLEDGE or CAPABILITY generated
- Be technological/scientific (not business improvement)
- Result directly from Line 244 work
- Extend beyond what was previously known/achievable

### Audit Checklist
- [ ] States new knowledge or capability (not just deliverable)
- [ ] Advancement is technological, not business metric
- [ ] Direct result of resolving Line 242 uncertainties
- [ ] Extends state of knowledge in the field
- [ ] Specific and describable (not vague)
- [ ] Focuses on WHAT WAS LEARNED, not what was built
- [ ] Negative knowledge acknowledged where relevant

### Red Flags - Rewrite If Present

| If You Find | Problem | Rewrite To |
|-------------|---------|------------|
| "We successfully developed [product]" | Outcome, not knowledge | Technical knowledge that enabled the product |
| "Improved performance by X%" | Business metric | Technical understanding enabling improvement |
| "Created a new [feature]" | Feature description | Technical principles discovered |
| No connection to Line 244 | Disconnected | Direct link from experiments to knowledge |
| Advancement = objective | Circular reasoning | Distinguish goal from knowledge achieved |
| "We achieved [the goal]" | Completion statement | "We determined that...", "We established that..." |

### Strong Advancement Patterns
Use these structures:

```
"Through systematic experimentation, we determined that [specific technical
finding] when [conditions], which was previously unknown in [domain]."

"We established that [approach A] is superior to [approach B] for
[application] because [technical reason], contributing new understanding
to [field]."

"The investigation revealed that [parameter X] must be maintained within
[range] to achieve [outcome], a relationship not documented in existing
literature or standard practice."

"We generated new knowledge regarding [technical domain], specifically
that [finding], enabling [capability] that was previously unachievable."
```

---

## Cross-Section Coherence Audit

### Traceability Verification
Create and verify this mapping:

| Uncertainty (242) | Work Performed (244) | Advancement (246) |
|-------------------|----------------------|-------------------|
| Uncertainty 1 | Activities addressing 1 | Knowledge from 1 |
| Uncertainty 2 | Activities addressing 2 | Knowledge from 2 |
| ... | ... | ... |

### Coherence Checks
- [ ] Every uncertainty has corresponding work activities
- [ ] Every uncertainty has a resulting advancement
- [ ] No orphan work activities (all link to an uncertainty)
- [ ] No orphan advancements (all link to work performed)
- [ ] Terminology consistent across all three sections
- [ ] Technical depth consistent across sections
- [ ] Narrative flows logically: uncertainty -> work -> advancement

---

## Language & Style Requirements

### Required Style

- Third person, past tense
- Active voice preferred
- Technical but accessible
- No marketing language or superlatives

### Prohibited Terms - Replace These

| Never Use | Replace With |
|-----------|--------------|
| "Cutting-edge," "innovative," "novel" | Specific technical descriptions |
| "Best-in-class," "world-class" | Measurable technical specifications |
| "Cost-effective," "efficient" (as goals) | Technical performance parameters |
| "Customer requirements" | Technical specifications |
| "Competitive advantage" | Technical capability |
| "Quick," "fast," "rapid" | Specific performance metrics |
| "Seamless," "robust," "scalable" | Quantified technical characteristics |
| "Solution" (standalone) | Specific technical implementation |

---

## CRA Compliance Verification

### Five-Question Test
Verify the submission demonstrates ALL five:

- [ ] 1. Scientific or technological uncertainty existed (Line 242)
- [ ] 2. Systematic investigation was conducted (Line 244)
- [ ] 3. Work aimed to achieve technological advancement (Line 246)
- [ ] 4. Scientific/technological knowledge base was used (throughout)
- [ ] 5. Advancement was achieved or attempted (Line 246)

### Exclusion Check
Verify the work is NOT:

- [ ] Market research or sales promotion
- [ ] Quality control or routine testing
- [ ] Routine data collection
- [ ] Commercial production or tooling-up
- [ ] Style changes or routine design
- [ ] Prospecting or resource exploration
- [ ] Social sciences or humanities research
- [ ] Routine software development or configuration

---

## Scoring & Risk Assessment

After audit, score each element 1-5:

| Element | Score |
|---------|-------|
| Uncertainty clarity | /5 |
| Uncertainty is technological | /5 |
| Work shows systematic investigation | /5 |
| Work-to-uncertainty traceability | /5 |
| Advancement is knowledge-based | /5 |
| Advancement-to-work traceability | /5 |
| Technical depth appropriate | /5 |
| Language quality | /5 |
| Cross-section coherence | /5 |
| CRA eligibility alignment | /5 |
| **TOTAL** | **/50** |

### Score Interpretation

- **45-50:** Strong claim, ready for submission
- **35-44:** Moderate strength, refinement recommended
- **25-34:** Weak claim, significant revision needed
- **Below 25:** High denial risk, major rework required

---

## Audit Output Format

When auditing, provide this structured output:

```markdown
## SR&ED Audit Results

### Overall Assessment
- **Score:** [X]/50
- **Risk Level:** [Low/Moderate/High/Critical]
- **Summary:** [2-3 sentence assessment]

### Line 242 - Uncertainties
**Strengths:**
- [List strengths]

**Issues Found:**
- [List issues with specific quotes]

**Recommended Revisions:**
- [Specific rewrite suggestions]

### Line 244 - Work Performed
**Strengths:**
- [List strengths]

**Issues Found:**
- [List issues with specific quotes]

**Recommended Revisions:**
- [Specific rewrite suggestions]

### Line 246 - Advancements
**Strengths:**
- [List strengths]

**Issues Found:**
- [List issues with specific quotes]

**Recommended Revisions:**
- [Specific rewrite suggestions]

### Cross-Section Issues
- [Traceability gaps]
- [Coherence problems]
- [Terminology inconsistencies]

### Priority Action Items
1. **Critical:** [Must fix before submission]
2. **Important:** [Should fix to strengthen claim]
3. **Recommended:** [Would improve claim quality]

### Revised Draft (if requested)
[Provide rewritten sections addressing all issues]
```

---

## Self-Audit Workflow

When writing SR&ED content, automatically:

1. Draft the content based on project information
2. Pause and apply this audit framework
3. Score each element against the checklists
4. Identify red flags and weak areas
5. Revise the draft to address issues
6. Re-audit until score >= 45/50
7. Present final version with audit summary

**Never present SR&ED writing without first completing this audit cycle.**

---

## Quick Reference Card

### Line 242 Must-Haves
- Uncertainty framed as knowledge gap (not business problem)
- Explains WHY existing methods were insufficient
- Specific technical parameters identified
- Field-level uncertainty (not company-specific)

### Line 244 Must-Haves
- Hypothesis -> Test -> Analyze -> Iterate structure
- Links to each Line 242 uncertainty
- Specific methods, tools, quantities
- Failed attempts documented

### Line 246 Must-Haves
- New knowledge stated (not just deliverable)
- What was LEARNED emphasized
- Links to Line 244 work
- Extends field knowledge

### Universal Don'ts
- Business/market/cost language as drivers
- Marketing superlatives
- Vague statements without specifics
- Orphan content (unlinked sections)
- Product descriptions without knowledge focus
