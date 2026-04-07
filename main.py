"""
AZ-900 AI Tutor — FastAPI Application
--------------------------------------
Provides a POST /chat endpoint for conversational queries.

Also provides:
- POST /evaluate   — track user performance per topic
- GET  /performance — view current user stats
- GET  /stats       — alias for /performance
- GET  /weak-topics — sorted list of weak topics
- POST /start-exam  — generate a practice exam
- GET  /test        — quick quiz mode
"""

import time
import uuid
import random
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from embeddings import search, get_model
from generator import generate_answer, get_generator


# ── In-Memory User Performance Tracking ────────────────────────────────
user_stats: dict = {
    "correct": 0,
    "wrong": 0,
    "topics": {},   # topic_name -> {"correct": int, "wrong": int}
}

# ── Static AZ-900 Question Bank ─────────────────────────────────────────
QUESTION_BANK = [
    {
        "question": "What is the primary benefit of cloud computing?",
        "options": [
            {"label": "A", "text": "Eliminates all IT costs"},
            {"label": "B", "text": "On-demand scalability and pay-as-you-go pricing"},
            {"label": "C", "text": "Requires no internet connection"},
            {"label": "D", "text": "Only available to large enterprises"},
        ],
        "correct_answer": "B",
        "topic": "Cloud Concepts",
        "explanation": "Cloud computing offers on-demand resources and a consumption-based pricing model."
    },
    {
        "question": "Which cloud service model gives you the most control over the underlying infrastructure?",
        "options": [
            {"label": "A", "text": "SaaS"},
            {"label": "B", "text": "PaaS"},
            {"label": "C", "text": "IaaS"},
            {"label": "D", "text": "FaaS"},
        ],
        "correct_answer": "C",
        "topic": "Cloud Concepts",
        "explanation": "IaaS (Infrastructure as a Service) provides the most control — you manage VMs, storage, and networking."
    },
    {
        "question": "What does 'high availability' mean in Azure?",
        "options": [
            {"label": "A", "text": "Services are always free"},
            {"label": "B", "text": "Services run on the fastest hardware"},
            {"label": "C", "text": "Minimal downtime with guaranteed uptime SLAs"},
            {"label": "D", "text": "Services are physically close to you"},
        ],
        "correct_answer": "C",
        "topic": "Cloud Concepts",
        "explanation": "High availability ensures services remain accessible with minimal downtime, backed by SLA guarantees."
    },
    {
        "question": "What is an Azure Region?",
        "options": [
            {"label": "A", "text": "A single data center building"},
            {"label": "B", "text": "A geographic area containing one or more data centers"},
            {"label": "C", "text": "A virtual network segment"},
            {"label": "D", "text": "An Azure subscription boundary"},
        ],
        "correct_answer": "B",
        "topic": "Azure Architecture",
        "explanation": "An Azure Region is a geographic area that contains at least one, but potentially multiple, data centers."
    },
    {
        "question": "What is the purpose of an Azure Availability Zone?",
        "options": [
            {"label": "A", "text": "To reduce pricing for reserved instances"},
            {"label": "B", "text": "To isolate resources by subscription"},
            {"label": "C", "text": "To protect against data center failures within a region"},
            {"label": "D", "text": "To speed up global content delivery"},
        ],
        "correct_answer": "C",
        "topic": "Azure Architecture",
        "explanation": "Availability Zones are physically separate data centers within a region to protect against single data center failures."
    },
    {
        "question": "Which Azure service is used to deploy and manage virtual machines?",
        "options": [
            {"label": "A", "text": "Azure App Service"},
            {"label": "B", "text": "Azure Virtual Machines"},
            {"label": "C", "text": "Azure Functions"},
            {"label": "D", "text": "Azure Container Instances"},
        ],
        "correct_answer": "B",
        "topic": "Azure Compute",
        "explanation": "Azure Virtual Machines is the IaaS offering for deploying and managing VMs in Azure."
    },
    {
        "question": "What is Azure App Service primarily used for?",
        "options": [
            {"label": "A", "text": "Running virtual machines"},
            {"label": "B", "text": "Storing large amounts of unstructured data"},
            {"label": "C", "text": "Hosting web apps, APIs, and mobile backends"},
            {"label": "D", "text": "Managing Active Directory"},
        ],
        "correct_answer": "C",
        "topic": "Azure Compute",
        "explanation": "Azure App Service is a PaaS offering for hosting web applications, RESTful APIs, and mobile backends."
    },
    {
        "question": "What is Azure Functions an example of?",
        "options": [
            {"label": "A", "text": "IaaS"},
            {"label": "B", "text": "SaaS"},
            {"label": "C", "text": "Serverless / FaaS"},
            {"label": "D", "text": "DBaaS"},
        ],
        "correct_answer": "C",
        "topic": "Azure Compute",
        "explanation": "Azure Functions is a serverless (Function-as-a-Service) compute offering — you pay only when your code runs."
    },
    {
        "question": "What is Azure Blob Storage used for?",
        "options": [
            {"label": "A", "text": "Running virtual machines"},
            {"label": "B", "text": "Storing unstructured data like images, videos, and documents"},
            {"label": "C", "text": "Running relational databases"},
            {"label": "D", "text": "Managing DNS records"},
        ],
        "correct_answer": "B",
        "topic": "Azure Storage",
        "explanation": "Azure Blob Storage is an object storage solution for the cloud, ideal for unstructured data."
    },
    {
        "question": "Which storage redundancy option replicates data to a secondary region?",
        "options": [
            {"label": "A", "text": "LRS (Locally Redundant Storage)"},
            {"label": "B", "text": "ZRS (Zone Redundant Storage)"},
            {"label": "C", "text": "GRS (Geo-Redundant Storage)"},
            {"label": "D", "text": "NRS (Node Redundant Storage)"},
        ],
        "correct_answer": "C",
        "topic": "Azure Storage",
        "explanation": "GRS replicates your data to a secondary region hundreds of miles away from the primary region."
    },
    {
        "question": "What is an Azure Virtual Network (VNet)?",
        "options": [
            {"label": "A", "text": "A managed Kubernetes cluster"},
            {"label": "B", "text": "A private network in Azure for resource communication"},
            {"label": "C", "text": "A CDN for global content distribution"},
            {"label": "D", "text": "An identity management service"},
        ],
        "correct_answer": "B",
        "topic": "Azure Networking",
        "explanation": "Azure Virtual Network (VNet) enables Azure resources to communicate with each other, the internet, and on-premises networks."
    },
    {
        "question": "What is VNet Peering?",
        "options": [
            {"label": "A", "text": "Connecting a VNet to the internet"},
            {"label": "B", "text": "Replicating data between storage accounts"},
            {"label": "C", "text": "Connecting two VNets so resources can communicate"},
            {"label": "D", "text": "A load balancing technique"},
        ],
        "correct_answer": "C",
        "topic": "Azure Networking",
        "explanation": "VNet Peering connects two Azure Virtual Networks, allowing resources to communicate as if on the same network."
    },
    {
        "question": "What does Azure Load Balancer do?",
        "options": [
            {"label": "A", "text": "Distributes incoming traffic across multiple backend resources"},
            {"label": "B", "text": "Backs up virtual machine disks"},
            {"label": "C", "text": "Encrypts data at rest"},
            {"label": "D", "text": "Manages user identities"},
        ],
        "correct_answer": "A",
        "topic": "Azure Networking",
        "explanation": "Azure Load Balancer distributes inbound traffic to backend pool instances based on rules and health probes."
    },
    {
        "question": "What is Azure Active Directory (AAD)?",
        "options": [
            {"label": "A", "text": "A file storage system"},
            {"label": "B", "text": "A cloud-based identity and access management service"},
            {"label": "C", "text": "A relational database service"},
            {"label": "D", "text": "A virtual machine image gallery"},
        ],
        "correct_answer": "B",
        "topic": "Identity & Security",
        "explanation": "Azure Active Directory is Microsoft's cloud-based identity and access management service."
    },
    {
        "question": "What is Multi-Factor Authentication (MFA)?",
        "options": [
            {"label": "A", "text": "Using multiple passwords for one account"},
            {"label": "B", "text": "A verification method requiring two or more credentials"},
            {"label": "C", "text": "Encrypting data with multiple keys"},
            {"label": "D", "text": "A firewall with multiple rules"},
        ],
        "correct_answer": "B",
        "topic": "Identity & Security",
        "explanation": "MFA adds a second layer of security by requiring additional verification beyond just a password."
    },
    {
        "question": "What is Role-Based Access Control (RBAC) in Azure?",
        "options": [
            {"label": "A", "text": "A feature to assign permissions to users based on their roles"},
            {"label": "B", "text": "A way to create custom Azure regions"},
            {"label": "C", "text": "A method to replicate databases"},
            {"label": "D", "text": "A billing management tool"},
        ],
        "correct_answer": "A",
        "topic": "Cloud Governance",
        "explanation": "RBAC allows you to grant users only the access they need to do their jobs by assigning roles."
    },
    {
        "question": "What is Azure Policy used for?",
        "options": [
            {"label": "A", "text": "Monitoring application performance"},
            {"label": "B", "text": "Creating virtual networks"},
            {"label": "C", "text": "Enforcing organizational standards and compliance"},
            {"label": "D", "text": "Managing DNS records"},
        ],
        "correct_answer": "C",
        "topic": "Cloud Governance",
        "explanation": "Azure Policy helps enforce organizational standards and assess compliance at scale."
    },
    {
        "question": "What is a Management Group in Azure?",
        "options": [
            {"label": "A", "text": "A group of Azure administrators"},
            {"label": "B", "text": "A container for managing access, policies, and compliance across subscriptions"},
            {"label": "C", "text": "A billing account grouping"},
            {"label": "D", "text": "A group of virtual machines"},
        ],
        "correct_answer": "B",
        "topic": "Cloud Governance",
        "explanation": "Management Groups provide a governance scope above subscriptions to apply policies across multiple subscriptions."
    },
    {
        "question": "What is the Azure Pricing Calculator used for?",
        "options": [
            {"label": "A", "text": "To pay your Azure bills"},
            {"label": "B", "text": "To estimate costs for Azure services before deployment"},
            {"label": "C", "text": "To compare Azure with AWS pricing"},
            {"label": "D", "text": "To apply discount codes"},
        ],
        "correct_answer": "B",
        "topic": "Cost Management",
        "explanation": "The Azure Pricing Calculator helps you estimate your expected monthly bill for Azure services."
    },
    {
        "question": "What is Azure Cost Management + Billing used for?",
        "options": [
            {"label": "A", "text": "Deploying new Azure services"},
            {"label": "B", "text": "Monitoring, allocating, and optimizing Azure cloud costs"},
            {"label": "C", "text": "Creating user accounts"},
            {"label": "D", "text": "Configuring firewalls"},
        ],
        "correct_answer": "B",
        "topic": "Cost Management",
        "explanation": "Azure Cost Management + Billing helps you understand your Azure invoice, monitor usage, and optimize spending."
    },
    {
        "question": "What is a Service Level Agreement (SLA)?",
        "options": [
            {"label": "A", "text": "A pricing contract for Azure services"},
            {"label": "B", "text": "Microsoft's commitment to uptime and connectivity"},
            {"label": "C", "text": "A security compliance standard"},
            {"label": "D", "text": "A backup and recovery plan"},
        ],
        "correct_answer": "B",
        "topic": "Cloud Concepts",
        "explanation": "An SLA defines Microsoft's commitment to uptime and connectivity for Azure services, typically 99.9% or higher."
    },
    {
        "question": "What is the Shared Responsibility Model?",
        "options": [
            {"label": "A", "text": "Sharing Azure costs between teams"},
            {"label": "B", "text": "Microsoft handles all security responsibilities"},
            {"label": "C", "text": "Security responsibilities are divided between the cloud provider and customer"},
            {"label": "D", "text": "Customers host their own physical infrastructure"},
        ],
        "correct_answer": "C",
        "topic": "Cloud Concepts",
        "explanation": "The Shared Responsibility Model defines which security tasks are handled by Microsoft and which by the customer."
    },
    {
        "question": "What is Azure Resource Manager (ARM)?",
        "options": [
            {"label": "A", "text": "A virtual machine management tool"},
            {"label": "B", "text": "The deployment and management service for Azure resources"},
            {"label": "C", "text": "A cloud storage interface"},
            {"label": "D", "text": "A networking protocol"},
        ],
        "correct_answer": "B",
        "topic": "Azure Architecture",
        "explanation": "ARM is the deployment and management service that provides a management layer to create, update, and delete resources."
    },
    {
        "question": "What is the purpose of a Resource Group in Azure?",
        "options": [
            {"label": "A", "text": "To group users with similar permissions"},
            {"label": "B", "text": "To group related Azure resources for management as a unit"},
            {"label": "C", "text": "To group virtual networks together"},
            {"label": "D", "text": "To organize Azure subscriptions"},
        ],
        "correct_answer": "B",
        "topic": "Azure Architecture",
        "explanation": "A Resource Group is a container that holds related resources for an Azure solution, enabling lifecycle management as a unit."
    },
    {
        "question": "What is Azure Monitor?",
        "options": [
            {"label": "A", "text": "A tool to create Azure dashboards"},
            {"label": "B", "text": "A service for collecting, analyzing, and acting on telemetry data"},
            {"label": "C", "text": "A billing alert system"},
            {"label": "D", "text": "A network traffic analyzer"},
        ],
        "correct_answer": "B",
        "topic": "Azure Management",
        "explanation": "Azure Monitor collects and analyzes telemetry from cloud and on-premises environments to maximize performance and availability."
    },
]


# ── Pydantic Models ─────────────────────────────────────────────────────
class EvaluateRequest(BaseModel):
    topic: str
    correct: bool

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = []
    top_k: int = 3

class StartExamRequest(BaseModel):
    topic: Optional[str] = None
    count: int = 10


# ── Helpers ─────────────────────────────────────────────────────────────
def get_weak_topic() -> str | None:
    worst_topic = None
    worst_wrong = 0
    for topic, counts in user_stats["topics"].items():
        if counts["wrong"] > worst_wrong:
            worst_wrong = counts["wrong"]
            worst_topic = topic
    return worst_topic

def get_sorted_weak_topics() -> list:
    result = []
    for topic, counts in user_stats["topics"].items():
        total = counts["correct"] + counts["wrong"]
        if total == 0:
            continue
        error_rate = round(counts["wrong"] / total, 2)
        result.append({
            "topic": topic,
            "correct": counts["correct"],
            "wrong": counts["wrong"],
            "total": total,
            "error_rate": error_rate,
        })
    result.sort(key=lambda x: x["error_rate"], reverse=True)
    return result


# ── Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 60)
    print("  AZ-900 AI Tutor — Starting Up")
    print("=" * 60 + "\n")
    print("⏳ Pre-loading models (this may take a minute)...")
    get_model()
    print("  ✅ Embedding model loaded")
    get_generator()
    print("  ✅ Generation model loaded")
    print("\n🚀 Server ready! http://localhost:8000/docs\n")
    yield
    print("👋 Shutting down...")


# ── App ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AZ-900 AI Tutor",
    description="Intelligent, fully offline tutor for Microsoft AZ-900 certification.",
    version="2.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"service": "AZ-900 AI Tutor", "version": "2.0.0", "status": "online", "docs": "/docs"}


@app.post("/chat")
async def chat(request: ChatRequest):
    """Stateful conversational endpoint with memory."""
    start_time = time.time()
    query = request.query
    history = request.history
    top_k = request.top_k

    if len(query) < 3:
        raise HTTPException(status_code=400, detail="Query too short")

    try:
        search_query = query
        if history:
            last_user_msg = next((m.content for m in reversed(history) if m.role == "user"), "")
            if last_user_msg:
                search_query = f"{last_user_msg} {query}"

        retrieved = search(search_query, top_k=top_k)
        if not retrieved:
            raise HTTPException(status_code=404, detail="No relevant content found.")

        hist_dicts = [{"role": m.role, "content": m.content} for m in history]
        answer = generate_answer(query, retrieved, hist_dicts)
        answer["response_time_seconds"] = round(time.time() - start_time, 2)

        weak = get_weak_topic()
        if weak:
            answer["weak_topic_hint"] = f"⚠️ You seem weak in: {weak}. Would you like a quick test?"

        return JSONResponse(content=answer)

    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Vector store not found: {e}. Run build_vectorstore.py first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/evaluate")
async def evaluate(payload: EvaluateRequest):
    """Record whether the user answered correctly for a given topic."""
    topic = payload.topic
    is_correct = payload.correct

    if is_correct:
        user_stats["correct"] += 1
    else:
        user_stats["wrong"] += 1

    if topic not in user_stats["topics"]:
        user_stats["topics"][topic] = {"correct": 0, "wrong": 0}

    if is_correct:
        user_stats["topics"][topic]["correct"] += 1
    else:
        user_stats["topics"][topic]["wrong"] += 1

    return {
        "status": "recorded",
        "evaluated": {"topic": topic, "correct": is_correct},
        "user_stats": user_stats,
    }


@app.get("/performance")
async def performance():
    """Return the current user performance stats and weak topic."""
    weak = get_weak_topic()
    return {"user_stats": user_stats, "weak_topic": weak}


@app.get("/stats")
async def stats():
    """Alias for /performance — returns user session stats."""
    weak = get_weak_topic()
    return {"user_stats": user_stats, "weak_topic": weak}


@app.get("/weak-topics")
async def weak_topics():
    """Return a sorted list of topics by error rate (highest first)."""
    topics = get_sorted_weak_topics()
    return {
        "weak_topics": topics,
        "total_topics_tracked": len(topics),
        "overall": {
            "correct": user_stats["correct"],
            "wrong": user_stats["wrong"],
        }
    }


@app.post("/start-exam")
async def start_exam(request: StartExamRequest):
    """
    Generate a practice exam. If topic is specified, filter questions to that topic.
    Falls back to mixed questions if topic has fewer than `count` questions.
    """
    topic = request.topic
    count = max(1, min(request.count, 15))  # clamp between 1-15

    if topic:
        pool = [q for q in QUESTION_BANK if q["topic"].lower() == topic.lower()]
        if len(pool) < count:
            # Supplement with general questions
            others = [q for q in QUESTION_BANK if q["topic"].lower() != topic.lower()]
            pool += random.sample(others, min(count - len(pool), len(others)))
    else:
        pool = list(QUESTION_BANK)

    selected = random.sample(pool, min(count, len(pool)))

    questions = []
    for i, q in enumerate(selected):
        questions.append({
            "id": i + 1,
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "topic": q["topic"],
            "explanation": q["explanation"],
        })

    return {
        "exam_id": str(uuid.uuid4()),
        "topic": topic or "Mixed",
        "question_count": len(questions),
        "questions": questions,
    }


@app.get("/test")
async def test_mode():
    """Return a set of quick quiz questions."""
    weak = get_weak_topic()
    message = "Starting test"
    if weak:
        message += f" — focusing on your weak area: {weak}"
    return {
        "message": message,
        "weak_topic": weak,
        "questions": [
            "What is Azure?", "What is IaaS?", "What is SLA?",
            "What is the shared responsibility model?", "What are Azure Regions?",
        ],
    }


@app.get("/kb-stats")
async def kb_stats():
    """Return statistics about the loaded knowledge base (chunks, vectors)."""
    try:
        from embeddings import load_index
        index, chunks = load_index()
        word_counts = [len(c.split()) for c in chunks]
        return {
            "total_chunks": len(chunks),
            "total_vectors": index.ntotal,
            "embedding_dimension": index.d,
            "avg_chunk_words": round(sum(word_counts) / len(word_counts), 1),
            "min_chunk_words": min(word_counts),
            "max_chunk_words": max(word_counts),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
