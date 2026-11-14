from appendix_a.evaluation import run_cases

results = run_cases()
passed = sum(r.status == "pass" for r in results)
print(passed, "of", len(results), "cases passed")


class WrongNumbers:
    def complete(self, prompt):
        evidence = prompt.split("EVIDENCE:", 1)[-1]
        return evidence.replace("46,000", "41,000")


result = run_cases(llm=WrongNumbers(), case_ids=["E04"])[0]
print(result.status, result.failures)
