# Bill Analyzer — Next Phase Design Spec

> Approved: 2026-05-19 | Approach: Bug-First (Plan A) | Scope: P0 + P1

## Phase 1: Bug Fixes (P0)

### 1.1 to_dict() — 补全缺失字段
- **File**: `src/database/models.py:61-76`
- **Problem**: Only 12 fields returned; missing `is_anomaly`, `anomaly_*`, `is_subscription`, `subscription_*`, `payment_method`, `status`
- **Fix**: Add all business fields. Use `or False` for boolean defaults.

### 1.2 Session Lifecycle — Option 1
- **Files**: `src/database/operations.py`, `app.py` (~8 callsites)
- **Problem**: ORM objects returned after session close → DetachedInstanceError risk
- **Fix**: Return `List[Dict]` from query methods (call `.to_dict()` inside session). Update all `app.py` callsites to use dicts directly.

### 1.3 Bare Except
- **File**: `app.py:88`
- **Fix**: `except:` → `except Exception:`, show "—" fallback in sidebar.

## Phase 2: Test Coverage (P0)

- pytest + conftest.py (in-memory SQLite fixture, sample DataFrame fixture)
- `tests/test_parsers.py` — parse + detect_format + encoding
- `tests/test_pipeline.py` — 6-step flow + error handling
- `tests/test_classifiers.py` — rule confidence, AI fallback (mocked)
- `tests/test_database.py` — CRUD, dedup, stats, to_dict completeness

## Phase 3: PDF Parser (P0)

- **File**: New `src/parsers/pdf_parser.py`
- **Lib**: `pdfplumber` primary, `PyMuPDF` fallback
- **Blocked on**: User providing sample PDFs in `tests/samples/`
- **Design**: Inherit `BaseParser`, detect bank type from table headers

## Phase 4: UI Enhancements (P1)

### 4.1 Manual Classification
- Inline edit: `st.data_editor` with dropdown for category/subcategory
- Batch: Checkbox selection + "apply category" button on category management page
- Write back: `classification_method='manual'`

### 4.2 Search & Advanced Filters
- Text search (counterparty + description), date range, amount slider
- Subcategory filter (linked to category), anomaly/subscription toggles
- New DB params: `keyword`, `amount_min`, `amount_max`, `subcategory`

### 4.3 Excel Export
- New `src/utils/exporters.py`, using openpyxl
- 5 sheets: All Transactions, Category Summary, Monthly Trends, Anomalies, Subscriptions

## Phase 5: New Features (P1)

### 5.1 Budget Management
- Reuse `BudgetPlan` from `models_extended.py`, integrate into `init_db.py`
- Per-category monthly limit + alert threshold (default 80%)
- New page with progress bars + overspend warnings
- Sidebar alert for over-budget categories

### 5.2 Classification Performance
- Vectorize rule matching: `str.contains()` + `np.select`
- Batch AI calls for low-confidence records
- Target: <5s for 10k records (excluding AI)

## Cleanup
- Integrate `BudgetPlan` table into `init_db.py`
- Move debug scripts to `scripts/debug/` or delete
- Move sample files to `tests/fixtures/`
