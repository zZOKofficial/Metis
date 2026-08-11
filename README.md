# METIS — Your Business. Operated by AI.

METIS is an AI-operated business management platform for small businesses. It provides an AI workforce made of specialized agents that perform real business tasks, collaborate with each other, use business data and tools, and produce measurable business outcomes.

## Quick Start

### Prerequisites
- Python 3.11, 3.12, or 3.13 (Python 3.14 not yet supported)
- Node.js 20+
- Google Cloud account with Firestore and Gemini API enabled

### Backend Setup

`ash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Google Cloud credentials

# Run
uvicorn src.main:app --reload --port 8000
`

### Frontend Setup

`ash
cd frontend
npm install
npm run dev
`

Visit http://localhost:3000

## Architecture

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI
- **AI:** Google Gemini via Vertex AI
- **Database:** Firestore
- **Deployment:** Cloud Run

## Agents

| Agent | Role |
|-------|------|
| Manager | Orchestrates workforce, delegates tasks |
| Sales | Product inquiries, recommendations, orders |
| Support | Customer questions, FAQs, complaints |
| Marketing | Campaigns, content, promotions |
| Operations | Order management, inventory tracking |
| Analytics | Business metrics, insights, recommendations |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/business | Create business |
| GET | /api/business/{id} | Get business |
| POST | /api/products/{id} | Add product |
| GET | /api/products/{id} | List products |
| POST | /api/orders/{id} | Create order |
| GET | /api/orders/{id} | List orders |
| GET | /api/agents/{id} | Agent status |
| POST | /api/chat/{id} | Chat with Manager |
| GET | /api/approvals/{id} | List approvals |
| GET | /api/analytics/{id}/dashboard | Dashboard metrics |

## License

MIT
