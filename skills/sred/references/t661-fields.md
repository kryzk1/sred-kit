# T661 Part 2 fields

What each field of Form T661 Part 2 needs, and where the kit keeps it. One Part 2 per project. Check the current form and the CRA guide (T4088) for wording changes before filing.

## Section A: project identification

| Line | Field | Kit | Rule |
|---|---|---|---|
| 200 | Project title (and ID code if any) | `projects.toml` `title`; narrative `- 200` | A continuation copies the prior filing's title exactly |
| 202 | Start date (YYYY-MM-DD) | `start`; `- 202` | A continuation copies the prior filing's start date. A new project: the earliest record of the hypothesis or recognized uncertainty, never the fiscal-year start by default |
| 204 | Completion or expected completion date | `end`; `- 204` | The evidenced end, or the expected end if work continues. Don't leave a date that umbrellas later years without reason |
| 206 | Field of science or technology code (X.XX.XX, see the guide) | `field_code`; `- 206` | Keep the prior code unless the technology changed |
| 208 | Continuation of a previously claimed project | `continuation = true`; `- 208 Continuation: yes` | Exactly one of 208 and 210 |
| 210 | First claim for the project | `continuation = false`; `- 210 First claim: yes` | Needs a genuinely new uncertainty set; write a demarcation note if a related project just ended |
| 218, 220, 221 | Work done jointly or in collaboration with other businesses; their names and business numbers | `eligibility.collaboration` | Flag for the accountant |

## Section B: project description

| Line | Question | Limit |
|---|---|---|
| 242 | What scientific or technological uncertainties did you attempt to overcome? | 350 words |
| 244 | What work did you perform in the tax year to overcome them? (chronological) | 700 words |
| 246 | What scientific or technological advancements did you achieve, or attempt to achieve? | 350 words |

Some filing software enforces a line budget instead (for example 50/100/50 lines of 78 characters). `limits.mode` in `sred.toml` follows the preparer's software; `check.py narrative` reports both counts either way. Plain text only.

## Section C: additional project information

| Lines | Field | Kit |
|---|---|---|
| 253–259 | Who prepared Section B: an employee directly involved (253, name 254), another employee (255, 256), an external consultant (257, name 258, firm 259) | narrative `- Prepared by:`; `preparer.third_party_preparer` |
| 260–261 | Key individuals directly involved: names, qualifications or experience, position titles | narrative `- Key individuals:`; each must be claimed in `person_summary.csv` |
| 265 | Salary or wages claimed for SR&ED performed outside Canada | `eligibility.work_outside_canada`; roster `in_canada` |
| 266 | Expenditures for SR&ED carried out on behalf of another party | `eligibility.client_contract_work` |
| 267–269 | SR&ED performed by people other than employees; their names and business numbers | narrative `- Contractors:`; contractor rows in `roster.csv`; Line 244 must say what contractors did |
| 270–281 | Evidence available: planning documents (270), resource records or time sheets (271), design of experiments (272), project records or notebooks (273), design, architecture and source code (274), records of trial runs (275), progress reports or meeting minutes (276), test protocols, data, analysis and conclusions (277), photos and videos (278), samples or prototypes (279), contracts (280), other (281) | narrative `- Evidence:`. Tick every type the narrative relies on and that is actually retained |
| 282 | Other supporting information | `handoff/README.md` notes |

## Filing deadline

The claim must be filed within 18 months of the end of the tax year. `check.py setup` prints the date.
