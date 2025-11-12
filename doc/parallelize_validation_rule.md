To parallelize validation rule application in `_validate_sample`, use `concurrent.futures.ThreadPoolExecutor`. Refactored method:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _validate_sample(self, sample_df: pd.DataFrame) -> dict:
    logger.info("Running validation rules on sample in parallel...")
    results = {'critical_rules': {}, 'important_rules': {}, 'optional_rules': {}, 'sample_size': len(sample_df)}
    
    all_rules = {
        'critical_rules': self.validation_rules['critical_rules'],
        'important_rules': self.validation_rules['important_rules'],
        'optional_rules': self.validation_rules['optional_rules']
    }
    
    def apply_rule(category, rule_id, rule):
        res = self._apply_validation_rule(sample_df, rule)
        return category, rule_id, res
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for category, rules in all_rules.items():
            for rule_id, rule in rules.items():
                futures.append(executor.submit(apply_rule, category, rule_id, rule))
        
        for future in as_completed(futures):
            cat, rid, res = future.result()
            results[cat][rid] = res
    
    return results
```