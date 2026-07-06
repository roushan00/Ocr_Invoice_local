# OCR Invoice Local

AI-powered invoice extraction system that uses a fine-tuned vision-language model (via Ollama) to parse invoice PDFs and extract structured data into PostgreSQL, with real-time progress streaming via Redis SSE.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Uvicorn, Python 3.10+ |
| **AI/ML** | Llama 3.2 Vision (Ollama), Unsloth + LoRA (fine-tuning) |
| **Database** | PostgreSQL (SQLAlchemy 2.0 async) |
| **Cache/Pub-Sub** | Redis (async, SSE progress streaming) |
| **PDF Processing** | PyMuPDF (fitz), Pillow, OpenCV |
| **Validation** | Pydantic v2 with field validators |
| **Logging** | Loguru |

## Project Structure

```
app/
├── api/v1/
│   ├── router.py                          # Route aggregator
│   └── endpoints/
│       ├── start_process.py               # POST /start-process
│       ├── stream_process.py              # GET  /stream-process/{unique_id}
│       └── cancel_process.py              # POST /cancel-process
├── core/
│   ├── config.py                          # Pydantic settings (env vars)
│   ├── db_config.py                       # SQLAlchemy engine & session
│   └── redis.py                           # Redis async client
├── models/
│   ├── input_request.py                   # ProcessRequest, CancelRequest
│   ├── universal_template.py              # UniversalInvoice (main model)
│   ├── general_template.py                # GeneralInvoice (basic template)
│   └── georgia_with_confidence.py         # FieldWithConfidence wrapper
├── services/
│   ├── processor.py                       # Main processing orchestration
│   ├── llm.py                             # AsyncOpenAI → Ollama integration
│   ├── prompt_strategy.py                 # Distributor-specific prompt selection
│   ├── convert_pdf.py                     # PDF → optimized JPEG conversion
│   ├── retry.py                           # Retry decorator with GPU semaphore
│   ├── progress.py                        # Redis progress updates
│   ├── field_confidence.py                # Confidence score computation
│   ├── memoery_clean.py                   # GPU memory cleanup
│   └── merge_invoice.py                   # Multi-page invoice merging
├── prompts/
│   ├── georgia_prompt.py                  # Georgia Crown extraction prompt
│   ├── general_prompt.py                  # General fallback prompt
│   ├── general_prompt2.py                 # Alternative general prompt
│   └── georgia_qwen_prompt.py             # Qwen-specific prompt
├── db_operations/
│   ├── invoice_ops.py                     # Invoice CRUD
│   ├── invoice_items_ops.py               # Line items conversion
│   ├── distributor_ops.py                 # Distributor CRUD
│   ├── update_invoice_status.py           # Status updates
│   ├── update_page.py                     # Page count updates
│   ├── stats_calculation_for_general.py   # Invoice stats calculation
│   └── utils.py                           # Date parsing, field mapping
├── state/
│   └── shared.py                          # ProcessingContext, queues
└── main.py                                # FastAPI app initialization

Modelfile                 # Ollama model definition
build_ollama_model.sh     # Script to build Ollama model
merge_model.py            # Unsloth LoRA → merged model script
```

## API Endpoints

### `POST /start-process`

Start background invoice processing.

```json
// Request
{
  "unique_id": "uuid-string",
  "distributor_id": "uuid-string"   // optional, overrides LLM detection
}

// Response
{
  "message": "Processing started.",
  "status": "processing_background"
}
```

### `GET /stream-process/{unique_id}`

Real-time SSE progress stream.

```
Accept: text/event-stream

data: {"elapsed": 5.2, "fileName": "invoice.pdf", "pages": 3, "percentage": 33, "status": 1, "pageProcess": {"pageNo": 1, "status": 1}}
data: {"elapsed": 15.6, "fileName": "invoice.pdf", "pages": 3, "percentage": 100, "status": 2}
```

- Subscribes to Redis pub/sub channel `progress-events:{unique_id}`
- Returns latest snapshot on connect (refresh-safe)
- Auto-terminates when status reaches COMPLETED (2) or ERROR (3)

### `POST /cancel-process`

Cancel a running process.

```json
// Request
{ "unique_id": "uuid-string" }

// Response
{ "message": "Processing cancelled successfully.", "status": "cancelled" }
```

### `GET /health`

Health check endpoint.

## Processing Workflow

```
1. Client sends POST /start-process with unique_id
                    │
2. Validate folder exists in LOCAL_STORAGE_BASE_PATH/{unique_id}
                    │
3. Convert PDF → optimized JPEG images (DPI 200, Quality 90)
                    │
4. For each page:
   ├── Send progress update → Redis → SSE clients
   ├── Send image to LLM vision model (Ollama)
   ├── Parse JSON response → UniversalInvoice (Pydantic)
   ├── Compute confidence scores from logprobs
   ├── Store invoice + line items → PostgreSQL
   └── Calculate stats, update page count
                    │
5. Multi-page handling: detect new invoice numbers, merge pages
                    │
6. Cleanup: remove temp files, unload GPU memory, expire Redis key (1hr)
```

## Data Model

### UniversalInvoice

```python
class InvoiceLineItem:
    line_no, item_distributor_code, upc, item_name, size
    pack, unit_in_case, case_qty, unit_qty
    unit_cost, discount, tax, net_unit_cost, total_cost, rip
    is_out_of_stock, is_free

class InvoiceSummary:
    total_items, total_out_of_stocks, total_case, total_units
    total_rip, sub_total, total_discounts, total_tax
    deposit, total_payable

class UniversalInvoice:
    distributor_name, invoice_no, invoice_date, due_date
    route_no, page_number, items[], summary
```

Includes automatic type coercion (string → int/float) and JSON repair for LLM output quirks.

## Supported Templates

| Template | Distributor | Details |
|----------|------------|---------|
| **Georgia** | Georgia Crown Distributing Co. | RIP field, OOS/FREE detection, pack/unit parsing |
| **General** | All others | Generic invoice structure, flexible column mapping |

Distributor is auto-detected from the invoice by the LLM. The prompt strategy pattern (`prompt_strategy.py`) selects the appropriate prompt based on distributor name.

## Database Schema

| Table | Purpose |
|-------|---------|
| `public.InvoiceFiles` | File upload tracking (Id, Status, Pages) |
| `public.Invoice` | Invoice master records (Number, Date, Totals, Stats JSON) |
| `public.InvoiceItems` | Line items (ItemData JSON with FieldCode/Value/ConfidenceLevel) |
| `masters.Distributor` | Distributor master data (Id, Name, TableSchema JSON) |

**Status Codes:** Queue (0) → Processing (1) → Completed (2) / Error (3)

## Configuration

Create a `.env` file in the project root:

```env
# App
MODEL_NAME=llama2-vision
APP_NAME=Georgia
LOCAL_STORAGE_BASE_PATH=/path/to/invoice/storage

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=invoices_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_SCHEMA=public

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=null

# Status Codes
STATUS_QUEUE=0
STATUS_PROCESSING=1
STATUS_COMPLETED=2
STATUS_ERROR=3

DEBUG=False
```

## Setup & Run

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis
- Ollama with a vision model loaded
- GPU recommended for inference

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Build/load Ollama model (option A: pull pre-built)
ollama pull llama2-vision

# Build/load Ollama model (option B: merge fine-tuned model)
python merge_model.py
bash build_ollama_model.sh

# Start Ollama (separate terminal)
ollama serve

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Usage

```bash
# 1. Place invoice PDF in storage path
cp invoice.pdf /path/to/storage/{unique_id}/

# 2. Start processing
curl -X POST http://localhost:8000/start-process \
  -H "Content-Type: application/json" \
  -d '{"unique_id": "my-invoice-id"}'

# 3. Stream progress
curl -N http://localhost:8000/stream-process/my-invoice-id

# 4. Cancel (if needed)
curl -X POST http://localhost:8000/cancel-process \
  -H "Content-Type: application/json" \
  -d '{"unique_id": "my-invoice-id"}'
```

## Model Building

### Fine-tuned Model Merge

`merge_model.py` loads a LoRA-adapted model via Unsloth (4-bit), merges weights into the base model (16-bit), and saves in HuggingFace format.

### Ollama Model Build

`build_ollama_model.sh` creates a quantized GGUF model (Q4_K_S) and registers it with Ollama using the `Modelfile` configuration (num_ctx=4096, temperature=0.1).

**Quantization options:** Q4_K_S (smallest/fastest) · Q4_K_M (balanced) · Q5_K_M (better quality) · Q8_0 (full precision)

## Architecture Highlights

- **Async-first** — All I/O (GPU calls, DB, Redis) is async with GPU semaphore to prevent OOM
- **Real-time streaming** — Redis pub/sub powers SSE with refresh-safe snapshots
- **Retry logic** — Exponential backoff (2 attempts, 10-60s wait) via Tenacity
- **LLM robustness** — JSON repair, automatic type coercion, confidence scoring from logprobs
- **Multi-template** — Extensible prompt strategy pattern for new distributors
- **Graceful cancellation** — asyncio task cancellation with proper cleanup
