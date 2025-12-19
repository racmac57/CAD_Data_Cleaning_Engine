# Cad Validation Quick Reference

**Processing Date:** 2025-11-23 00:17:53
**Source File:** CAD_VALIDATION_QUICK_REFERENCE.md
**Total Chunks:** 1

---

# CAD Validation & Revert - Quick Reference

**Last Updated:** 2025-11-22

---

## 🚀 Quick Commands

### Run Complete Workflow (All 3 Steps)
```bash
python scripts/run_cad_validation_workflow.py
```

### Run Individual Steps

**Step 1 & 2: Validation + Diff**
```bash
python scripts/validate_cad_field_changes.py
```

**Step 3: Revert**
```bash
python scripts/revert_cad_using_diff.py
```

---

## 📁 File Paths

### Input Files
| File | Purpose |
|------|---------|
| `test/2025_11_17_CAD_Cleanup_PreManual.csv` | BEFORE (original) |
| `test/2025_11_17_CAD_Cleaned_FullAddress2.csv` | AFTER (cleaned) |

### Output Files
| File | Purpose |
|------|---------|
| `test/CAD_Field_Diff_Report.csv` | Field changes |
| `test/CADNotes_Mismatches.csv` | CADNotes drift |
| `test/2025_11_17_CAD_Reverted_From_Diff.csv` | Reverted file |
| `test/CAD_Revert_Log.txt` | Revert log |

---

## 🔍 Fields Compared

- `Incident`
- `Disposition`
- `How Reported`
- `FullAddress2`
- `Response Type`
- `CADNotes`

---

## ⚠️ Warning Signs

### CADNotes Changed
- **Action:** STOP and investigate
- **Cause:** Data alignment issue
- **Fix:** Don't proceed until resolved

### Unexpected Field Changes
- **Action:** Review diff report
- **Fix:** Run revert to restore

### Verification Failed
- **Action:** Check revert log
- **Fix:** Re-run revert or investigate

---

## ✅ Expected Results for FullAddress2 Cleaning

**Diff Report Should Show:**
- ✓ 40K-50K FullAddress2 changes
- ✓ 0 CADNotes changes
- ✓ 0 Incident changes
- ✓ 0 How Reported changes
- ✓ 0 Response Type changes
- ✓ 0-50 Disposition changes (cleanup only)

**If CADNotes > 0:** INVESTIGATE BEFORE PROCEEDING

---

## 🛠️ Workflow Summary

```
1. Create cleaned file → test/2025_11_17_CAD_Cleaned_FullAddress2.csv
                         ↓
2. Run validation      → python scripts/validate_cad_field_changes.py
                         ↓
3. Review diff report  → test/CAD_Field_Diff_Report.csv
                         ↓
4. Check CADNotes      → test/CADNotes_Mismatches.csv
                         ↓
5. If needed, revert   → python scripts/revert_cad_using_diff.py
                         ↓
6. Use reverted file   → test/2025_11_17_CAD_Reverted_From_Diff.csv
```

---

## 📊 Sample Diff Report Row

```csv
ReportNumberNew,Field_Name,Old_Value,New_Value,match
19-000017,FullAddress2,"Hudson Street & , Hackensack, NJ, 07601","[ADDRESS-REDACTED], Hackensack, NJ, 07601",FALSE
```

---

## 🔧 Common Issues

| Issue | Solution |
|-------|----------|
| AFTER file not found | Create cleaned file first |
| No matching records | Check ReportNumberNew alignment |
| CADNotes mismatches | Investigate data alignment |
| Verification failed | Check revert log for errors |

---

## 📚 Full Documentation

See: `doc/CAD_VALIDATION_REVERT_GUIDE.md`

---

## 🎯 One-Liner Checklist

Before using reverted file:
- [ ] CADNotes mismatches = 0
- [ ] Only expected fields changed
- [ ] Verification passed
- [ ] Revert log shows no errors

