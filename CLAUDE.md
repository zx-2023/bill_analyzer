# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a family financial data analysis system built with Python and Streamlit. It processes multi-platform bill data (Alipay, WeChat Pay, Bank, Meituan), performs intelligent classification, deduplication, and provides visualization analysis.

## Architecture

### Core Modules

1. **Parsers** (`src/parsers/`)
   - `BaseParser`: Abstract base class for all platform parsers
   - `AlipayParser`: Parses Alipay CSV bills (GBK encoding)
   - Platform auto-detection based on column names and keywords
   - Standardizes heterogeneous formats into unified schema

2. **Processors** (`src/processors/`)
   - `DataCleaner`: Removes invalid records, standardizes merchant names, filters excluded transactions
   - `Deduplicator`: Multi-level deduplication (same-platform by transaction_id, cross-platform by fuzzy matching)
   - Similarity calculation: time window (±5min) + exact amount + description/merchant fuzzy match

3. **Classifiers** (`src/classifiers/`)
   - `RuleClassifier`: YAML-based keyword, merchant, and regex pattern matching
   - `AIClassifier`: Kimi API integration for AI-assisted classification
   - `HybridClassifier`: Rule-first (confidence threshold 0.8), AI fallback for low-confidence cases

4. **Database** (`src/database/`)
   - SQLAlchemy ORM models: `Transaction`, `Category`, `ClassificationRule`, `ImportHistory`
   - `DatabaseManager`: Context-managed sessions, CRUD operations, summary statistics

5. **Visualization** (Streamlit)
   - Main app: `app.py`
   - Pages: Dashboard, Data Import, Transactions, Category Management, Settings

## Commands

### Setup and Initialization

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database (creates tables and default categories)
python scripts/init_db.py
```

### Running the Application

```bash
# Start Streamlit app
streamlit run app.py
```

### Development Workflow

```bash
# Run tests (when implemented)
pytest tests/

# Format code
black src/ app.py

# Lint code
flake8 src/ app.py
```

## Key Conventions

### Data Flow

1. **Import**: File upload → Parser detection → Parse to DataFrame
2. **Process**: Clean → Deduplicate → Classify
3. **Store**: Convert to dict → Insert to database (check duplicates)
4. **Display**: Query database → Render Streamlit components

### Configuration Management

- **Platform configs**: `config/platform_config.yaml` - column mappings, encodings, date formats
- **Classification rules**: `config/classification_rules.yaml` - category keywords, merchants, patterns
- **Environment variables**: `.env` - API keys, database path (copy from `.env.example`)

### Database Conventions

- All amounts stored as absolute positive values; `type` field determines income/expense
- `transaction_id` must be unique across entire database
- Duplicate detection uses `is_duplicate` flag and `duplicate_group` for grouping
- Classification tracking: `classification_method` (rule/ai/manual), `classification_confidence`

### Parser Implementation

When adding new platform parsers:

1. Inherit from `BaseParser`
2. Define `PLATFORM_NAME` class variable
3. Implement `parse()` and `detect_format()` methods
4. Add platform config to `config/platform_config.yaml`
5. Register in auto-detection logic

Example structure:
```python
class NewPlatformParser(BaseParser):
    PLATFORM_NAME = "new_platform"

    def parse(self, file_path: str) -> pd.DataFrame:
        df = self.read_file(file_path)
        df = self.standardize(df)
        return df

    def detect_format(self, file_path: str) -> bool:
        # Check for platform-specific features
        pass
```

### Classification Rule Syntax

In `classification_rules.yaml`:

```yaml
categories:
  category_name:
    keywords: [keyword1, keyword2]       # High confidence (0.9)
    merchants: [merchant1, merchant2]    # High confidence (0.9)
    patterns: ['regex1', 'regex2']       # Medium confidence (0.7)
    exclude_keywords: [exclude1]         # Reduces confidence by 50%
```

## Important Implementation Details

### Alipay CSV Parsing

- Alipay CSVs may have header advertisement rows
- `_clean_alipay_header()` searches for "交易时间" keyword to locate actual header
- Default encoding: GBK (fallback: UTF-8, GB2312, GB18030)

### Deduplication Strategy

**Level 1 (Strong)**: Same `transaction_id` within same platform (confidence 1.0)

**Level 2 (Fuzzy)**: Cross-platform matching
- Time window: ±5 minutes
- Amount: exact match required
- Description + merchant similarity > 80%
- Confidence ≥ 0.8: auto-mark duplicate
- Confidence 0.7-0.8: mark for review

### AI Classification

- Uses Kimi API (`kimi-k2-turbo-preview` model)
- Temperature: 0.3 (low randomness for consistency)
- Batch processing to reduce API calls
- Validation: AI result must match existing categories, otherwise fall back to rule-based

### Session State Management (Streamlit)

- `st.session_state.db`: DatabaseManager instance (singleton)
- `st.session_state.classifier`: HybridClassifier instance
- Initialize in main app, reuse across pages

## Troubleshooting

### Common Issues

1. **"File encoding error"**: Check `platform_config.yaml` encoding setting; parser tries multiple encodings automatically

2. **"Duplicate transactions not detected"**: Verify time window and similarity thresholds in `Deduplicator.__init__()`

3. **"AI classification fails"**: Check `.env` for valid `KIMI_API_KEY`; validate with `AIClassifier.validate_api_key()`

4. **"Database locked"**: SQLite doesn't handle concurrent writes well; use `DatabaseManager.get_session()` context manager

### Development Tips

- Use `loguru` logger instead of `print()` for debugging
- Test parsers with real bill samples (anonymized)
- Run database operations in try-except blocks with session rollback
- Streamlit hot-reloads on file changes; use `@st.cache_data` for expensive operations

## Future Extension Points

1. **Add new platforms**: Implement parser in `src/parsers/`, add config to YAML
2. **Custom categories**: Edit `classification_rules.yaml` or use database `Category` model
3. **Export formats**: Add exporters in `src/utils/exporters.py`
4. **Visualization**: Add chart components in `src/visualization/` and integrate to dashboard
5. **Budget management**: Create new `Budget` model and tracking logic
