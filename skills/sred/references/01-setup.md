# Phase 1: Onboarding and setup

Collect everything later phases need, so the run never stalls for missing facts. Onboarding records **facts and preferences**; it locks no scope decisions.

## Procedure

1. In an empty claim folder, copy `sred.toml`, `roster.csv` and `STATE.md` from `<skill-dir>/templates/`. Set `phase: 1-setup`.
2. Ask the five batches below, one batch at a time. Use multiple-choice prompts where the answer is a choice.
3. Accept documents instead of typed answers: a payroll export, prior T661 filings, invoices, contracts, the accountant's labour template, an answers file. Extract the answers, then show what you extracted for confirmation.
4. "I don't know yet" is a valid answer. Leave the field blank and add an open question to `STATE.md` tagged with the phase it blocks, e.g. `- Q2 (blocks phase 6): Bob's paid hours`.
5. Run `python3 <skill-dir>/scripts/check.py setup --claim .` after each batch. Every `MISSING` line is either answered or logged as an open question.
6. Run `python3 <skill-dir>/scripts/capture.py check --claim .` once sources are configured. A source already captured (listed in `evidence/raw/MANIFEST.json`) does not need working credentials.
7. Show a one-page summary: company and fiscal year, the filing deadline `check.py setup` prints (fiscal year end + 18 months), people, sources and their subscription end dates, preferences, and open questions. The claimant approves it.
8. Gate: nothing blocks phase 2. Log the phase, set `phase: 2-capture`, and write the Next action (usually "capture the source whose access ends first").

## Question bank

"Lands in" names the `sred.toml` key or `roster.csv` column. "Blocks" is the phase `check.py setup` holds until it is answered; "-" means optional.

### A. Company and claim

| Ask | Lands in | Blocks |
|---|---|---|
| Legal company name | `company.name` | 2 |
| Canadian-controlled private corporation? | `company.ccpc` | - |
| Provinces of operation | `company.provinces` | - |
| Time zone of the team (dates are bucketed in it) | `company.timezone` (IANA, e.g. `America/Toronto`) | - |
| Fiscal year start and end | `fiscal_year.start`, `.end` (unquoted TOML dates) | 2 |
| Has the company claimed SR&ED before? | `claim.first_claim` | 3 |
| Prior T661 Part 2 filings (copy them into `prior/`) | `claim.prior_filings` | 3 |
| Project titles exactly as filed before (Line 200) | `claim.prior_titles` | 3 |
| Field-of-science codes filed before (Line 206) | `claim.field_codes` | - |
| Prior projects and their completion dates | `[[claim.prior_projects]]` `title`, `end` | - |
| Accountant or preparer, and firm | `preparer.accountant`, `.firm` | 7 |
| Their labour-summary template, if any (CSV `column,field`) | `preparer.labour_template` | - |
| Does their filing software enforce the form's word limits or a line budget? | `limits.mode` (`words` or `lines`); a different budget goes in `[limits.lines]` | 7 |
| Target date to hand off to the accountant | `preparer.handoff_target` | - |
| Who prepares the claim; is a paid third party involved? | `preparer.third_party_preparer` | - |
| Who approves decisions | `preparer.ratifier` | 3 |

### B. Eligibility basics

Each answer may be "none". Anything else is flagged for the accountant and reviewed in Phase 3.

| Ask | Lands in | Blocks |
|---|---|---|
| Government assistance received (grants, IRAP, other credits) | `eligibility.government_assistance` | 3 |
| Work performed for clients under contract | `eligibility.client_contract_work` | 3 |
| Work funded by someone else | `eligibility.funded_by_others` | 3 |
| Work performed outside Canada | `eligibility.work_outside_canada` | 3 |
| Work done jointly or in collaboration with other businesses (Line 218) | `eligibility.collaboration` | - |

### C. People (one `roster.csv` row each; a person who was both employee and contractor gets two rows)

| Ask | Column | Blocks |
|---|---|---|
| Short id and full name | `id`, `name` | 2 |
| Employee or contractor; company (for contractors) | `classification`, `company` | 2 |
| Role; start and end dates if not the whole year | `title`, `start`, `end` | - |
| Handles in each tool, and email | `aliases`: `github:jdoe;gitlab:jdoe;jira:Jane Doe;slack:U123;email:jane@co.com` | 2 |
| Worked in Canada? | `in_canada` (Y/N) | 6 |
| Owns 10% or more of any class of shares, or is related to someone who does? | `specified_employee` (Y/N) | 6 |
| Employees: paid hours; wages paid and earned in the year; bonus; taxable benefits; pay in lieu | `paid_hours`, `wages_paid`, `wages_earned`, `bonus`, `taxable_benefits`, `pay_in_lieu` | 6 |
| Contractors: invoiced amount paid in the year, and for work done in the year | `wages_paid`, `wages_earned` | 6 |
| Contractors: arm's length? written contract? does it mention SR&ED? | `arms_length`, `contract_provided`, `sred_in_contract` (Y/N) | 6 |
| Address, if the accountant's template wants it | `street`, `city`, `province`, `postal`, `country` | - |
| Employees' total earned wages from payroll (contractors excluded) | `payroll.total_wages_earned` | 6 |

### D. Tools (one `[[sources]]` block each)

| Ask | Lands in | Blocks |
|---|---|---|
| Code host(s): GitHub, GitLab, or local clones of any git host | `kind = "code"`; at least one code source | 2 |
| Issue tracker, chat, meeting notes, docs | `kind = "tracker" \| "chat" \| "meetings" \| "docs"` | - |
| How to capture each: API, the tool's export file, a Claude connector, or `git log` | `method = "api" \| "export" \| "connector" \| "git-log"` | 2 |
| API: credentials (env var names), org/repos (GitHub), projects (GitLab), base URL and projects (Jira) | `token_env`, `email_env`, `org`, `repos`, `projects`, `base_url` | 2 |
| Export: where the file is, and which preset fits (see `adding-a-source.md`) | `export_path`, `mapping` | 2 |
| Local clones: their paths | `paths` | 2 |
| When does each subscription end? | `subscription_end` | - |
| Slack plan tier (free plans hide history older than 90 days) | `plan` | - |
| What issue keys look like (e.g. `ACME-123`, `#123`) | `issue_key_regex` | - |

Credentials: GitHub uses `GITHUB_TOKEN` or `gh auth login`; GitLab `GITLAB_TOKEN`; Linear `LINEAR_API_KEY`; Jira `JIRA_EMAIL` and `JIRA_TOKEN`.

### E. Context and preferences

| Ask | Lands in |
|---|---|
| What the company builds; which problems were technically hard this year; experiments that were abandoned | `scope/claimant_context.md` (leads for discovery, never evidence) |
| Work they believe is not SR&ED | `STATE.md` `## Preferences (not decisions)`; decided in the Phase 3 coverage map |
| Preferred scenario (conservative, balanced, maximum) | `STATE.md` `## Preferences (not decisions)`; leave `claim.scenario` blank until Phase 3 |
| ITC estimate rates (template defaults; marked "verify current rates") | `[rates]` |
