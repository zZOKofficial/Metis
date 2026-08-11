Yep — **METIS**. Here’s the copy-paste-ready `.md` version:

````md
# METIS — Master Development Prompt

> **Your Business. Operated by AI.**

## Mission

Build **METIS**, an AI-operated business management platform for small businesses.

METIS is not a chatbot. It is an **AI workforce** made of specialized agents that perform real business tasks, collaborate with each other, use business data and tools, and produce measurable business outcomes.

The goal is to create a polished, functional MVP suitable for a hackathon focused on building a business with **real customers and real revenue within 90 days**.

---

## 1. Product Concept

**Name:** METIS

**Origin:** Metis (Μῆτις) is associated with wisdom, practical intelligence, cunning, and intelligent strategy in Greek mythology.

**Tagline:**

> **Your Business. Operated by AI.**

METIS gives small businesses an AI workforce instead of another generic AI assistant.

### AI Workforce

- **Manager Agent** — coordinates the workforce
- **Sales Agent** — handles sales and product inquiries
- **Support Agent** — handles customer questions and issues
- **Marketing Agent** — creates marketing activities
- **Operations Agent** — manages orders and inventory
- **Analytics Agent** — analyzes business performance

The business owner remains the highest authority.

---

# 2. Target Customer

Do not initially target every type of business.

The MVP should focus on:

> **Small businesses selling products through social media and online channels.**

Examples:

- Clothing stores
- Electronics shops
- Cosmetics businesses
- Small online retailers
- Facebook-based businesses

The architecture must remain extensible for other industries later.

---

# 3. Problem

Small businesses often cannot afford dedicated employees for:

- Customer support
- Sales
- Marketing
- Order management
- Business analysis

The owner ends up doing everything manually.

METIS transforms this:

```text
Business Owner
      │
      ▼
┌───────────────┐
│ Manager Agent │
└───────┬───────┘
        │
 ┌──────┼───────────────┐
 ▼      ▼               ▼
Sales  Support      Marketing
 │      │               │
 └──────┼───────────────┘
        ▼
   Operations
        │
        ▼
    Analytics
````

---

# 4. Core Principle

The most important principle is:

> **Agents must perform actions, not merely generate text.**

Bad:

```text
User → Chatbot → Text
```

Desired:

```text
Business Event
      ↓
Manager Agent
      ↓
Specialized Agent
      ↓
Tool / Database / API
      ↓
Action
      ↓
Result
      ↓
Manager Agent
      ↓
Business Owner
```

Every agent must have:

* A defined responsibility
* Tools
* Permissions
* Context/memory
* Structured inputs and outputs
* Error handling
* Audit logging
* Controlled communication with other agents

---

# 5. MVP Scope

Prioritize a small but complete workflow over a large collection of unfinished features.

The MVP must include:

1. Business setup
2. Product management
3. Inventory management
4. Customer management
5. Order management
6. AI agent orchestration
7. Agent activity tracking
8. Human approval system
9. Business analytics
10. Owner-facing dashboard
11. Business chat with Manager Agent
12. Google Cloud integration

---

# 6. Business Setup

The owner must be able to create a business profile containing:

* Business name
* Business category
* Description
* Contact information
* Operating hours
* Business policies
* Products
* Pricing
* Inventory
* Business goals

### Product Model

```text
Product
├── ID
├── Name
├── Description
├── Price
├── Stock
├── Category
├── Variants
└── Status
```

---

# 7. Manager Agent

The Manager Agent is the central orchestrator.

### Responsibilities

* Understand business objectives
* Delegate tasks
* Coordinate agents
* Monitor agent results
* Request human approval
* Combine results
* Produce business summaries
* Enforce permissions

Example:

```text
Owner:
"Promote our new summer collection."

Manager Agent
    ↓
Marketing Agent
    ↓
Analytics Agent
    ↓
Sales Agent
    ↓
Manager Agent
    ↓
Campaign proposal
    ↓
Owner approval
```

The Manager should delegate tasks instead of doing everything itself.

---

# 8. Sales Agent

### Responsibilities

* Answer product questions
* Search products
* Check inventory
* Recommend products
* Calculate order totals
* Create orders
* Suggest upsells
* Track potential customers
* Follow up with leads

Example:

```text
Customer:
"Do you have a black shirt under ৳1500?"

Sales Agent
    ↓
Search Product Database
    ↓
Check Inventory
    ↓
Rank Products
    ↓
Respond
```

For the MVP, a simulated customer conversation interface is acceptable.

Design the system so real messaging integrations can be added later.

---

# 9. Customer Support Agent

### Responsibilities

* Answer FAQs
* Explain business policies
* Handle common complaints
* Track customer issues
* Escalate complex issues
* Summarize conversations

The agent must use the business knowledge base.

It must never invent:

* Prices
* Policies
* Refund rules
* Delivery information
* Product information

When information is unavailable, it must escalate or request clarification.

---

# 10. Marketing Agent

### Responsibilities

* Analyze products
* Identify promotional opportunities
* Generate social media content
* Create campaigns
* Write promotional copy
* Suggest target audiences
* Analyze campaign results

Example:

```text
Marketing Agent:

Product A:
High inventory
Low sales

Recommendation:
Create a promotional campaign for Product A.
```

During the MVP, external publishing should require owner approval.

---

# 11. Operations Agent

### Responsibilities

* Manage orders
* Update order status
* Monitor inventory
* Detect low-stock products
* Track operational issues
* Generate operational summaries

Example:

```text
Product A
Stock: 5

Operations Agent:
"Product A is approaching the low-stock threshold."
```

---

# 12. Analytics Agent

The Analytics Agent converts business data into decisions.

It must answer:

* What are my best-selling products?
* What was my revenue today?
* What products are declining?
* Which products are low in stock?
* What should I focus on?
* Which products deserve promotion?
* How are sales changing over time?

### Dashboard Metrics

* Revenue
* Orders
* Customers
* Conversion rate
* Top products
* Inventory alerts
* Agent activity
* AI recommendations

All numerical answers must come from actual stored business data.

---

# 13. Agent Communication

Agents must communicate through structured messages.

Example:

```json
{
  "requester": "manager",
  "target": "marketing",
  "task": "create_campaign",
  "context": {},
  "priority": "normal",
  "requires_approval": true
}
```

Agents must not have unrestricted access to one another.

### Permission Structure

```text
Manager
├── Sales
├── Support
├── Marketing
├── Operations
└── Analytics

Marketing
└── Analytics

Sales
└── Operations
```

All inter-agent actions must be logged.

---

# 14. Human Approval

The business owner is always the final authority.

### Low-Risk Actions

May happen automatically:

* Data analysis
* Reports
* Inventory warnings
* Draft generation

### Medium-Risk Actions

May require configurable approval:

* Customer messages
* Campaign creation
* Business-data modifications

### High-Risk Actions

Always require explicit approval:

* Financial transactions
* Refunds
* Purchases
* External campaign publishing
* Destructive operations

The UI must clearly show:

```text
Action
Agent
Reason
Expected Result
Risk Level

[ Approve ] [ Reject ]
```

---

# 15. Memory Architecture

Implement three types of context.

### Business Memory

Shared information:

* Products
* Policies
* Goals
* Business configuration

### Agent Memory

Agent-specific information:

* Previous tasks
* Relevant history
* Learned preferences

### Conversation Memory

Short-term conversational context.

Agents must only access information allowed by their permissions.

---

# 16. Google Cloud

Google Cloud must be meaningfully integrated into the product.

Prefer:

* **Google ADK** — agent development and orchestration
* **Vertex AI / Gemini** — AI models
* **Cloud Run** — deployment
* **Firestore** — application data and agent state
* **Cloud Storage** — documents and assets
* **Cloud Logging** — monitoring and debugging

Do not add unnecessary services simply to increase the technology list.

The architecture should be simple enough to build and deploy quickly.

---

# 17. Recommended Technology Stack

## Frontend

* Next.js
* TypeScript
* Tailwind CSS
* Modern component library

## Backend

Prefer:

* Python
* FastAPI
* Google ADK

Node.js/TypeScript is acceptable if it significantly improves implementation speed.

## AI

* Gemini
* Vertex AI
* Google ADK

## Database

* Firestore

## Deployment

* Cloud Run

Use a modular monolithic architecture unless there is a strong reason to introduce separate services.

---

# 18. Application Architecture

```text
                    WEB CLIENT
                        │
                        ▼
                 API / BACKEND
                        │
                        ▼
               AGENT ORCHESTRATOR
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    MANAGER           SALES         MARKETING
        │               │               │
        ▼               ▼               ▼
    SUPPORT         OPERATIONS      ANALYTICS
        │               │               │
        └───────────────┼───────────────┘
                        ▼
                    FIRESTORE
                        │
                        ▼
                   GOOGLE CLOUD
```

---

# 19. User Interface

The UI should look like a modern SaaS product.

Avoid:

* Excessive gradients
* Generic AI glow effects
* Unnecessary animations
* Overcrowded dashboards
* Excessive cards
* Fake futuristic interfaces

The application should feel professional and trustworthy.

## Dashboard

Show:

* Revenue
* Orders
* Customers
* Active agents
* Alerts
* Recent activity
* AI recommendations

## Agent Center

Example:

```text
Sales Agent
Status: Active
Tasks: 24
Success Rate: 96%
```

## Activity Feed

Example:

```text
12:42
Sales Agent checked inventory.

12:43
Sales Agent recommended Product #42.

12:44
Operations Agent created Order #183.

12:45
Analytics Agent detected increased demand.
```

## Approval Center

Display actions requiring owner authorization.

## Business Chat

Allow the owner to communicate with the Manager Agent.

Example:

```text
Owner:
"How is my business doing today?"

Manager:
"Revenue is ৳38,400 from 13 orders.
Sales Agent handled 47 customer conversations.
Product A is approaching low stock."
```

All numbers must come from actual application data.

---

# 20. End-to-End Demo

Build the MVP around one complete scenario.

### Step 1

Owner adds a summer collection.

### Step 2

A customer asks:

> "Do you have a blue shirt under ৳2000?"

### Step 3

Sales Agent:

* Searches products
* Checks inventory
* Recommends a product

### Step 4

Customer places an order.

### Step 5

Operations Agent records the order.

### Step 6

Inventory is automatically updated.

### Step 7

Analytics Agent detects increased demand.

### Step 8

Manager Agent reports:

> "Product X sold 8 units today and has only 4 remaining."

### Step 9

Owner asks:

> "Create a promotion for Product Y."

### Step 10

Marketing Agent creates a campaign.

### Step 11

Owner approves it.

### Step 12

The system records the completed action.

This workflow must be polished enough to serve as the primary hackathon demonstration.

---

# 21. Revenue Model

ERGON should use a subscription model.

### Starter

৳1,000/month

### Growth

৳3,000/month

### Pro

৳7,000+/month

Pricing can eventually depend on:

* Number of agents
* Customer conversations
* Orders
* Automation volume
* Business size

For the hackathon, focus on proving that businesses will pay.

---

# 22. 90-Day Business Strategy

The objective is not to build every possible feature.

The objective is:

> **Get paying customers.**

### Phase 1

Build the MVP.

### Phase 2

Find 3–5 small businesses.

### Phase 3

Deploy METIS for them.

### Phase 4

Measure:

* Conversations handled
* Orders generated
* Time saved
* Revenue influenced
* Response time

### Phase 5

Convert successful users into paying customers.

The application should expose these metrics so they can be used as evidence during the hackathon.

---

# 23. Engineering Rules

Follow these rules strictly:

1. Do not over-engineer.
2. Build the MVP before advanced features.
3. Never fabricate business data.
4. Never fabricate agent actions.
5. Never claim an external action occurred if it did not.
6. Keep important actions auditable.
7. Use structured communication between agents.
8. Implement robust error handling.
9. Store secrets in environment variables.
10. Never expose API keys in frontend code.
11. Validate external inputs.
12. Implement authentication.
13. Implement authorization.
14. Protect business data.
15. Keep the system deployable.
16. Document important architecture decisions.
17. Prioritize reliability over unnecessary features.

---

# 24. Testing

Test:

* Agent routing
* Agent permissions
* Invalid requests
* Hallucination prevention
* Database operations
* Order creation
* Inventory updates
* Approval workflows
* Authentication
* Authorization
* API failures
* AI failures
* Duplicate requests
* Concurrent operations
* Incorrect product information

The system must fail safely.

---

# 25. Development Method

Before implementing major functionality:

1. Analyze the requirements.
2. Define the MVP boundary.
3. Design the architecture.
4. Define data models.
5. Define agent interfaces.
6. Define permissions.
7. Define API contracts.
8. Implement the core workflow.
9. Implement the UI.
10. Test the workflow.
11. Deploy to Google Cloud.
12. Perform a production-style review.

Do not generate the entire application blindly in one step.

Work incrementally.

After each major implementation, verify that the system still runs.

---

# 26. Hackathon Priorities

When there is limited time, prioritize:

1. Real business workflow
2. Agent execution
3. Agent collaboration
4. Google Cloud integration
5. Business value
6. Excellent UX
7. Revenue demonstration
8. Analytics
9. Advanced features

Do not spend significant time on:

* Landing-page animations
* Unnecessary microservices
* Dozens of agents
* Elaborate agent personalities
* Features unrelated to business value

> **Five excellent agents are better than twenty fake ones.**

---

# 27. Definition of Done

METIS is considered MVP-complete when a business owner can:

1. Create a business.
2. Add products.
3. Set inventory.
4. View customers.
5. Receive a simulated customer inquiry.
6. Have the Sales Agent respond using real product data.
7. Create an order.
8. Automatically update inventory.
9. Have Operations Agent track the order.
10. Have Analytics Agent analyze the business.
11. Ask Manager Agent for a business summary.
12. Ask Marketing Agent to create a campaign.
13. Approve or reject an agent action.
14. View the complete agent activity history.
15. Deploy the application using Google Cloud.

---

# 28. Final Product Standard

METIS must feel like a real SaaS product that a small business could actually use.

A user should immediately understand:

### What is METIS?

An AI workforce for small businesses.

### What does it do?

It operates sales, customer support, marketing, operations, and analytics through specialized AI agents.

### Who pays?

Small businesses.

### Why do they pay?

METIS performs work that would otherwise require employees or significant owner time.

### How does it make money?

Monthly subscription.

### What makes it different?

The agents don't merely advise the business.

> **They perform the work.**

Build a company, not a science project.

```

This version uses **METIS consistently** and is ready to save as `METIS_MASTER_PROMPT.md`.
```
