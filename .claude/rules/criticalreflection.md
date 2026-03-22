---
description: Post-implementation checklist to catch scope drift, duplication, and missed requirements
alwaysApply: true
---

**Critical Implementation Reflection Checklist**

For the changes you’ve just implemented, review your work using the following criteria:

- **Scope or Semantic Drift:** Have you unintentionally expanded, reduced, or altered the original scope or meaning?
- **Unintended Functionality:** Did you implement or modify any features beyond what was intended or requested?
- **Intent Changes:** Were there any changes in explicit or implied intent that were not previously agreed upon?
- **Major Assumptions:** Did you introduce any significant assumptions on-the-fly without confirmation?
- **Duplication:** Is there any new or repeated code, logic, or documentation (partial or complete)?
- **Missed Tasks:** Did you fail to address any required tasks?
- **Incorrect Task Status:** Are any tasks incorrectly marked as complete (`[X]`) when they are still in progress (`[W]`) or not started (`[ ]`)?
- **Other Concerns:** Are there any other implementation patterns that could cause concern for the code owner?

**Instructions:**
Review all relevant `.py`, `.ts`, and `.md` files as needed to verify your answers.

**Report:**
Summarize your findings clearly, highlighting any issues, oversights, or risks.
